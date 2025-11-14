-- Seed data for local development ONLY. Do not run in production.
-- Idempotent inserts using ON CONFLICT DO NOTHING.

-- Test user profile (linked to auth.users). Only create profile if auth user exists.
insert into public.profiles (id, full_name, email)
select '00000000-0000-0000-0000-000000000001', 'Test User', 'test@neura.ai'
where exists (
  select 1 from auth.users where id = '00000000-0000-0000-0000-000000000001'
)
on conflict (id) do nothing;

-- Sample document for the test user
insert into public.documents (id, user_id, filename, storage_path, extracted_text, size_bytes, mime_type, status)
select gen_random_uuid(),
  '00000000-0000-0000-0000-000000000001',
  'sample-document.txt',
  'uploads/test/sample.txt',
  'This is a sample document for testing the Neura system. It contains several sentences that will be chunked and embedded for retrieval augmented generation (RAG) queries.',
  1024,
  'text/plain',
  'extracted'
where exists (
  select 1 from auth.users where id = '00000000-0000-0000-0000-000000000001'
)
on conflict do nothing;

-- Retrieve the sample document id for embedding and flashcards (assuming latest for user)
with doc as (
  select id from public.documents
  where user_id = '00000000-0000-0000-0000-000000000001'
  order by created_at desc limit 1
)
-- Sample embeddings (placeholder vectors). Replace with real 1536-dim vectors in practice.
insert into public.embeddings (document_id, chunk_index, chunk_text, embedding, token_count)
select doc.id, 0,
  'This is a sample document for testing the Neura system.',
  ('[' || repeat('0.1,',1535) || '0.1]')::vector(1536),
  100
from doc
where exists (
  select 1 from auth.users where id = '00000000-0000-0000-0000-000000000001'
)
on conflict do nothing;

with doc as (
  select id from public.documents
  where user_id = '00000000-0000-0000-0000-000000000001'
  order by created_at desc limit 1
)
insert into public.embeddings (document_id, chunk_index, chunk_text, embedding, token_count)
select doc.id, 1,
  'It contains several sentences that will be chunked and embedded.',
  ('[' || repeat('0.2,',1535) || '0.2]')::vector(1536),
  150
from doc
where exists (
  select 1 from auth.users where id = '00000000-0000-0000-0000-000000000001'
)
on conflict do nothing;

with doc as (
  select id from public.documents
  where user_id = '00000000-0000-0000-0000-000000000001'
  order by created_at desc limit 1
)
insert into public.embeddings (document_id, chunk_index, chunk_text, embedding, token_count)
select doc.id, 2,
  'Retrieval augmented generation (RAG) queries will use cosine similarity.',
  ('[' || repeat('0.05,',1535) || '0.05]')::vector(1536),
  80
from doc
where exists (
  select 1 from auth.users where id = '00000000-0000-0000-0000-000000000001'
)
on conflict do nothing;

-- Sample flashcards
with doc as (
  select id from public.documents
  where user_id = '00000000-0000-0000-0000-000000000001'
  order by created_at desc limit 1
)
insert into public.flashcards (user_id, document_id, question, answer)
select '00000000-0000-0000-0000-000000000001', doc.id, 'What is Neura?', 'An AI-powered note-making platform.'
from doc
where exists (
  select 1 from auth.users where id = '00000000-0000-0000-0000-000000000001'
)
on conflict do nothing;

with doc as (
  select id from public.documents
  where user_id = '00000000-0000-0000-0000-000000000001'
  order by created_at desc limit 1
)
insert into public.flashcards (user_id, document_id, question, answer)
select '00000000-0000-0000-0000-000000000001', doc.id, 'What does RAG stand for?', 'Retrieval Augmented Generation.'
from doc
where exists (
  select 1 from auth.users where id = '00000000-0000-0000-0000-000000000001'
)
on conflict do nothing;

with doc as (
  select id from public.documents
  where user_id = '00000000-0000-0000-0000-000000000001'
  order by created_at desc limit 1
)
insert into public.flashcards (user_id, document_id, question, answer)
select '00000000-0000-0000-0000-000000000001', doc.id, 'What indexing method is used?', 'IVFFLAT vector index with cosine similarity.'
from doc
where exists (
  select 1 from auth.users where id = '00000000-0000-0000-0000-000000000001'
)
on conflict do nothing;

-- Verification (uncomment to inspect after seeding)
-- select * from public.profiles;
-- select * from public.documents;
-- select * from public.embeddings limit 5;
-- select * from public.flashcards;
