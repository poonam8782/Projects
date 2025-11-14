# Supabase Database Setup Instructions

## Quick Setup via Supabase Dashboard

1. **Go to your Supabase project**:
   https://app.supabase.com/project/aozvuqzmcwhmrjsgwgop

2. **Navigate to SQL Editor**:
   - Click on "SQL Editor" in the left sidebar
   - Click "New query"

3. **Apply SQL files in this order**:

   ### Step 1: Create Tables
   Copy and paste the entire contents of `schema.sql` and run it

   ### Step 2: Set up Row Level Security
   Copy and paste the entire contents of `rls_policies.sql` and run it

   ### Step 3: Create Storage Buckets
   Copy and paste the entire contents of `storage_buckets.sql` and run it

   ### Step 4: Enable Vector Search
   Copy and paste the entire contents of `vector_search.sql` and run it

   ### Step 5 (Optional): Add Test Data
   Copy and paste the entire contents of `seed.sql` and run it

4. **Verify the setup**:
   - Go to "Table Editor" and you should see: `profiles`, `documents`, `embeddings`, `flashcards`
   - Go to "Storage" and you should see a bucket named `documents`

## Alternative: Using psql (Command Line)

If you prefer using the command line:

```bash
# Get your database connection string from Supabase dashboard
# Settings > Database > Connection string > Direct connection

# Then run:
cd /Users/dheerajjoshi/Desktop/Project/infra/supabase
psql "YOUR_CONNECTION_STRING_HERE" -f schema.sql
psql "YOUR_CONNECTION_STRING_HERE" -f rls_policies.sql
psql "YOUR_CONNECTION_STRING_HERE" -f storage_buckets.sql
psql "YOUR_CONNECTION_STRING_HERE" -f vector_search.sql
# Optional:
psql "YOUR_CONNECTION_STRING_HERE" -f seed.sql
```

## What Each File Does

- **schema.sql**: Creates all tables (profiles, documents, embeddings, flashcards)
- **rls_policies.sql**: Sets up Row Level Security to ensure users can only access their own data
- **storage_buckets.sql**: Creates the storage bucket for uploaded documents
- **vector_search.sql**: Creates the vector similarity search function for embeddings
- **seed.sql**: (Optional) Adds sample data for testing

## Troubleshooting

If you get errors about existing objects, it's safe - the scripts use `if not exists` clauses.

After setup, refresh your browser and the 500 errors should be resolved!
