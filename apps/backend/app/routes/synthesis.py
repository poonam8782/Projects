"""
Multi-Document Synthesis Endpoints

Provides endpoints for multi-document synthesis operations (Sprint 6).
Aggregates text and optionally embeddings from multiple documents,
uses Gemini AI to generate unified summaries or comparative analyses
with source attribution.
"""

import logging
import time
import re
from typing import List, Dict
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, status

from app.supabase_client import get_supabase_client
from app.core.auth import require_user
from app.schemas import SynthesizeRequest, SynthesizeResponse, DocumentSource
from app.services.gemini_client import synthesize_documents


router = APIRouter(prefix="/synthesize", tags=["synthesis"])
logger = logging.getLogger(__name__)


@router.post("", response_model=SynthesizeResponse)
def synthesize_multi_documents(
    request: SynthesizeRequest,
    user=Depends(require_user),
):
    """Generate unified summary or comparative analysis from multiple documents.
    
    Fetches all documents and verifies ownership, validates all have extracted_text,
    aggregates text with source labels, calls Gemini AI with synthesis-specific prompt,
    parses Sources section for attribution, returns markdown with structured source attribution.
    
    Args:
        request: SynthesizeRequest with document_ids, synthesis_type, include_embeddings
        user: Authenticated user from JWT token
        
    Returns:
        SynthesizeResponse with markdown_output, sources, document_count, processing_time
        
    Raises:
        HTTPException 400: Documents missing extracted text
        HTTPException 404: Documents not found or access denied
        HTTPException 429: Gemini API rate limit exceeded
        HTTPException 500: Synthesis generation failed
    """
    user_id = user["sub"]
    start_time = time.time()
    
    logger.info(
        "Starting synthesis for user %s: %d documents, type=%s",
        user_id,
        len(request.document_ids),
        request.synthesis_type
    )
    
    supabase = get_supabase_client()
    
    try:
        # Fetch all documents and verify ownership
        try:
            document_ids_str = [str(doc_id) for doc_id in request.document_ids]
            result = (
                supabase.table("documents")
                .select("id, filename, extracted_text")
                .in_("id", document_ids_str)
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as e:  # noqa: BLE001
            logger.error("Database error fetching documents: %s", e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error",
            )
        
        # Validate that all documents were found (ownership check)
        if len(result.data) != len(request.document_ids):
            logger.warning(
                "User %s attempted to synthesize %d documents but only owns %d",
                user_id,
                len(request.document_ids),
                len(result.data)
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more documents not found or access denied",
            )
        
        # Reorder documents to match request order (Comment 4)
        doc_map = {doc["id"]: doc for doc in result.data}
        documents = [doc_map[str(doc_id)] for doc_id in request.document_ids]
        
        # Validate extracted text for all documents
        missing_text_docs = [
            doc["filename"]
            for doc in documents
            if not doc.get("extracted_text", "").strip()
        ]
        
        if missing_text_docs:
            logger.warning(
                "Documents missing extracted text: %s",
                ", ".join(missing_text_docs)
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Documents missing extracted text: {', '.join(missing_text_docs)}",
            )
        
        # Prepare documents for synthesis
        documents_data = [
            {"filename": doc["filename"], "text": doc["extracted_text"]}
            for doc in documents
        ]
        
        total_length = sum(len(doc["text"]) for doc in documents_data)
        
        logger.info(
            "Synthesizing %d documents with %d total characters",
            len(documents),
            total_length
        )
        
        # Generate synthesis via Gemini
        try:
            synthesis_markdown = synthesize_documents(
                documents_data,
                synthesis_type=request.synthesis_type,
                temperature=0.5,
                max_output_tokens=8192
            )
        except ValueError as e:
            logger.error("Validation error in synthesis: %s", e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except RuntimeError as e:
            message = str(e)
            # Check for rate limiting
            if "rate limit" in message.lower() or "429" in message:
                logger.warning("Gemini API rate limit: %s", message)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Gemini API rate limit exceeded. Please try again later.",
                )
            # General Gemini error
            logger.error("Gemini synthesis failed: %s", message, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate synthesis",
            )
        
        # Validate markdown is not empty
        if not synthesis_markdown.strip():
            logger.error("Gemini returned empty synthesis")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Synthesis generation returned empty result",
            )
        
        logger.info("Generated %d characters of synthesis", len(synthesis_markdown))
        
        # Parse source attribution from markdown
        sources = []
        
        # Try to find Sources section
        sources_match = re.search(
            r"## Sources\n(.+?)(?=\n##|$)",
            synthesis_markdown,
            re.DOTALL
        )
        
        if sources_match:
            sources_text = sources_match.group(1)
            
            # Parse bullet points per document
            # Pattern: **Document N: filename**\n- Key point 1\n- Key point 2
            doc_pattern = r"\*\*Document \d+: (.+?)\*\*\n((?:- .+\n?)+)"
            doc_matches = list(re.finditer(doc_pattern, sources_text))
            
            # Build filename map for fallback (Comment 3)
            filename_map = {doc["filename"].lower(): doc["id"] for doc in documents}
            
            for i, doc_match in enumerate(doc_matches):
                filename = doc_match.group(1).strip()
                key_points_text = doc_match.group(2)
                
                # Extract individual key points
                key_points = [
                    line.strip()[2:].strip()  # Remove "- " prefix
                    for line in key_points_text.strip().split("\n")
                    if line.strip().startswith("-")
                ]
                
                # Order-based mapping first (Comment 3)
                doc_id = None
                if i < len(documents):
                    doc_id = documents[i]["id"]
                else:
                    # Fallback: exact case-insensitive filename match
                    doc_id = filename_map.get(filename.lower())
                
                if doc_id:
                    # Normalize UUID (Comment 2)
                    if isinstance(doc_id, str):
                        normalized_id = UUID(doc_id)
                    elif isinstance(doc_id, UUID):
                        normalized_id = doc_id
                    else:
                        normalized_id = UUID(str(doc_id))
                    
                    sources.append(DocumentSource(
                        document_id=normalized_id,
                        filename=filename,
                        key_points=key_points
                    ))
            
            logger.info("Parsed %d document sources from markdown", len(sources))
        else:
            logger.warning("Sources section not found in synthesis markdown")
        
        # Fill gaps if fewer sources parsed than documents (Comment 1)
        if len(sources) < len(documents):
            logger.warning(
                "Only parsed %d sources, expected %d. Filling gaps.",
                len(sources),
                len(documents)
            )
            # Create set of document IDs already in sources
            parsed_ids = {str(src.document_id) for src in sources}
            
            # Append missing documents with empty key_points
            for doc in documents:
                doc_id_str = str(doc["id"])
                if doc_id_str not in parsed_ids:
                    # Normalize UUID (Comment 2)
                    if isinstance(doc["id"], str):
                        normalized_id = UUID(doc["id"])
                    elif isinstance(doc["id"], UUID):
                        normalized_id = doc["id"]
                    else:
                        normalized_id = UUID(str(doc["id"]))
                    
                    sources.append(DocumentSource(
                        document_id=normalized_id,
                        filename=doc["filename"],
                        key_points=[]
                    ))
        
        # Build response
        processing_time = time.time() - start_time
        
        message = (
            "Synthesis completed successfully"
            if request.synthesis_type == "summary"
            else "Comparative analysis completed successfully"
        )
        
        response = SynthesizeResponse(
            synthesis_type=request.synthesis_type,
            markdown_output=synthesis_markdown,
            sources=sources,
            document_count=len(request.document_ids),
            total_text_length=total_length,
            status="success",
            message=message,
            processing_time_seconds=processing_time
        )
        
        logger.info(
            "Synthesis completed: type=%s, documents=%d, time=%.2fs",
            request.synthesis_type,
            len(documents),
            processing_time
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.error("Unexpected error in synthesis: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )
