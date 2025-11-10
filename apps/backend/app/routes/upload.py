"""
File upload endpoint for Neura.

Handles multipart file uploads, validates file type and size, uploads to Supabase Storage,
extracts text, and saves metadata to database.
"""

import logging
from typing import Annotated, Optional
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, Header, HTTPException, Depends, status

from app.supabase_client import get_supabase_client
from app.core.auth import require_user
from app.schemas import DocumentUploadResponse
from app.utils.extractors import get_extractor_for_mime_type

# Constants
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "image/png",
    "image/jpeg",
}

MIME_TO_EXTENSION = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
    "image/png": ".png",
    "image/jpeg": ".jpg",
}

# Router setup
router = APIRouter(prefix="/upload", tags=["upload"])

# Logger setup
logger = logging.getLogger(__name__)


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: Annotated[UploadFile, File(...)],
    content_length: Annotated[Optional[int], Header()] = None,
    user = Depends(require_user),
):
    """
    Upload a document file and extract text.
    
    Args:
        file: The uploaded file (multipart/form-data)
        content_length: Content-Length header for early validation
        user: Authenticated user from JWT middleware
        
    Returns:
        DocumentUploadResponse with document metadata and extracted text preview
        
    Raises:
        HTTPException: 411 if Content-Length header missing
        HTTPException: 400 if file type not supported
        HTTPException: 413 if file size exceeds limit
        HTTPException: 500 if storage upload or database save fails
    """
    # Validation: Content-Length check
    if content_length is None:
        raise HTTPException(
            status_code=status.HTTP_411_LENGTH_REQUIRED,
            detail="Content-Length header required"
        )
    
    # Validation: MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file.content_type} not supported. Allowed: PDF, DOCX, TXT, PNG, JPG"
        )
    
    # Validation: Read file and check actual size
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 10MB limit"
        )
    
    # Generate document ID and storage path
    document_id = uuid4()
    user_id = user["sub"]
    extension = MIME_TO_EXTENSION.get(file.content_type, "")
    storage_path = f"uploads/{user_id}/{document_id}{extension}"
    
    # Upload to Supabase Storage
    try:
        supabase = get_supabase_client()
        upload_response = supabase.storage.from_("uploads").upload(
            path=storage_path,
            file=file_bytes,
            file_options={
                "content-type": file.content_type,
                "upsert": "false"
            }
        )
        
        # Check if upload response indicates an error
        if hasattr(upload_response, 'error') and upload_response.error:
            logger.error(f"Storage upload returned error: {upload_response.error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file to storage"
            )
    except HTTPException:
        # Re-raise HTTPException as-is
        raise
    except Exception as e:
        logger.error(f"Storage upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file to storage"
        )
    
    # Extract text
    extractor = get_extractor_for_mime_type(file.content_type)
    
    if extractor is None:
        # No extractor available for this type
        extracted_text = ""
        status_value = "uploaded"
    else:
        try:
            extracted_text = extractor(file_bytes)
            
            # Check if extraction succeeded
            if extracted_text and extracted_text.strip():
                status_value = "extracted"
            else:
                status_value = "failed"
                extracted_text = ""
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            status_value = "failed"
            extracted_text = ""
    
    # Save to database
    try:
        result = supabase.table("documents").insert({
            "id": str(document_id),
            "user_id": user_id,
            "filename": file.filename,
            "storage_path": storage_path,
            "extracted_text": extracted_text,
            "size_bytes": len(file_bytes),
            "mime_type": file.content_type,
            "status": status_value,
        }).execute()
        
        # Extract inserted row
        document_data = result.data[0]
    except Exception as e:
        logger.error(f"Database save failed: {e}")
        
        # Attempt cleanup: delete uploaded file from storage
        try:
            supabase.storage.from_("uploads").remove([storage_path])
        except Exception as cleanup_error:
            logger.error(f"Storage cleanup failed: {cleanup_error}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save document metadata"
        )
    
    # Build response
    extracted_text_preview = None
    if extracted_text:
        # First 200 characters for preview
        extracted_text_preview = extracted_text[:200]
        if len(extracted_text) > 200:
            extracted_text_preview += "..."
    
    # Determine message based on status
    if status_value == "extracted":
        message = "Document uploaded and text extracted successfully"
    elif status_value == "failed":
        message = "Document uploaded but text extraction failed"
    else:
        message = "Document uploaded"
    
    return DocumentUploadResponse(
        id=document_data["id"],
        filename=document_data["filename"],
        size_bytes=document_data["size_bytes"],
        mime_type=document_data["mime_type"],
        status=document_data["status"],
        storage_path=document_data["storage_path"],
        extracted_text_preview=extracted_text_preview,
        created_at=document_data["created_at"],
        message=message,
    )
