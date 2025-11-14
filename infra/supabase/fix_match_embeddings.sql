-- Quick fix: Update match_embeddings function to use correct parameter names
-- Run this in Supabase SQL Editor if you already ran the full migration

DROP FUNCTION IF EXISTS public.match_embeddings(vector, float, int, uuid);
DROP FUNCTION IF EXISTS public.match_embeddings(vector, uuid, int, float);

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

COMMENT ON FUNCTION public.match_embeddings IS 'Find similar text chunks using cosine similarity with 768-dim vectors';
