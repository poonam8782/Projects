import os
import sys
from pathlib import Path
from supabase import create_client


def _load_env():
    """Load .env file manually (no external dependencies) if present.

    Priority: local backend .env then project root .env.
    Does not override already-set environment variables.
    """
    candidates = [
        Path(__file__).resolve().parent.parent / ".env",  # apps/backend/.env
        Path(__file__).resolve().parents[3] / ".env",      # project root .env
    ]
    for candidate in candidates:
        if candidate.is_file():
            try:
                with candidate.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" not in line:
                            continue
                        name, value = line.split("=", 1)
                        name = name.strip()
                        value = value.strip()
                        if name and value and name not in os.environ:
                            os.environ[name] = value
                break  # stop after first found
            except Exception as e:  # noqa: BLE001
                print(f"Warning: failed to parse {candidate}: {e}", file=sys.stderr)


def main():
    _load_env()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url:
        print("Missing SUPABASE_URL in environment (set it or create .env)", file=sys.stderr)
        sys.exit(1)
    if not key:
        print("Missing SUPABASE_SERVICE_ROLE_KEY in environment (set it or create .env)", file=sys.stderr)
        sys.exit(1)

    try:
        client = create_client(url, key)
        result = client.table("documents").select("id").limit(1).execute()
        count = len(result.data or [])
        print(f"OK: Connected. documents sample rows: {count}")
        sys.exit(0)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
