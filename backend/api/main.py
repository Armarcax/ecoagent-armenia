"""
EcoAgent Armenia — FastAPI Backend
OpenRouter (անվճար) версия
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# .env из папки backend
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

from rag.rag_engine import (
    query_ecoagent,
    search_kb,
    build_context,
    SEED_LAWS,
    _knowledge_base,
    chunk_text,
    doc_id_hash,
)

app = FastAPI(
    title="EcoAgent Armenia API",
    description="ՀՀ Բնապահպանական և բնօգտագործման AI Agent",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://ecoagent.am",
        "https://ecoagent-armenia-9dm3flk7n-armarcaxs-projects.vercel.app",
        "https://ecoagent-armenia.vercel.app",
        "*",  # Allow all origins for now
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Startup ──────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    global _knowledge_base

    # Initialize in-memory KB (fallback)
    _knowledge_base.clear()
    for doc in SEED_LAWS:
        chunks = chunk_text(doc.get("body", ""))
        for i, chunk in enumerate(chunks):
            _knowledge_base.append({
                "id":         doc_id_hash(doc["doc_id"], i),
                "doc_id":     doc["doc_id"],
                "title":      doc["title"],
                "chunk":      chunk,
                "sector":     doc.get("sector", "general"),
                "url":        doc.get("url", ""),
                "doc_number": doc.get("doc_number", ""),
                "date":       doc.get("date", ""),
                "source":     doc.get("source", "arlis.am"),
            })

    # Initialize Supabase DB
    try:
        from db.supabase_client import init_db
        await init_db()
        print(f"[✓] Supabase initialized")
    except Exception as e:
        print(f"[⚠️] Supabase init failed: {e}")

    print(f"[✓] EcoAgent started — {len(_knowledge_base)} chunks in KB")


# ─── Models ───────────────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    question: str
    sector:   Optional[str] = None

class QueryResponse(BaseModel):
    answer:      str
    sources:     list[dict]
    sector:      str
    chunks_used: int
    timestamp:   str


# ─── Routes ───────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "name":    "EcoAgent Armenia",
        "version": "1.0.0",
        "status":  "running",
        "kb_size": len(_knowledge_base),
    }

@app.get("/health")
async def health():
    return {"status": "ok", "kb_chunks": len(_knowledge_base)}


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Հarczit partar che")
    result = await query_ecoagent(question=req.question, sector=req.sector)
    return QueryResponse(**result)


@app.post("/query/stream")
async def query_stream(req: QueryRequest):
    """Streaming — OpenRouter-ov"""

    cl = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )

    chunks = await search_kb(req.question, sector=req.sector, top_k=6)
    context = build_context(chunks) if chunks else "Տvyal harcit veraberel teghekvatyun chi gtvel."

    system_prompt = """Դու EcoAgent Armenia-ն ես՝ Հայաստանի բնապահպանական արհեստական բանականության խորհրդատուն։

⚠️ ԿԱՐԵՎՈՐ — Պատասխանները պետք է լինեն միայն մաքուր հայերեն լեզվով՝ հայկական տառերով (Ա, Բ, Գ, Դ և այլն)։
Լատինատառ գրությունը արգելվում է։

ԿԱՆՈՆՆԵՐ

1. Պատասխանիր միայն տրամադրված համատեքստի հիման վրա։
2. Նշիր օրենքի անվանումը, համապատասխան հոդվածը և հղումը (URL)։
3. Պատասխանը կառուցիր կետերով, հստակ և մասնագիտական ձևով։

ՊԱՏԱՍԽԱՆԻ ՁԵՎԱՉԱՓ

✅ Ի՞նչ է պահանջում օրենքը

📋 Անհրաժեշտ փաստաթղթեր

⚠️ Տուգանքներ / ռիսկեր

🔗 Աղբյուրներ"""

    user_msg = f"HARCC: {req.question}\n\nCONTEXT:\n{context}\n\nPataskhanir hayeren."

    async def generate():
        # Sources առաջinsend
        sources = []
        seen = set()
        for chunk in chunks:
            if chunk["doc_id"] not in seen:
                seen.add(chunk["doc_id"])
                sources.append({
                    "title":      chunk["title"],
                    "url":        chunk["url"],
                    "doc_number": chunk["doc_number"],
                })
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

        # Stream OpenRouter
        try:
            stream = cl.chat.completions.create(
                model="openrouter/auto",
                max_tokens=1500,
                stream=True,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_msg},
                ],
            )
            for chunk_data in stream:
                delta = chunk_data.choices[0].delta
                if delta.content:
                    yield f"data: {json.dumps({'type': 'text', 'content': delta.content})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'text', 'content': f'⚠️ Sghal: {e}'})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/sectors")
async def get_sectors():
    return {"sectors": [
        {"id": "construction",  "name": "Շինարարություն", "icon": "🏗️"},
        {"id": "mining",        "name": "Հանքարդյունաբերություն", "icon": "⛏️"},
        {"id": "forestry",      "name": "Անտառ տնեսություն", "icon": "🌲"},
        {"id": "agriculture",   "name": "Գյուղատնտեսություն", "icon": "🌾"},
        {"id": "energy",        "name": "Էներգետիկա", "icon": "☀️"},
        {"id": "import_export", "name": "Արտահանում և ներմուծում", "icon": "🚢"},
        {"id": "biodiversity",  "name": "Շրջակա միջավայրի պահպանություն", "icon": "🐾"},
        {"id": "air",           "name": "Օդ ու ջրի աղտոտվածություն", "icon": "💨"},
        {"id": "waste",         "name": "Թափոնների վերամշակում", "icon": "♻️"},
        {"id": "esg",           "name": "ESG հաշվետվություն", "icon": "📊"},
    ]}


@app.get("/laws")
async def get_laws(sector: Optional[str] = None):
    seen = set()
    laws = []
    for chunk in _knowledge_base:
        if chunk["doc_id"] not in seen:
            if not sector or chunk["sector"] == sector:
                seen.add(chunk["doc_id"])
                laws.append({
                    "doc_id":     chunk["doc_id"],
                    "title":      chunk["title"],
                    "doc_number": chunk["doc_number"],
                    "sector":     chunk["sector"],
                    "url":        chunk["url"],
                    "date":       chunk["date"],
                })
    return {"laws": laws, "total": len(laws)}


@app.get("/stats")
async def get_stats():
    sector_counts: dict = {}
    for chunk in _knowledge_base:
        s = chunk["sector"]
        sector_counts[s] = sector_counts.get(s, 0) + 1
    return {
        "total_chunks": len(_knowledge_base),
        "total_docs":   len({c["doc_id"] for c in _knowledge_base}),
        "sectors":      sector_counts,
        "last_updated": datetime.utcnow().isoformat(),
    }


# Add analytics endpoints

@app.post('/feedback')
async def submit_feedback(query_id: int, feedback: str):
    """Submit user feedback (up/down) for a query"""
    from db.supabase_client import get_supabase
    supabase = get_supabase()
    supabase.table("query_analytics").update({
        "user_feedback": feedback
    }).eq("id", query_id).execute()
    return {"status": "ok"}

@app.get('/analytics')
async def get_analytics():
    """Get query analytics (admin only)"""
    from db.supabase_client import get_supabase
    supabase = get_supabase()
    result = supabase.table("query_analytics").select("*").execute()
    return {"analytics": result.data}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)