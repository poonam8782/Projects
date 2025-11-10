"""
Flashcard Review Endpoints

Provides endpoints for flashcard review operations with SM-2 spaced repetition.
Handles flashcard review with quality ratings, updates scheduling parameters using
the SM-2 algorithm, and returns the next due flashcard.
"""

import logging
from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, status

from app.supabase_client import get_supabase_client
from app.core.auth import require_user
from app.schemas import ReviewRequest, ReviewResponse, FlashcardResponse
from app.utils.sm2 import calculate_sm2, format_interval_description


router = APIRouter(prefix="/flashcards", tags=["flashcards"])
logger = logging.getLogger(__name__)


@router.get("", response_model=List[FlashcardResponse])
def get_flashcards_by_document(
    document_id: UUID,
    user=Depends(require_user),
):
    """Fetch all flashcards for a specific document.
    
    Args:
        document_id: UUID of the document
        user: Authenticated user from JWT token
        
    Returns:
        List of FlashcardResponse objects with SM-2 scheduling data
        
    Note:
        Returns empty list if document has no flashcards or user doesn't own document.
        Flashcards are ordered by next_review (due cards first).
    """
    user_id = user["sub"]
    supabase = get_supabase_client()
    
    try:
        # Query flashcards for the document (ownership verified via user_id filter)
        result = supabase.table("flashcards").select("*").eq(
            "document_id", str(document_id)
        ).eq(
            "user_id", user_id
        ).order(
            "next_review", desc=False
        ).execute()
        
        # Convert to FlashcardResponse objects
        flashcards = [FlashcardResponse(**flashcard) for flashcard in result.data]
        return flashcards
        
    except Exception as e:
        logger.error(f"Failed to fetch flashcards for document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch flashcards"
        )


@router.post("/review", response_model=ReviewResponse)
def review_flashcard(
    request: ReviewRequest,
    user=Depends(require_user),
):
    """Update flashcard scheduling based on user's quality rating using SM-2 algorithm.

    Fetches the flashcard, verifies ownership, calculates new SM-2 parameters based on
    the quality rating, updates the database, and returns the updated flashcard along
    with the next flashcard due for review.

    Args:
        request: ReviewRequest with flashcard_id and quality rating (0-5).
        user: Authenticated user info from JWT.

    Returns:
        ReviewResponse with reviewed flashcard, next due flashcard, and progress metrics.

    Raises:
        HTTPException 404: Flashcard not found or access denied.
        HTTPException 422: Invalid quality rating (caught by Pydantic validation).
        HTTPException 500: Database update failed or unexpected error.
    """
    user_id = user["sub"]
    logger.info("Reviewing flashcard %s for user %s with quality %d", request.flashcard_id, user_id, request.quality)

    supabase = get_supabase_client()

    try:
        # Fetch flashcard and verify ownership
        try:
            flashcard_result = (
                supabase.table("flashcards")
                .select("*")
                .eq("id", request.flashcard_id)
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
        except Exception as e:  # noqa: BLE001
            logger.error("Database error fetching flashcard: %s", e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error",
            )

        if not flashcard_result.data:
            logger.warning("Flashcard %s not found for user %s", request.flashcard_id, user_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flashcard not found or access denied",
            )

        flashcard = flashcard_result.data[0]

        # Extract current SM-2 values and document_id for scoping
        current_efactor = flashcard.get("efactor", 2.5)
        current_repetitions = flashcard.get("repetitions", 0)
        current_interval = flashcard.get("interval", 1)
        flashcard_document_id = flashcard["document_id"]

        # Calculate new SM-2 parameters
        try:
            sm2_result = calculate_sm2(
                quality=request.quality,
                current_efactor=current_efactor,
                current_repetitions=current_repetitions,
                current_interval=current_interval,
            )
        except ValueError as e:
            logger.error("SM-2 calculation error: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"SM-2 calculation error: {e}",
            )

        logger.info(
            "SM-2 update for flashcard %s: quality=%d, interval %d→%d days",
            request.flashcard_id,
            request.quality,
            current_interval,
            sm2_result.interval,
        )

        # Update flashcard in database
        update_dict = {
            "efactor": sm2_result.efactor,
            "repetitions": sm2_result.repetitions,
            "interval": sm2_result.interval,
            "next_review": sm2_result.next_review.isoformat(),
            "last_reviewed": datetime.now(timezone.utc).isoformat(),
        }

        try:
            update_result = (
                supabase.table("flashcards")
                .update(update_dict)
                .eq("id", request.flashcard_id)
                .eq("user_id", user_id)
                .execute()
            )
            updated_flashcard = update_result.data[0]
        except Exception as e:  # noqa: BLE001
            logger.error("Database error updating flashcard: %s", e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update flashcard",
            )

        # Fetch next due flashcard (exclude just-reviewed card for edge timing cases)
        next_flashcard = None
        try:
            next_result = (
                supabase.table("flashcards")
                .select("*")
                .eq("user_id", user_id)
                .eq("document_id", str(flashcard_document_id))
                .neq("id", request.flashcard_id)
                .lte("next_review", datetime.now(timezone.utc).isoformat())
                .order("next_review", desc=False)
                .limit(1)
                .execute()
            )
            if next_result.data:
                next_flashcard = next_result.data[0]
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to fetch next flashcard: %s", e)
            # Don't fail the request if we can't fetch the next flashcard

        # Count total due flashcards
        due_count = 0
        try:
            count_result = (
                supabase.table("flashcards")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .eq("document_id", str(flashcard_document_id))
                .lte("next_review", datetime.now(timezone.utc).isoformat())
                .execute()
            )
            due_count = count_result.count or 0
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to count due flashcards: %s", e)
            # Don't fail the request if we can't get the count

        # Build response
        interval_desc = format_interval_description(sm2_result.interval)
        message = f"Review again in {interval_desc}" if next_flashcard else "No more flashcards due"

        return ReviewResponse(
            reviewed_flashcard=FlashcardResponse(**updated_flashcard),
            next_flashcard=FlashcardResponse(**next_flashcard) if next_flashcard else None,
            due_count=due_count,
            message=message,
        )

    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.error("Unexpected error in /flashcards/review: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )
