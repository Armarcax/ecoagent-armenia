"""
EcoAgent Armenia — RAG Engine
Loads from all_docs.json (real Armenian laws) + Supabase hybrid (optional)
"""

import sys, os, hashlib, json, warnings
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

load_dotenv(dotenv_path=os.path.join(backend_dir, '.env'))

_knowledge_base: list[dict] = []


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start + chunk_size])
        start += chunk_size - overlap
    return chunks


def doc_id_hash(doc_id, chunk_idx: int) -> str:
    return hashlib.md5(f"{doc_id}_{chunk_idx}".encode()).hexdigest()


def load_knowledge_base():
    """Load from all_docs.json — real Armenian laws"""
    global _knowledge_base
    _knowledge_base.clear()

    # Try multiple paths for all_docs.json
    search_paths = [
        os.path.join(backend_dir, "all_docs.json"),
        os.path.join(backend_dir, "data", "all_docs.json"),
        os.path.join(os.path.dirname(backend_dir), "data", "all_docs.json"),
        os.path.join(backend_dir, "scraper", "combined_laws.json"),
        os.path.join(backend_dir, "scraped_laws.json"),
    ]

    docs = []
    loaded_from = None
    for path in search_paths:
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    docs = json.load(f)
                loaded_from = path
                break
            except Exception as e:
                print(f"[⚠️] Failed to load {path}: {e}")

    if not docs:
        print("[⚠️] all_docs.json not found — knowledge base empty")
        return

    # Deduplicate
    seen = set()
    unique_docs = []
    for d in docs:
        did = d.get("doc_id")
        if did not in seen:
            seen.add(did)
            unique_docs.append(d)

    # Build chunks
    for doc in unique_docs:
        body = doc.get("body") or doc.get("content") or doc.get("text") or ""
        chunks = chunk_text(body) if body else [doc.get("title", "")]
        for i, chunk in enumerate(chunks):
            _knowledge_base.append({
                "id":         doc_id_hash(doc["doc_id"], i),
                "doc_id":     doc["doc_id"],
                "title":      doc.get("title", ""),
                "chunk":      chunk,
                "sector":     doc.get("sector", "general"),
                "url":        doc.get("url", f"https://www.arlis.am/documentview.aspx?docid={doc['doc_id']}"),
                "doc_number": doc.get("doc_number", ""),
                "date":       doc.get("date", ""),
                "source":     doc.get("source", "arlis.am"),
            })

    print(f"[✓] KB loaded from {loaded_from}: {len(_knowledge_base)} chunks from {len(unique_docs)} docs")


def build_context(chunks: list[dict]) -> str:
    parts = []
    seen = set()
    for chunk in chunks:
        header = f"📋 {chunk['title']}"
        if chunk.get("doc_number"):
            header += f" ({chunk['doc_number']})"
        if chunk.get("url") and chunk.get("doc_id") not in seen:
            header += f"\n🔗 {chunk['url']}"
            seen.add(chunk["doc_id"])
        parts.append(f"{header}\n\n{chunk['chunk']}")
    return ("\n\n" + "─" * 50 + "\n\n").join(parts)


async def search_kb(query: str, sector: Optional[str] = None, top_k: int = 6) -> list[dict]:
    # 1. Try Supabase hybrid search
    try:
        from db.supabase_client import is_supabase_available, search_laws_hybrid
        if is_supabase_available():
            results = await search_laws_hybrid(query, sector, top_k)
            if results:
                return [
                    {
                        "id":         r.get("id"),
                        "doc_id":     r.get("law_id", r.get("doc_id")),
                        "title":      r.get("title", ""),
                        "chunk":      r.get("chunk_text", r.get("chunk", "")),
                        "sector":     r.get("sector", "general"),
                        "url":        r.get("url", ""),
                        "doc_number": r.get("doc_number", ""),
                        "date":       r.get("date", ""),
                    }
                    for r in results
                ]
    except Exception as e:
        print(f"[⚠️] Supabase search failed: {e}. Using in-memory.")

    # 2. In-memory keyword search (always works)
    if not _knowledge_base:
        load_knowledge_base()

    query_words = set(query.lower().split())
    scored = []
    for chunk in _knowledge_base:
        # Sector filter
        if sector and chunk["sector"] != sector and chunk["sector"] != "general":
            continue
        text = (chunk["title"] + " " + chunk["chunk"]).lower()
        score = sum(1 for w in query_words if len(w) > 2 and w in text)
        # Boost title matches
        if any(w in chunk["title"].lower() for w in query_words if len(w) > 2):
            score += 5
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]


async def query_ecoagent(question: str, sector: Optional[str] = None) -> dict:
    chunks = await search_kb(question, sector=sector)
    context = build_context(chunks) if chunks else "Տvyal harcit veraberyal teghekvatyun chi gtnvel."

    from llm_provider import generate_response
    user_msg = f"НARЦ: {question}\n\nCONTEXT:\n{context}\n\nPataskhanir maqur hayeren, karrucvackov:"

    answer_parts = []
    try:
        async for chunk in generate_response("", user_msg):
            answer_parts.append(chunk)
    except Exception as e:
        answer_parts = [f"⚠️ {e}"]

    answer = "".join(answer_parts)

    sources = []
    seen = set()
    for chunk in chunks:
        if chunk["doc_id"] not in seen:
            seen.add(chunk["doc_id"])
            sources.append({
                "title":      chunk["title"],
                "doc_number": chunk.get("doc_number", ""),
                "url":        chunk.get("url", ""),
                "sector":     chunk.get("sector", "general"),
                "date":       chunk.get("date", ""),
            })

    return {
        "answer":      answer,
        "sources":     sources,
        "sector":      sector or "general",
        "chunks_used": len(chunks),
        "timestamp":   datetime.utcnow().isoformat(),
    }


# Load on import
load_knowledge_base()

SEED_LAWS = []
