#!/bin/bash
# Quick migration script to update embeddings to 768 dimensions

echo "=================================="
echo "Embedding Dimension Migration"
echo "1536 → 768 dimensions"
echo "=================================="
echo ""
echo "This will:"
echo "1. Drop existing embeddings table and data"
echo "2. Recreate with 768 dimensions"
echo "3. Update the match_embeddings function"
echo ""
echo "⚠️  WARNING: All existing embeddings will be deleted!"
echo "   Documents will need to be re-embedded."
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Migration cancelled."
    exit 1
fi

echo ""
echo "Please run the following SQL in your Supabase SQL Editor:"
echo ""
echo "Copy and paste the contents of:"
echo "  infra/supabase/migrate_embeddings_768.sql"
echo ""
echo "Or run it via Supabase CLI:"
echo "  supabase db execute -f infra/supabase/migrate_embeddings_768.sql"
echo ""
echo "After migration, restart your backend server."
