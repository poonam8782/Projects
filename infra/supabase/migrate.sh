#!/bin/bash
# Apply Supabase database migrations: schema, RLS, and optional seeds
# Requires Supabase CLI (npm install -g supabase) or psql client
# Reads credentials from project .env

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

ENV_FILE="$PROJECT_ROOT/.env"
if [[ -f "$ENV_FILE" ]]; then
  echo "Loading environment from .env"
  # shellcheck disable=SC1090
  source "$ENV_FILE"
else
  echo "Warning: .env not found at $ENV_FILE. Ensure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set in the environment." >&2
fi

require_var() { : "${!1:?$1 is required}"; }
require_var SUPABASE_URL
require_var SUPABASE_SERVICE_ROLE_KEY
require_var SUPABASE_DB_URL

# Extract project ref from SUPABASE_URL (https://<ref>.supabase.co)
PROJECT_REF=$(echo "$SUPABASE_URL" | sed -E 's#https?://([^.]+)\.supabase\.co.*#\1#') || true
echo "Using Supabase project ref: $PROJECT_REF"

apply_sql() {
  local file="$1"
  echo "Applying $(basename "$file")..."
  # Prefer Supabase CLI if logged in and linked; fallback to psql over pooled endpoint
  if command -v supabase >/dev/null 2>&1; then
    # Try using db remote commit via psql connection string if available
    # Supabase CLI doesn't execute arbitrary SQL files remotely without migrations,
    # so we fallback to psql if PGPASSWORD/connection string is provided.
    :
  fi

  if command -v psql >/dev/null 2>&1; then
    echo "Using explicit DB URL from SUPABASE_DB_URL"
    psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f "$file"
  else
    echo "Error: psql is not installed. Install PostgreSQL client or use Supabase Studio SQL editor to run: $file" >&2
    exit 1
  fi
}

pushd "$SCRIPT_DIR" >/dev/null
apply_sql "schema.sql"
apply_sql "rls_policies.sql"
apply_sql "vector_search.sql"
if command -v psql >/dev/null 2>&1; then
  POLICY_EXISTS=$(psql "$SUPABASE_DB_URL" -t -A -c "SELECT 1 FROM pg_policies WHERE policyname='Users can view own processed files' LIMIT 1" || true)
  if [[ -z "$POLICY_EXISTS" ]]; then
    apply_sql "storage_buckets.sql"
  else
    echo "Skipping storage_buckets.sql (policies already exist)"
  fi
else
  apply_sql "storage_buckets.sql"
fi

# Apply optional conversations table migration (Comment 6)
if [[ -f "conversations.sql" ]]; then
  echo "Applying conversations table (optional, for chat history persistence)..."
  apply_sql "conversations.sql"
else
  echo "Skipping conversations.sql (file not found, chat history export will be unavailable)"
fi

if [[ "${1:-}" == "--seed" ]]; then
  apply_sql "seed.sql"
fi
popd >/dev/null

echo "✅ Migrations applied successfully (schema, RLS policies, vector search functions, storage buckets, conversations [optional])!"
echo "Tip: Run with --seed to insert development seed data."
echo "Alternate workflow (recommended for production):"
echo "  supabase link --project-ref $PROJECT_REF && supabase db push"
