-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Laws table
CREATE TABLE IF NOT EXISTS laws (
    id SERIAL PRIMARY KEY,
    doc_id INTEGER UNIQUE NOT NULL,
    doc_number VARCHAR(50),
    title TEXT NOT NULL,
    body TEXT,
    sector VARCHAR(50) DEFAULT 'general',
    url TEXT,
    date DATE,
    source VARCHAR(50) DEFAULT 'arlis.am',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Chunks table with embeddings
CREATE TABLE IF NOT EXISTS law_chunks (
    id SERIAL PRIMARY KEY,
    law_id INTEGER REFERENCES laws(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    embedding VECTOR(384),  -- all-MiniLM-L6-v2 dimensions
    chunk_index INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create HNSW index for fast similarity search
CREATE INDEX IF NOT EXISTS idx_law_chunks_embedding
ON law_chunks USING hnsw (embedding vector_cosine_ops);

-- Analytics table
CREATE TABLE IF NOT EXISTS query_analytics (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    sector VARCHAR(50),
    sources_used INTEGER,
    response_time_ms INTEGER,
    user_feedback VARCHAR(10),  -- 'up' or 'down'
    created_at TIMESTAMP DEFAULT NOW()
);

-- Function for hybrid search (keyword + vector)
CREATE OR REPLACE FUNCTION hybrid_search(
    query_embedding VECTOR(384),
    query_text TEXT,
    sector_filter VARCHAR(50) DEFAULT NULL,
    top_k INTEGER DEFAULT 6
)
RETURNS TABLE (
    id INTEGER,
    law_id INTEGER,
    chunk_text TEXT,
    title TEXT,
    doc_number VARCHAR(50),
    url TEXT,
    sector VARCHAR(50),
    similarity FLOAT
) AS $$
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
        (1 - (lc.embedding <=> query_embedding)) * 0.7 +
        (CASE
            WHEN lc.chunk_text ILIKE '%' || query_text || '%' THEN 0.3
            WHEN l.title ILIKE '%' || query_text || '%' THEN 0.2
            ELSE 0.0
        END) AS similarity
    FROM law_chunks lc
    JOIN laws l ON lc.law_id = l.id
    WHERE (sector_filter IS NULL OR l.sector = sector_filter OR l.sector = 'general')
    ORDER BY similarity DESC
    LIMIT top_k;
END;
$$ LANGUAGE plpgsql;
