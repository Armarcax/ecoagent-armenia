-- ══════════════════════════════════════════════════════════════
-- EcoAgent Armenia — Supabase Schema
-- Supabase SQL Editor-um gratsir
-- ══════════════════════════════════════════════════════════════

-- 1. pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Laws table
CREATE TABLE IF NOT EXISTS laws (
    id         SERIAL PRIMARY KEY,
    doc_id     INTEGER UNIQUE NOT NULL,
    doc_number VARCHAR(50),
    title      TEXT NOT NULL,
    body       TEXT,
    sector     VARCHAR(50) DEFAULT 'general',
    url        TEXT,
    date       DATE,
    source     VARCHAR(50) DEFAULT 'arlis.am',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Chunks table with embeddings (384-dim for all-MiniLM-L6-v2)
CREATE TABLE IF NOT EXISTS law_chunks (
    id          SERIAL PRIMARY KEY,
    law_id      INTEGER REFERENCES laws(id) ON DELETE CASCADE,
    chunk_text  TEXT NOT NULL,
    embedding   VECTOR(384),
    chunk_index INTEGER,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 4. HNSW index for fast cosine similarity search
CREATE INDEX IF NOT EXISTS idx_law_chunks_embedding
ON law_chunks USING hnsw (embedding vector_cosine_ops);

-- 5. Sector index
CREATE INDEX IF NOT EXISTS idx_laws_sector ON laws (sector);

-- 6. Hybrid search function
CREATE OR REPLACE FUNCTION hybrid_search(
    query_embedding VECTOR(384),
    query_text      TEXT,
    sector_filter   VARCHAR(50) DEFAULT NULL,
    top_k           INTEGER     DEFAULT 6
)
RETURNS TABLE (
    id          INTEGER,
    law_id      INTEGER,
    chunk_text  TEXT,
    title       TEXT,
    doc_number  VARCHAR(50),
    url         TEXT,
    sector      VARCHAR(50),
    similarity  FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        lc.id,
        lc.law_id,
        lc.chunk_text,
        l.title,
        l.doc_number,
        l.url,
        l.sector,
        -- Hybrid score: 70% vector + 30% keyword
        (1 - (lc.embedding <=> query_embedding)) * 0.7 +
        CASE
            WHEN lc.chunk_text ILIKE '%' || query_text || '%' THEN 0.3
            WHEN l.title       ILIKE '%' || query_text || '%' THEN 0.2
            ELSE 0.0
        END AS similarity
    FROM law_chunks lc
    JOIN laws l ON lc.law_id = l.id
    WHERE (sector_filter IS NULL OR l.sector = sector_filter OR l.sector = 'general')
    ORDER BY similarity DESC
    LIMIT top_k;
END;
$$;
