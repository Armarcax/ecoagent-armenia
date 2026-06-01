"""Supabase client for EcoAgent Armenia"""

import os
from supabase import create_client, Client
from typing import Optional

_supabase: Optional[Client] = None

def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        _supabase = create_client(url, key)
    return _supabase

async def init_db():
    """Initialize database with seed data"""
    supabase = get_supabase()
    # Check if laws exist
    result = supabase.table("laws").select("id", count="exact").limit(1).execute()
    if result.count == 0:
        from rag.rag_engine import SEED_LAWS
        for law in SEED_LAWS:
            await insert_law(law)

async def insert_law(law_data: dict):
    """Insert law and its chunks with embeddings"""
    supabase = get_supabase()

    # Insert law
    law_result = supabase.table("laws").insert({
        "doc_id": law_data["doc_id"],
        "doc_number": law_data.get("doc_number", ""),
        "title": law_data["title"],
        "body": law_data.get("body", ""),
        "sector": law_data.get("sector", "general"),
        "url": law_data.get("url", ""),
        "date": law_data.get("date"),
        "source": law_data.get("source", "arlis.am"),
    }).execute()

    law_db_id = law_result.data[0]["id"]

    # Generate embeddings for chunks
    from rag.embeddings import get_embedding
    from rag.rag_engine import chunk_text

    chunks = chunk_text(law_data.get("body", ""))
    for i, chunk in enumerate(chunks):
        embedding = await get_embedding(chunk)
        supabase.table("law_chunks").insert({
            "law_id": law_db_id,
            "chunk_text": chunk,
            "embedding": embedding,
            "chunk_index": i,
        }).execute()

async def search_laws(query: str, sector: Optional[str] = None, top_k: int = 6):
    """Hybrid search using pgvector"""
    from rag.embeddings import get_embedding

    supabase = get_supabase()
    query_embedding = await get_embedding(query)

    result = supabase.rpc("hybrid_search", {
        "query_embedding": query_embedding,
        "query_text": query,
        "sector_filter": sector,
        "top_k": top_k,
    }).execute()

    return result.data
