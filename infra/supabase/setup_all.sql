-- ============================================================================
-- Neura - Complete Database Setup
-- Run this entire script in Supabase SQL Editor to set up everything at once
-- ============================================================================

-- PART 1: EXTENSIONS AND TABLES (from schema.sql)
-- ============================================================================

-- Extensions
create extension if not exists vector;
create extension if not exists pgcrypto; -- for gen_random_uuid()

-- Profiles: 1:1 with auth.users
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text,
  email text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
comment on table public.profiles is 'User profiles linked to Supabase Auth users';

-- Documents: uploaded files with metadata and extracted text
create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  filename text not null,
  storage_path text not null,
  extracted_text text,
  size_bytes bigint,
  mime_type text,
  status text not null default 'uploaded',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
comment on table public.documents is 'Uploaded documents with metadata and extracted text';
create index if not exists idx_documents_user_id on public.documents(user_id);
create index if not exists idx_documents_status on public.documents(status);
create index if not exists idx_documents_user_created_at on public.documents(user_id, created_at desc);

-- Embeddings: text chunks and vectors for RAG
create table if not exists public.embeddings (
  id bigserial primary key,
  document_id uuid not null references public.documents(id) on delete cascade,
  chunk_index int not null,
  chunk_text text not null,
  embedding vector(1536) not null,
  token_count int,
  created_at timestamptz not null default now()
);
comment on table public.embeddings is 'Text chunks with 1536-dim embeddings for RAG';
create index if not exists idx_embeddings_vector on public.embeddings using ivfflat (embedding vector_cosine_ops) with (lists = 100);
create unique index if not exists idx_embeddings_unique_chunk on public.embeddings(document_id, chunk_index);

-- Flashcards: SM-2 spaced repetition fields
create table if not exists public.flashcards (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  document_id uuid references public.documents(id) on delete cascade,
  question text not null,
  answer text not null,
  efactor numeric(3,2) not null default 2.50,
  repetitions int not null default 0,
  interval int not null default 1,
  next_review timestamptz not null default now(),
  last_reviewed timestamptz,
  created_at timestamptz not null default now()
);
comment on table public.flashcards is 'Flashcards with SM-2 spaced repetition scheduling';
create index if not exists idx_flashcards_user_id on public.flashcards(user_id);
create index if not exists idx_flashcards_document_id on public.flashcards(document_id);
create index if not exists idx_flashcards_next_review on public.flashcards(user_id, next_review);

-- Updated_at trigger
create or replace function public.update_updated_at_column()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists update_profiles_updated_at on public.profiles;
create trigger update_profiles_updated_at
before update on public.profiles
for each row execute function public.update_updated_at_column();

drop trigger if exists update_documents_updated_at on public.documents;
create trigger update_documents_updated_at
before update on public.documents
for each row execute function public.update_updated_at_column();


-- PART 2: STORAGE BUCKETS
-- ============================================================================

-- Create uploads bucket
INSERT INTO storage.buckets (id, name, public)
VALUES ('uploads', 'uploads', false)
ON CONFLICT (id) DO NOTHING;

-- Create processed bucket
INSERT INTO storage.buckets (id, name, public)
VALUES ('processed', 'processed', false)
ON CONFLICT (id) DO NOTHING;


-- PART 3: ROW LEVEL SECURITY POLICIES
-- ============================================================================

-- Enable RLS on all tables
alter table public.profiles enable row level security;
alter table public.documents enable row level security;
alter table public.embeddings enable row level security;
alter table public.flashcards enable row level security;

-- Profiles RLS
drop policy if exists "Users can view own profile" on public.profiles;
create policy "Users can view own profile" on public.profiles
  for select using (auth.uid() = id);

drop policy if exists "Users can update own profile" on public.profiles;
create policy "Users can update own profile" on public.profiles
  for update using (auth.uid() = id);

drop policy if exists "Users can insert own profile" on public.profiles;
create policy "Users can insert own profile" on public.profiles
  for insert with check (auth.uid() = id);

-- Documents RLS
drop policy if exists "Users can view own documents" on public.documents;
create policy "Users can view own documents" on public.documents
  for select using (auth.uid() = user_id);

drop policy if exists "Users can insert own documents" on public.documents;
create policy "Users can insert own documents" on public.documents
  for insert with check (auth.uid() = user_id);

drop policy if exists "Users can update own documents" on public.documents;
create policy "Users can update own documents" on public.documents
  for update using (auth.uid() = user_id);

drop policy if exists "Users can delete own documents" on public.documents;
create policy "Users can delete own documents" on public.documents
  for delete using (auth.uid() = user_id);

-- Embeddings RLS (access via document ownership)
drop policy if exists "Users can view embeddings for own documents" on public.embeddings;
create policy "Users can view embeddings for own documents" on public.embeddings
  for select using (
    exists (
      select 1 from public.documents
      where documents.id = embeddings.document_id
      and documents.user_id = auth.uid()
    )
  );

drop policy if exists "Users can insert embeddings for own documents" on public.embeddings;
create policy "Users can insert embeddings for own documents" on public.embeddings
  for insert with check (
    exists (
      select 1 from public.documents
      where documents.id = embeddings.document_id
      and documents.user_id = auth.uid()
    )
  );

drop policy if exists "Users can delete embeddings for own documents" on public.embeddings;
create policy "Users can delete embeddings for own documents" on public.embeddings
  for delete using (
    exists (
      select 1 from public.documents
      where documents.id = embeddings.document_id
      and documents.user_id = auth.uid()
    )
  );

-- Flashcards RLS
drop policy if exists "Users can view own flashcards" on public.flashcards;
create policy "Users can view own flashcards" on public.flashcards
  for select using (auth.uid() = user_id);

drop policy if exists "Users can insert own flashcards" on public.flashcards;
create policy "Users can insert own flashcards" on public.flashcards
  for insert with check (auth.uid() = user_id);

drop policy if exists "Users can update own flashcards" on public.flashcards;
create policy "Users can update own flashcards" on public.flashcards
  for update using (auth.uid() = user_id);

drop policy if exists "Users can delete own flashcards" on public.flashcards;
create policy "Users can delete own flashcards" on public.flashcards
  for delete using (auth.uid() = user_id);

-- Storage RLS Policies for uploads bucket
drop policy if exists "Users can view own uploads" on storage.objects;
create policy "Users can view own uploads" on storage.objects
  for select using (
    bucket_id = 'uploads' AND (storage.foldername(name))[1] = auth.uid()::text
  );

drop policy if exists "Users can upload to own folder" on storage.objects;
create policy "Users can upload to own folder" on storage.objects
  for insert with check (
    bucket_id = 'uploads' AND (storage.foldername(name))[1] = auth.uid()::text
  );

drop policy if exists "Users can delete own uploads" on storage.objects;
create policy "Users can delete own uploads" on storage.objects
  for delete using (
    bucket_id = 'uploads' AND (storage.foldername(name))[1] = auth.uid()::text
  );

-- Storage RLS Policies for processed bucket
drop policy if exists "Users can view own processed files" on storage.objects;
create policy "Users can view own processed files" on storage.objects
  for select using (
    bucket_id = 'processed' AND (storage.foldername(name))[1] = auth.uid()::text
  );

drop policy if exists "Users can upload to own processed folder" on storage.objects;
create policy "Users can upload to own processed folder" on storage.objects
  for insert with check (
    bucket_id = 'processed' AND (storage.foldername(name))[1] = auth.uid()::text
  );

drop policy if exists "Users can delete own processed files" on storage.objects;
create policy "Users can delete own processed files" on storage.objects
  for delete using (
    bucket_id = 'processed' AND (storage.foldername(name))[1] = auth.uid()::text
  );


-- PART 4: VECTOR SEARCH FUNCTION
-- ============================================================================

create or replace function match_embeddings(
  query_embedding vector(1536),
  match_threshold float default 0.7,
  match_count int default 5,
  filter_document_id uuid default null
)
returns table (
  id bigint,
  document_id uuid,
  chunk_text text,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    e.id,
    e.document_id,
    e.chunk_text,
    1 - (e.embedding <=> query_embedding) as similarity
  from public.embeddings e
  where
    (filter_document_id is null or e.document_id = filter_document_id)
    and 1 - (e.embedding <=> query_embedding) > match_threshold
  order by e.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- ============================================================================
-- Setup Complete! 
-- Your database is now ready for Neura
-- ============================================================================
