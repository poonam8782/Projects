"""
Helper functions for constructing storage paths.

Centralizes path construction to avoid duplication and path drift.
"""

from uuid import UUID


def get_notes_path(user_id: str, document_id: UUID) -> str:
    """
    Construct the storage path for generated notes.
    
    Args:
        user_id: User ID (subject from JWT)
        document_id: Document UUID
        
    Returns:
        Storage path in format: "processed/{user_id}/{document_id}-notes.md"
    """
    return f"processed/{user_id}/{document_id}-notes.md"
