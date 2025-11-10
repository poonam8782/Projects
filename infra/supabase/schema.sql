-- Supabase Database Schema for Neura
-- Enables pgvector and defines profiles, documents, embeddings, and flashcards tables

-- Extensions
create extension if not exists vector;
create extension if not exists pgcrypto; -- for gen_random_uuid()

-- Profiles: 1:1 with auth.users
-- User profiles linked to Supabase Auth users
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
  status text not null default 'uploaded', -- uploaded | extracted | embedded | failed
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
comment on table public.documents is 'Uploaded documents with metadata and extracted text';
create index if not exists idx_documents_user_id on public.documents(user_id);
create index if not exists idx_documents_status on public.documents(status);
-- Composite index for listings by user ordered by newest first
create index if not exists idx_documents_user_created_at on public.documents(user_id, created_at desc);
-- Constrain status to known values
alter table public.documents
  add constraint documents_status_check
  check (status in ('uploaded','extracted','embedded','failed'));

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
-- IVFFLAT index for cosine similarity; tune lists based on dataset size
create index if not exists idx_embeddings_vector on public.embeddings using ivfflat (embedding vector_cosine_ops) with (lists = 100);
-- Ensure one row per chunk per document
create unique index if not exists idx_embeddings_unique_chunk on public.embeddings(document_id, chunk_index);

-- Flashcards: SM-2 spaced repetition fields
create table if not exists public.flashcards (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  document_id uuid references public.documents(id) on delete set null,
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

-- updated_at trigger
create or replace function public.update_updated_at_column()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

-- Apply trigger to tables with updated_at
drop trigger if exists update_profiles_updated_at on public.profiles;
create trigger update_profiles_updated_at
before update on public.profiles
for each row execute function public.update_updated_at_column();

drop trigger if exists update_documents_updated_at on public.documents;
create trigger update_documents_updated_at
before update on public.documents
for each row execute function public.update_updated_at_column();
