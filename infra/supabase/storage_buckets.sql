-- Supabase Storage Buckets and RLS Policies Migration
--
-- Creates buckets for user uploads and AI-generated processed content
-- with row-level security policies enforcing per-user access.
--
-- Buckets:
--   uploads/   - User-uploaded source documents (Sprint 1)
--   processed/ - AI-generated content (notes, mindmaps, exports) (Sprint 4+)
--
-- Idempotent: Uses ON CONFLICT DO NOTHING for bucket creation.

-- Create uploads bucket (if not already created)
INSERT INTO storage.buckets (id, name, public)
VALUES ('uploads', 'uploads', false)
ON CONFLICT (id) DO NOTHING;
-- Bucket for user-uploaded files (PDF, DOCX, TXT, images)

-- Create processed bucket
INSERT INTO storage.buckets (id, name, public)
VALUES ('processed', 'processed', false)
ON CONFLICT (id) DO NOTHING;
-- Bucket for AI-generated content (notes, mindmaps, flashcard exports)

-- RLS Policies for uploads bucket
DO $$ BEGIN
IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND policyname = 'Users can view own uploads'
) THEN
    CREATE POLICY "Users can view own uploads" ON storage.objects FOR SELECT USING (
      bucket_id = 'uploads' AND (storage.foldername(name))[1] = auth.uid()::text
    );
END IF;
END $$;
DO $$ BEGIN
IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND policyname = 'Users can upload to own folder'
) THEN
    CREATE POLICY "Users can upload to own folder" ON storage.objects FOR INSERT WITH CHECK (
      bucket_id = 'uploads' AND (storage.foldername(name))[1] = auth.uid()::text
    );
END IF;
END $$;
DO $$ BEGIN
IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND policyname = 'Users can delete own uploads'
) THEN
    CREATE POLICY "Users can delete own uploads" ON storage.objects FOR DELETE USING (
      bucket_id = 'uploads' AND (storage.foldername(name))[1] = auth.uid()::text
    );
END IF;
END $$;

-- RLS Policies for processed bucket
DO $$ BEGIN
IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND policyname = 'Users can view own processed files'
) THEN
    CREATE POLICY "Users can view own processed files" ON storage.objects FOR SELECT USING (
      bucket_id = 'processed' AND (storage.foldername(name))[1] = auth.uid()::text
    );
END IF;
END $$;
DO $$ BEGIN
IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND policyname = 'Users can create processed files'
) THEN
    CREATE POLICY "Users can create processed files" ON storage.objects FOR INSERT WITH CHECK (
      bucket_id = 'processed' AND (storage.foldername(name))[1] = auth.uid()::text
    );
END IF;
END $$;
DO $$ BEGIN
IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND policyname = 'Users can update own processed files'
) THEN
    CREATE POLICY "Users can update own processed files" ON storage.objects FOR UPDATE USING (
      bucket_id = 'processed' AND (storage.foldername(name))[1] = auth.uid()::text
    );
END IF;
END $$;
DO $$ BEGIN
IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND policyname = 'Users can delete own processed files'
) THEN
    CREATE POLICY "Users can delete own processed files" ON storage.objects FOR DELETE USING (
      bucket_id = 'processed' AND (storage.foldername(name))[1] = auth.uid()::text
    );
END IF;
END $$;

-- Verification queries (run manually during debugging):
-- SELECT * FROM storage.buckets;
-- SELECT * FROM storage.objects WHERE bucket_id = 'processed';
