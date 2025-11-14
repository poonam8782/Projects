# Embedding Dimension Migration (1536 → 768)

## Problem
The application was configured to use 1536-dimensional embeddings, but Gemini's `models/embedding-001` actually produces 768-dimensional vectors. This caused a dimension mismatch error when trying to generate embeddings.

## Solution
Updated the entire system to use 768 dimensions, which is what Gemini's embedding model actually produces.

## Changes Made

### 1. Backend Configuration
- Updated `apps/backend/app/core/config.py`: Changed default embedding dimensions from 1536 to 768
- Updated `apps/backend/app/services/gemini_client.py`: Updated constants and documentation
- Updated `apps/backend/app/routes/embed.py`: Changed embedding generation call to use 768 dimensions

### 2. Database Schema
- Created migration script: `infra/supabase/migrate_embeddings_768.sql`
- Updated `infra/supabase/setup_all.sql`: Changed embeddings table to use `vector(768)`
- Updated `infra/supabase/vector_search.sql`: Changed match_embeddings function to accept `vector(768)`

## Migration Steps

### Option 1: Fresh Database (Recommended for Development)
If you're in development and can reset your database:

1. Run the complete setup with updated dimensions:
   ```bash
   # In Supabase SQL Editor
   # Copy and run: infra/supabase/setup_all.sql
   ```

### Option 2: Migrate Existing Database
If you have existing data that you want to preserve (except embeddings):

1. **Backup your database** (if you have important data)

2. Run the migration script in Supabase SQL Editor:
   ```bash
   # Copy and run: infra/supabase/migrate_embeddings_768.sql
   ```

3. **Important**: All existing embeddings will be deleted because they have incompatible dimensions. Documents will need to be re-embedded.

4. After migration, re-embed all documents:
   - Delete and re-upload documents, OR
   - Call the `/embed` endpoint for each existing document

### Option 3: Using Supabase CLI
If you're using local Supabase development:

```bash
# Stop Supabase
supabase stop

# Reset database
supabase db reset

# The new schema (with 768 dimensions) will be applied automatically
```

## Verification

After migration, verify the changes:

1. Check the embeddings table structure:
   ```sql
   SELECT column_name, data_type 
   FROM information_schema.columns 
   WHERE table_name = 'embeddings' AND column_name = 'embedding';
   ```
   Should return: `embedding | USER-DEFINED (vector(768))`

2. Check the match_embeddings function:
   ```sql
   SELECT routine_name, data_type 
   FROM information_schema.parameters 
   WHERE specific_name LIKE 'match_embeddings%' 
   AND parameter_name = 'query_embedding';
   ```

3. Test embedding generation:
   - Upload a document through the web interface
   - Check that embeddings are generated without dimension mismatch errors

## Important Notes

- **All existing embeddings will be deleted** during migration because 1536-dim and 768-dim vectors are incompatible
- Documents will need to be re-embedded after migration
- The embedding quality should not be significantly affected as 768 dimensions is sufficient for most semantic search tasks
- This change aligns the system with what Gemini's API actually provides

## Rollback (Not Recommended)

If you need to rollback to 1536 dimensions, you would need to:
1. Use a different embedding model that supports 1536 dimensions (not Gemini)
2. Update all the same files back to 1536
3. Re-run the schema setup
4. Re-embed all documents

However, this is not recommended as Gemini's embedding-001 is optimized for 768 dimensions.
