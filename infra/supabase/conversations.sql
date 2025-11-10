-- Chat Conversation History Table (Optional - Sprint 6+)
--
-- This migration adds a conversations table for persisting chat history.
-- This is optional for Sprint 6 - the export endpoint works without it by exporting
-- only persisted data (metadata, notes, flashcards). If this migration is applied,
-- chat history can be included in exports.
--
-- To enable chat history persistence:
-- 1. Apply this migration
-- 2. Update the chat endpoint (apps/backend/app/routes/chat.py) to insert messages
--    into this table after each exchange
-- 3. Chat history will then be available for export via the /export endpoint

-- Create conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    role text NOT NULL CHECK (role IN ('user', 'model')),
    content text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Add indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_conversations_document_id ON conversations(document_id, created_at);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);

-- Add table comment
COMMENT ON TABLE conversations IS 'Chat conversation history for export and analytics (optional, Sprint 6+)';

-- Enable Row Level Security
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can view their own conversations
CREATE POLICY "Users can view own conversations" ON conversations
    FOR SELECT
    USING (auth.uid() = user_id);

-- RLS Policy: Users can insert their own conversations
CREATE POLICY "Users can insert own conversations" ON conversations
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- RLS Policy: Users can delete their own conversations
CREATE POLICY "Users can delete own conversations" ON conversations
    FOR DELETE
    USING (auth.uid() = user_id);

-- Note: This table is optional. If not created, the export endpoint will skip chat
-- history and export only document metadata, notes, and flashcards. To enable chat
-- history persistence, the chat endpoint (apps/backend/app/routes/chat.py) would need
-- to be updated to insert messages into this table after each exchange.
