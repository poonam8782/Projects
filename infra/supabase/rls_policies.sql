-- Row Level Security (RLS) policies for multi-tenant isolation

-- Enable RLS on all tables
alter table if exists public.profiles enable row level security;
alter table if exists public.documents enable row level security;
alter table if exists public.embeddings enable row level security;
alter table if exists public.flashcards enable row level security;

-- Profiles
create policy if not exists "Users can view own profile"
  on public.profiles for select
  using (auth.uid() = id);

create policy if not exists "Users can insert own profile"
  on public.profiles for insert
  with check (auth.uid() = id);

create policy if not exists "Users can update own profile"
  on public.profiles for update
  using (auth.uid() = id)
  with check (auth.uid() = id);

create policy if not exists "Users can delete own profile"
  on public.profiles for delete
  using (auth.uid() = id);

-- Documents
create policy if not exists "Users can view own documents"
  on public.documents for select
  using (auth.uid() = user_id);

create policy if not exists "Users can insert own documents"
  on public.documents for insert
  with check (auth.uid() = user_id);

create policy if not exists "Users can update own documents"
  on public.documents for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy if not exists "Users can delete own documents"
  on public.documents for delete
  using (auth.uid() = user_id);

-- Embeddings (ownership via documents)
create policy if not exists "Users can view embeddings of own documents"
  on public.embeddings for select
  using (exists (
    select 1 from public.documents d
    where d.id = public.embeddings.document_id
      and d.user_id = auth.uid()
  ));

create policy if not exists "Users can insert embeddings for own documents"
  on public.embeddings for insert
  with check (exists (
    select 1 from public.documents d
    where d.id = public.embeddings.document_id
      and d.user_id = auth.uid()
  ));

create policy if not exists "Users can delete embeddings of own documents"
  on public.embeddings for delete
  using (exists (
    select 1 from public.documents d
    where d.id = public.embeddings.document_id
      and d.user_id = auth.uid()
  ));

-- No update policy for embeddings (immutable once created)

-- Flashcards
create policy if not exists "Users can view own flashcards"
  on public.flashcards for select
  using (auth.uid() = user_id);

create policy if not exists "Users can insert own flashcards"
  on public.flashcards for insert
  with check (auth.uid() = user_id);

create policy if not exists "Users can update own flashcards"
  on public.flashcards for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy if not exists "Users can delete own flashcards"
  on public.flashcards for delete
  using (auth.uid() = user_id);

-- Note: The backend uses SUPABASE_SERVICE_ROLE_KEY which bypasses RLS.
-- Frontend clients use the anon key; RLS is enforced using JWT claims (auth.uid()).