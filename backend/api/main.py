"""
EcoAgent Armenia — FastAPI Backend
Google Gemini (free) → Groq (free) → Local fallback
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

from rag.rag_engine import query_ecoagent, search_kb, build_context, load_knowledge_base
from llm_provider import generate_response

app = FastAPI(title="EcoAgent Armenia API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    load_knowledge_base()
    # Optional Supabase
    try:
        from db.supabase_client import init_supabase
        init_supabase()
    except Exception:
        pass
    print("[✓] EcoAgent Armenia v1.1 started")


class QueryRequest(BaseModel):
    question: str
    sector:   Optional[str] = None


class QueryResponse(BaseModel):
    answer:      str
    sources:     list[dict]
    sector:      str
    chunks_used: int
    timestamp:   str


@app.get("/")
async def root():
    from rag.rag_engine import _knowledge_base
    return {
        "name":      "EcoAgent Armenia",
        "version":   "1.1.0",
        "status":    "ok",
        "kb_chunks": len(_knowledge_base),
        "providers": os.getenv("LLM_PROVIDER_PRIORITY", "google,groq,none"),
    }


@app.get("/health")
async def health():
    from rag.rag_engine import _knowledge_base
    return {"status": "ok", "kb_chunks": len(_knowledge_base)}


@app.get("/health/db")
async def health_db():
    try:
        from db.supabase_client import is_supabase_available
        return {"supabase_available": is_supabase_available()}
    except Exception:
        return {"supabase_available": False}


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(400, detail="Հarczit partar che")
    result = await query_ecoagent(req.question, req.sector)
    return QueryResponse(**result)


@app.post("/query/stream")
async def query_stream(req: QueryRequest):
    chunks = await search_kb(req.question, sector=req.sector, top_k=6)
    context = build_context(chunks) if chunks else "Tvyal harcit veraberyal teghekvatyun chi gtnvel."
    user_msg = f"НARЦ: {req.question}\n\nCONTEXT:\n{context}\n\nPataskhanir maqur hayeren, karrucvackov:"

    async def generate():
        # Send sources first
        sources = []
        seen = set()
        for chunk in chunks:
            if chunk["doc_id"] not in seen:
                seen.add(chunk["doc_id"])
                sources.append({
                    "title":      chunk["title"],
                    "url":        chunk.get("url", ""),
                    "doc_number": chunk.get("doc_number", ""),
                })
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

        try:
            async for text_chunk in generate_response("", user_msg, stream=True):
                yield f"data: {json.dumps({'type': 'text', 'content': text_chunk})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'text', 'content': f'⚠️ Сkhал: {e}'})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/sectors")
async def get_sectors():
    return {"sectors": [
        {"id": "construction",  "name": "Շinararutyun",           "icon": "🏗️"},
        {"id": "mining",        "name": "Hanqardyunaberdutyun",    "icon": "⛏️"},
        {"id": "forestry",      "name": "Antarrtntesatyun",        "icon": "🌲"},
        {"id": "land",          "name": "Hoghayin Orrensgirk",     "icon": "🏔️"},
        {"id": "agriculture",   "name": "Gyughatntesatyun",        "icon": "🌾"},
        {"id": "energy",        "name": "Energetika",              "icon": "☀️"},
        {"id": "water",         "name": "Djrrayin Hayerrr",        "icon": "💧"},
        {"id": "biodiversity",  "name": "Bnutyun Pahpanutyun",     "icon": "🐾"},
        {"id": "air",           "name": "Od/Djur Aghtotum",        "icon": "💨"},
        {"id": "waste",         "name": "Taphonn Veramshakum",     "icon": "♻️"},
        {"id": "environment",   "name": "Bnapahpanutyun",          "icon": "🌿"},
        {"id": "licensing",     "name": "Licenzianерр/Tuylattvutyun", "icon": "📜"},
        {"id": "esg",           "name": "ESG Reporting",           "icon": "📊"},
    ]}


@app.get("/laws")
async def get_laws(sector: Optional[str] = None):
    from rag.rag_engine import _knowledge_base
    seen = set()
    laws = []
    for chunk in _knowledge_base:
        if chunk["doc_id"] not in seen:
            if not sector or chunk["sector"] == sector or sector == "all":
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
    from rag.rag_engine import _knowledge_base
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
