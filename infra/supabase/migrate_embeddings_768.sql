-- Migration: Update embeddings table to use 768 dimensions instead of 1536
-- This migration is needed because Gemini's embedding-001 model produces 768-dimensional vectors

-- Step 1: Drop the existing vector index
DROP INDEX IF EXISTS idx_embeddings_vector;

-- Step 2: Drop the match_embeddings function (depends on vector(1536))
DROP FUNCTION IF EXISTS match_embeddings(vector, float, int, uuid);

-- Step 3: Create a new embeddings table with 768 dimensions
CREATE TABLE IF NOT EXISTS public.embeddings_new (
  id bigserial primary key,
  document_id uuid not null references public.documents(id) on delete cascade,
  chunk_index int not null,
  chunk_text text not null,
  embedding vector(768) not null,
  token_count int,
  created_at timestamptz not null default now()
);

-- Step 4: Copy data if any exists (only metadata, not embeddings since dimensions are incompatible)
-- Note: Existing embeddings will need to be regenerated
-- INSERT INTO public.embeddings_new (document_id, chunk_index, chunk_text, token_count, created_at)
-- SELECT document_id, chunk_index, chunk_text, token_count, created_at FROM public.embeddings;

-- Step 5: Drop the old embeddings table
DROP TABLE IF EXISTS public.embeddings CASCADE;

-- Step 6: Rename the new table
ALTER TABLE public.embeddings_new RENAME TO embeddings;

-- Step 7: Add comment
COMMENT ON TABLE public.embeddings IS 'Text chunks with 768-dim embeddings for RAG';

-- Step 8: Create the vector index with 768 dimensions
CREATE INDEX IF NOT EXISTS idx_embeddings_vector 
  ON public.embeddings 
  USING ivfflat (embedding vector_cosine_ops) 
  WITH (lists = 100);

-- Step 9: Create unique index
CREATE UNIQUE INDEX IF NOT EXISTS idx_embeddings_unique_chunk 
  ON public.embeddings(document_id, chunk_index);

-- Step 10: Recreate the match_embeddings function with 768 dimensions
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

-- Step 11: Enable RLS
ALTER TABLE public.embeddings ENABLE ROW LEVEL SECURITY;

-- Step 12: Recreate RLS policies
DROP POLICY IF EXISTS "Users can view embeddings for own documents" ON public.embeddings;
CREATE POLICY "Users can view embeddings for own documents" ON public.embeddings
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM public.documents
      WHERE documents.id = embeddings.document_id
      AND documents.user_id = auth.uid()
    )
  );

DROP POLICY IF EXISTS "Users can insert embeddings for own documents" ON public.embeddings;
CREATE POLICY "Users can insert embeddings for own documents" ON public.embeddings
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.documents
      WHERE documents.id = embeddings.document_id
      AND documents.user_id = auth.uid()
    )
  );

DROP POLICY IF EXISTS "Users can delete embeddings for own documents" ON public.embeddings;
CREATE POLICY "Users can delete embeddings for own documents" ON public.embeddings
  FOR DELETE USING (
    EXISTS (
      SELECT 1 FROM public.documents
      WHERE documents.id = embeddings.document_id
      AND documents.user_id = auth.uid()
    )
  );

-- Migration complete!
-- Note: All existing embeddings have been deleted. Documents will need to be re-embedded.
