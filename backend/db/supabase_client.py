"""
EcoAgent Armenia — Optional Supabase client
Uses anon key (read-only). Falls back silently if not configured.
"""

import os
from typing import Optional, List

_supabase = None
_supabase_available = False


def init_supabase():
    global _supabase, _supabase_available
    if _supabase is not None:
        return
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        # Try service key first, fall back to anon key
        key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
        if url and key:
            _supabase = create_client(url, key)
            _supabase_available = True
            print("[✓] Supabase connected")
        else:
            print("[i] Supabase not configured — in-memory KB active")
    except Exception as e:
        print(f"[i] Supabase skip: {e}")


def is_supabase_available() -> bool:
    return _supabase_available


def get_supabase_client():
    return _supabase


async def search_laws_hybrid(
    query: str,
    sector: Optional[str] = None,
    top_k: int = 6,
) -> List[dict]:
    if not _supabase_available or _supabase is None:
        return []
    try:
        from embeddings import get_embedding
        embedding = await get_embedding(query)
        result = _supabase.rpc("hybrid_search", {
            "query_embedding": embedding,
            "query_text":      query,
            "sector_filter":   sector,
            "top_k":           top_k,
        }).execute()
        return result.data or []
    except Exception as e:
        print(f"[⚠️] Hybrid search error: {e}")
        return []
