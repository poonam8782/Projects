"""
Embedding Generation Endpoint

This module provides the /embed endpoint that generates embeddings for document chunks
using Gemini API and stores them in pgvector for similarity search (RAG in Sprint 3).

The endpoint orchestrates the complete embedding pipeline:
1. Fetch document and verify ownership
2. Chunk text using tiktoken-based chunker
3. Generate embeddings via Gemini API
4. Store embeddings in pgvector database
5. Update document status to 'embedded'
"""

import logging
import time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, status

from app.supabase_client import get_supabase_client
from app.core.auth import require_user
from app.schemas import EmbeddingResponse
from app.utils.chunker import chunk_text, get_chunk_count, count_tokens
from app.services.gemini_client import generate_embeddings_batch

# Constants
DEFAULT_CHUNK_SIZE = 1000  # Tokens per chunk
DEFAULT_OVERLAP = 200  # Token overlap between chunks

# Router setup
router = APIRouter(prefix="/embed", tags=["embed"])

# Logger setup
logger = logging.getLogger(__name__)


@router.post("", response_model=EmbeddingResponse)
def embed_document(
    document_id: UUID,
    user: dict = Depends(require_user)
):
    """
    Generate embeddings for all chunks of a document.
    
    This endpoint:
    - Verifies document ownership
    - Chunks the document's extracted text
    - Generates embeddings via Gemini API
    - Stores embeddings in pgvector database
    - Updates document status to 'embedded'
    
    The operation is idempotent: calling it multiple times will delete
    existing embeddings and regenerate them.
    
    Args:
        document_id: UUID of the document to embed
        user: Authenticated user info (injected by JWT middleware)
    
    Returns:
        EmbeddingResponse with chunk_count, embedding_count, status, message, processing_time
    
    Raises:
        HTTPException 400: Document has no extracted text
        HTTPException 404: Document not found or access denied
        HTTPException 500: Chunking, embedding generation, or database save failed
    """
    user_id = user["sub"]
    
    # Start timing for performance monitoring
    start_time = time.time()
    
    try:
        # Get Supabase client
        supabase = get_supabase_client()
        
        # Fetch document and verify ownership
        logger.info(f"Fetching document {document_id} for user {user_id}")
        doc_response = supabase.table("documents").select("extracted_text, status").eq("id", str(document_id)).eq("user_id", user_id).execute()
        
        if not doc_response.data or len(doc_response.data) == 0:
            logger.warning(f"Document {document_id} not found or access denied for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or access denied"
            )
        
        document = doc_response.data[0]
        extracted_text = document.get("extracted_text")
        
        # Validate extracted text exists
        if not extracted_text or not extracted_text.strip():
            logger.warning(f"Document {document_id} has no extracted text")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document has no extracted text. Upload and extract text first."
            )
        
        # Chunk text
        logger.info(f"Chunking document {document_id}")
        try:
            chunks = chunk_text(
                extracted_text,
                chunk_size=DEFAULT_CHUNK_SIZE,
                overlap=DEFAULT_OVERLAP
            )
            chunk_count = len(chunks)
            logger.info(f"Generated {chunk_count} chunks for document {document_id}")
            
            if chunk_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No chunks generated from document text"
                )
        except HTTPException:
            # Re-raise HTTPException (already properly formatted)
            raise
        except Exception as e:
            logger.error(f"Failed to chunk document {document_id}: {e}", exc_info=True)
            
            # Update document status to 'failed'
            try:
                supabase.table("documents").update({"status": "failed"}).eq("id", str(document_id)).execute()
                logger.info(f"Updated document {document_id} status to 'failed' after chunking error")
            except Exception as update_error:
                logger.error(f"Failed to update document {document_id} status to 'failed': {update_error}")
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to chunk document text: {e}"
            )
        
        # Delete existing embeddings (idempotent operation)
        try:
            logger.info(f"Deleting existing embeddings for document {document_id}")
            delete_response = supabase.table("embeddings").delete().eq("document_id", str(document_id)).execute()
            deleted_count = len(delete_response.data) if delete_response.data else 0
            logger.info(f"Deleted {deleted_count} existing embeddings for document {document_id}")
        except Exception as e:
            logger.error(f"Failed to delete existing embeddings for document {document_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete existing embeddings"
            )
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {chunk_count} chunks of document {document_id}")
        try:
            embeddings = generate_embeddings_batch(
                chunks,
                task_type="RETRIEVAL_DOCUMENT",
                dimensions=1536
            )
            embedding_count = len(embeddings)
            logger.info(f"Generated {embedding_count} embeddings for document {document_id}")
            
            # Validate embeddings count matches chunks count
            if len(embeddings) != len(chunks):
                logger.error(f"Embeddings count mismatch for document {document_id}: {len(embeddings)} embeddings vs {len(chunks)} chunks")
                # Update document status to 'failed'
                try:
                    supabase.table("documents").update({"status": "failed"}).eq("id", str(document_id)).execute()
                    logger.info(f"Updated document {document_id} status to 'failed'")
                except Exception as update_error:
                    logger.error(f"Failed to update document {document_id} status to 'failed': {update_error}")
                
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Embeddings count mismatch: {len(embeddings)} embeddings generated for {len(chunks)} chunks"
                )
        except HTTPException:
            # Re-raise HTTPException (already properly formatted)
            raise
        except Exception as e:
            logger.error(f"Failed to generate embeddings for document {document_id}: {e}", exc_info=True)
            
            # Update document status to 'failed'
            try:
                supabase.table("documents").update({"status": "failed"}).eq("id", str(document_id)).execute()
                logger.info(f"Updated document {document_id} status to 'failed'")
            except Exception as update_error:
                logger.error(f"Failed to update document {document_id} status to 'failed': {update_error}")
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate embeddings: {e}"
            )
        
        # Prepare embedding records for batch insert
        embedding_records = [
            {
                "document_id": str(document_id),
                "chunk_index": idx,
                "chunk_text": chunk,
                "embedding": embedding,
                "token_count": count_tokens(chunk)  # Use tokenizer-based count for accuracy
            }
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings))
        ]
        
        # Insert embeddings into database
        try:
            logger.info(f"Inserting {len(embedding_records)} embeddings for document {document_id}")
            insert_response = supabase.table("embeddings").insert(embedding_records).execute()
            logger.info(f"Successfully inserted embeddings for document {document_id}")
        except Exception as e:
            logger.error(f"Failed to save embeddings for document {document_id}: {e}", exc_info=True)
            
            # Update document status to 'failed'
            try:
                supabase.table("documents").update({"status": "failed"}).eq("id", str(document_id)).execute()
                logger.info(f"Updated document {document_id} status to 'failed'")
            except Exception as update_error:
                logger.error(f"Failed to update document {document_id} status to 'failed': {update_error}")
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save embeddings to database: {e}"
            )
        
        # Update document status to 'embedded'
        try:
            logger.info(f"Updating document {document_id} status to 'embedded'")
            supabase.table("documents").update({"status": "embedded"}).eq("id", str(document_id)).execute()
            logger.info(f"Successfully updated document {document_id} status to 'embedded'")
        except Exception as e:
            logger.warning(f"Failed to update document {document_id} status to 'embedded': {e}")
            # Don't fail the request - embeddings are already saved
        
        # Calculate processing time
        processing_time = time.time() - start_time
        logger.info(f"Embedding generation for document {document_id} completed in {processing_time:.2f}s")
        
        # Build response
        return EmbeddingResponse(
            document_id=str(document_id),
            chunk_count=chunk_count,
            embedding_count=embedding_count,
            status="embedded",
            message="Embeddings generated successfully",
            processing_time_seconds=processing_time
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (they're already properly formatted)
        raise
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error in embed endpoint for document {document_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        )
