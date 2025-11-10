"""
User profile management utilities.

Handles automatic profile creation for new users.
"""
import logging
from typing import Dict, Any

from app.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def ensure_user_profile(user_id: str, user_claims: Dict[str, Any] = None) -> bool:
    """
    Ensure a user profile exists in the profiles table.
    
    Creates a profile if it doesn't exist. This is called automatically
    on first request to avoid foreign key constraint errors.
    
    Args:
        user_id: The user's UUID from auth.users
        user_claims: Optional JWT claims containing email, etc.
        
    Returns:
        True if profile exists or was created successfully
        
    Raises:
        Exception: If profile creation fails
    """
    try:
        supabase = get_supabase_client()
        
        # Check if profile already exists
        result = supabase.table("profiles").select("id").eq("id", user_id).execute()
        
        if result.data and len(result.data) > 0:
            # Profile already exists
            return True
        
        # Profile doesn't exist, create it
        profile_data = {"id": user_id}
        
        # Extract email from claims if available
        if user_claims:
            email = user_claims.get("email")
            if email:
                profile_data["email"] = email
        
        logger.info(f"Creating profile for user {user_id}")
        supabase.table("profiles").insert(profile_data).execute()
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to ensure user profile for {user_id}: {e}")
        raise
