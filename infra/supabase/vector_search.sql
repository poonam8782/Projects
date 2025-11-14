-- Sprint 3: Add match_embeddings RPC function for cosine similarity search used by the RAG chat endpoint.

CREATE OR REPLACE FUNCTION public.match_embeddings(
    query_embedding vector(768),
    target_document_id uuid,
    match_count int DEFAULT 5,
    similarity_threshold float DEFAULT 0.0
)
RETURNS TABLE (
    id bigint,
    document_id uuid,
    chunk_index int,
    chunk_text text,
    similarity float
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        e.id,
        e.document_id,
        e.chunk_index,
        e.chunk_text,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM public.embeddings AS e
    WHERE e.document_id = target_document_id
      AND 1 - (e.embedding <=> query_embedding) >= similarity_threshold
    ORDER BY e.embedding <=> query_embedding ASC
    LIMIT match_count;
$$;

-- Note: The <=> operator computes cosine distance (0 = identical, 2 = opposite).
-- Similarity is derived as 1 - distance to produce a score in [0, 1], where higher is more similar.
-- The existing IVFFLAT index on embeddings.embedding accelerates this query automatically.

-- Example: Find top 5 most similar chunks for a query embedding
-- SELECT * FROM match_embeddings(
--   '[0.1, 0.2, ..., 0.0]'::vector(768),  -- query embedding
--   'doc-uuid'::uuid,                      -- document to search within
--   5,                                     -- top 5 results
--   0.3                                    -- minimum similarity threshold
-- );
