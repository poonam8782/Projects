-- ============================================================================
-- Fix Flashcard Cascade Deletion
-- This script updates the foreign key constraint to cascade delete flashcards
-- when their associated document is deleted.
-- ============================================================================

-- Step 1: Drop the existing constraint
ALTER TABLE public.flashcards 
DROP CONSTRAINT IF EXISTS flashcards_document_id_fkey;

-- Step 2: Add the new constraint with CASCADE
ALTER TABLE public.flashcards 
ADD CONSTRAINT flashcards_document_id_fkey 
FOREIGN KEY (document_id) 
REFERENCES public.documents(id) 
ON DELETE CASCADE;

-- Verify the change
SELECT 
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name,
    rc.delete_rule
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
JOIN information_schema.referential_constraints AS rc
    ON tc.constraint_name = rc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' 
    AND tc.table_name = 'flashcards'
    AND kcu.column_name = 'document_id';
