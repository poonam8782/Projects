"""
Document history endpoint for Neura.

Returns list of user's uploaded documents with metadata.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from app.supabase_client import get_supabase_client
from app.core.auth import require_user
from app.schemas import HistoryResponse, DocumentMetadata

# Router setup
router = APIRouter(prefix="/history", tags=["history"])

# Logger setup
logger = logging.getLogger(__name__)


@router.get("", response_model=HistoryResponse)
async def get_document_history(user=Depends(require_user)):
    """
    Get list of user's uploaded documents.
    
    Args:
        user: Authenticated user from JWT middleware
        
    Returns:
        HistoryResponse with list of DocumentMetadata objects
        
    Raises:
        HTTPException: 500 if database query fails
    """
    try:
        supabase = get_supabase_client()
        user_id = user["sub"]
        
        # Query documents table, filtered by user_id, ordered by created_at DESC
        result = supabase.table("documents").select(
            "id, filename, size_bytes, mime_type, status, created_at, updated_at"
        ).eq("user_id", user_id).order("created_at", desc=True).execute()
        
        # Build response
        documents = result.data
        message = "No documents found" if len(documents) == 0 else ""
        
        return HistoryResponse(
            documents=documents,
            total=len(documents),
            message=message
        )
    except Exception as e:
        logger.error(f"Failed to fetch document history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch document history"
        )


@router.post("/download/{document_id}")
async def get_download_url(document_id: str, user=Depends(require_user)):
    """
    Generate signed download URL for a document.
    
    Args:
        document_id: Document UUID
        user: Authenticated user from JWT middleware
        
    Returns:
        Dict with signed URL and expiration time
        
    Raises:
        HTTPException: 404 if document not found or access denied
        HTTPException: 500 if URL generation fails
    """
    try:
        supabase = get_supabase_client()
        user_id = user["sub"]
        
        # Query document and verify ownership
        result = supabase.table("documents").select("storage_path").eq(
            "id", document_id
        ).eq("user_id", user_id).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or access denied"
            )
        
        storage_path = result.data[0]["storage_path"]
        
        # Generate signed URL (60 seconds TTL)
        signed_url_response = supabase.storage.from_("uploads").create_signed_url(
            storage_path, expires_in=60
        )
        
        # Extract signed URL from response with explicit error checking
        signed_url = None
        
        # Handle dict response with error key
        if isinstance(signed_url_response, dict):
            if "error" in signed_url_response:
                logger.error(f"Supabase storage error: {signed_url_response['error']}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate download URL"
                )
            
            # Try nested data.signedURL first
            if "data" in signed_url_response and isinstance(signed_url_response["data"], dict):
                signed_url = signed_url_response["data"].get("signedURL")
            
            # Fallback to top-level signedURL
            if not signed_url:
                signed_url = signed_url_response.get("signedURL")
        
        # Handle object response with get method
        elif hasattr(signed_url_response, 'get'):
            signed_url = signed_url_response.get('signedURL')
        else:
            signed_url = signed_url_response
        
        # Final validation
        if not signed_url:
            logger.error(f"Missing signedURL in response: {signed_url_response}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate download URL"
            )
        
        return {
            "url": signed_url,
            "expires_in": 60
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate download URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL"
        )


@router.get("/{document_id}", response_model=DocumentMetadata)
async def get_document(document_id: str, user=Depends(require_user)):
    """
    Get a single document's metadata by ID, verifying ownership.
    
    Args:
        document_id: Document UUID
        user: Authenticated user from JWT middleware
    
    Returns:
        DocumentMetadata for the requested document
    
    Raises:
        HTTPException: 404 if not found or access denied
        HTTPException: 500 on database errors
    """
    try:
        supabase = get_supabase_client()
        user_id = user["sub"]

        result = supabase.table("documents").select(
            "id, filename, size_bytes, mime_type, status, created_at, updated_at"
        ).eq("id", document_id).eq("user_id", user_id).limit(1).execute()

        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or access denied"
            )

        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch document"
        )

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: str, user=Depends(require_user)):
    """
    Delete a document.
    
    Args:
        document_id: Document UUID
        user: Authenticated user from JWT middleware
        
    Returns:
        No content (204 status)
        
    Raises:
        HTTPException: 404 if document not found or access denied
        HTTPException: 500 if deletion fails
    """
    try:
        supabase = get_supabase_client()
        user_id = user["sub"]
        
        # Query document to get storage_path and verify ownership
        result = supabase.table("documents").select("storage_path").eq(
            "id", document_id
        ).eq("user_id", user_id).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or access denied"
            )
        
        storage_path = result.data[0]["storage_path"]
        
        # Delete from storage (log errors but don't fail)
        try:
            supabase.storage.from_("uploads").remove([storage_path])
        except Exception as storage_error:
            logger.error(f"Storage deletion failed (continuing): {storage_error}")
        
        # Delete related flashcards explicitly (belt-and-suspenders approach)
        try:
            supabase.table("flashcards").delete().eq("document_id", document_id).execute()
            logger.info(f"Deleted flashcards for document {document_id}")
        except Exception as flashcard_error:
            logger.error(f"Flashcard deletion failed (continuing): {flashcard_error}")
        
        # Delete from database (will cascade to embeddings)
        supabase.table("documents").delete().eq(
            "id", document_id
        ).eq("user_id", user_id).execute()
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )
