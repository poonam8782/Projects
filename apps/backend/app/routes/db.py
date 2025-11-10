import logging
from fastapi import APIRouter, HTTPException, status

from app.supabase_client import get_supabase_client

router = APIRouter(prefix="/db", tags=["database"])
logger = logging.getLogger(__name__)


@router.get("/health")
def database_health():
    """Lightweight Supabase connectivity check.

    Attempts a minimal select from documents table limited to 1 row.
    Returns status and row_count if successful.
    """
    try:
        supabase = get_supabase_client()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Supabase client init failed: {e}",
        )

    try:
        result = supabase.table("documents").select("id").limit(1).execute()
        row_count = len(result.data or [])
        return {"status": "ok", "row_count": row_count}
    except Exception as e:  # noqa: BLE001
        logger.error("Database health check failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database health check failed: {e}",
        )
