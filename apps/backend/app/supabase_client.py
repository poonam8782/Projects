"""Supabase service role client for backend admin operations.

This client uses the Supabase service role key and bypasses RLS. Use ONLY for
backend-admin tasks such as document processing, embedding insertion, and
maintenance. Never expose the service role key to the frontend.
"""

from supabase import create_client, Client
from app.core.config import get_settings


def get_supabase_client() -> Client:
    settings = get_settings()
    if not settings.supabase_url:
        raise ValueError("SUPABASE_URL is not configured")
    if not settings.supabase_service_role_key:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY is not configured")

    return create_client(settings.supabase_url, settings.supabase_service_role_key)
