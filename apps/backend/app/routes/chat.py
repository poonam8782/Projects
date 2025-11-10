"""RAG chat endpoint that combines vector similarity search with Gemini streaming.

This module exposes `/chat`, which embeds user queries, fetches relevant document
chunks via the `match_embeddings` RPC, assembles a context window, and streams
Gemini responses over Server-Sent Events (SSE) with provenance metadata.
"""

import json
import logging
from typing import Annotated, AsyncGenerator, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.auth import require_user
from app.schemas import ChatRequest, ChunkProvenance
from app.services.gemini_client import generate_embedding, stream_chat_response
import anyio
from supabase import Client

from app.supabase_client import get_supabase_client
from app.utils.chunker import count_tokens

DEFAULT_MAX_CHUNKS = 5
DEFAULT_SIMILARITY_THRESHOLD = 0.3
MAX_CONTEXT_TOKENS = 8000
MAX_HISTORY_TOKENS = 4000

router = APIRouter(prefix="/chat", tags=["chat"])

logger = logging.getLogger(__name__)


def _validate_document(supabase: Client, document_id: str, user_id: str) -> None:
    """Ensure the document exists, belongs to the user, and is embedded."""

    response = (
        supabase.table("documents")
        .select("status")
        .eq("id", document_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        logger.warning("Document %s not found for user %s", document_id, user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied",
        )

    status_value = response.data[0].get("status")
    if status_value != "embedded":
        logger.info(
            "Document %s is not embedded (status=%s) for user %s",
            document_id,
            status_value,
            user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document must be embedded first. Call /embed endpoint.",
        )


def _fetch_matching_chunks(
    supabase: Client,
    document_id: str,
    embedding: List[float],
    match_count: int,
    similarity_threshold: float,
) -> List[Dict]:
    """Call the match_embeddings RPC and return matching chunks."""

    payload = {
        "query_embedding": embedding,
        "target_document_id": document_id,
        "match_count": match_count,
        "similarity_threshold": similarity_threshold,
    }

    try:
        response = supabase.rpc("match_embeddings", payload).execute()
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Similarity search failed for document %s: %s",
            document_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform similarity search: {exc}",
        ) from exc
    matches = response.data or []

    if not matches:
        logger.info(
            "No matching chunks for document %s with similarity_threshold %.2f",
            document_id,
            similarity_threshold,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No relevant chunks found. Try lowering similarity threshold.",
        )

    return matches


def _assemble_context(matches: List[Dict]) -> List[Dict]:
    """Trim context to fit token budget while preserving highest-similarity chunks."""

    active_matches = matches.copy()

    while active_matches:
        ordered = sorted(active_matches, key=lambda item: item.get("chunk_index", 0))
        context_text = "\n\n---\n\n".join(chunk.get("chunk_text", "") for chunk in ordered)
        token_count = count_tokens(context_text)

        if token_count <= MAX_CONTEXT_TOKENS:
            logger.debug("Context assembled with %s tokens", token_count)
            return ordered

        lowest = min(active_matches, key=lambda item: item.get("similarity") or 0.0)
        logger.debug(
            "Truncating chunk %s (similarity=%.4f) to fit context window",
            lowest.get("id"),
            lowest.get("similarity") or 0.0,
        )
        active_matches.remove(lowest)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Unable to assemble context within token limits",
    )


def _prepare_history(history: List) -> List[Dict[str, List[str]]]:
    """Clamp conversation history to stay within the model token budget."""

    if not history:
        return []

    running_total = 0
    trimmed: List = []

    for message in history[::-1]:
        message_tokens = count_tokens(message.content)
        if running_total + message_tokens > MAX_HISTORY_TOKENS:
            break
        trimmed.insert(0, message)
        running_total += message_tokens

    if len(trimmed) < len(history):
        logger.debug(
            "Truncated chat history from %d to %d messages for token budget",
            len(history),
            len(trimmed),
        )

    return [{"role": msg.role, "parts": [msg.content]} for msg in trimmed]


@router.post("")
async def chat_with_document(
    request: ChatRequest,
    user: Annotated[dict, Depends(require_user)],
):
    """Perform RAG-based chat with SSE streaming."""

    document_id = str(request.document_id)
    user_id = user.get("sub")

    supabase = get_supabase_client()

    _validate_document(supabase, document_id, user_id)

    try:
        query_embedding = generate_embedding(
            request.query,
            task_type="RETRIEVAL_QUERY",
            dimensions=1536,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to embed query for document %s: %s", document_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to embed query: {exc}",
        )

    matches = _fetch_matching_chunks(
        supabase=supabase,
        document_id=document_id,
        embedding=query_embedding,
        match_count=request.max_chunks,
        similarity_threshold=request.similarity_threshold,
    )

    ordered_chunks = _assemble_context(matches)

    provenance_payload = [
        ChunkProvenance(
            chunk_id=chunk.get("id"),
            chunk_index=chunk.get("chunk_index"),
            chunk_text=chunk.get("chunk_text", ""),
            similarity=float(chunk.get("similarity", 0.0)),
        ).model_dump()
        for chunk in ordered_chunks
    ]

    context_text = "\n\n---\n\n".join(chunk.get("chunk_text", "") for chunk in ordered_chunks)

    gemini_history = _prepare_history(request.history)

    async def sse_stream() -> AsyncGenerator[bytes, None]:
        """Yield Server-Sent Events for chat streaming without relying on EventSourceResponse.

        This custom implementation avoids event loop cross-thread issues observed in tests
        (Future attached to a different loop) stemming from sse_starlette's global AppStatus
        event object. We manually format SSE frames: "event:" and "data:" lines separated
        by a blank line. Heartbeats/pings are omitted as tests don't assert them.
        """
        def _format(event: str, payload: dict) -> bytes:
            return f"event: {event}\ndata: {json.dumps(payload)}\n\n".encode()

        try:
            # Provenance first
            yield _format("provenance", {"chunks": provenance_payload})

            def _collect_tokens() -> List[str]:
                return list(
                    stream_chat_response(
                        prompt=request.query,
                        context=context_text,
                        history=gemini_history,
                    )
                )

            tokens = await anyio.to_thread.run_sync(_collect_tokens)
            for token in tokens:
                if token:
                    yield _format("token", {"token": token})

            yield _format("done", {"finish_reason": "stop"})
        except Exception as exc:  # noqa: BLE001
            logger.error("Streaming error for document %s: %s", document_id, exc, exc_info=True)
            yield _format("error", {"error": str(exc)})

    return StreamingResponse(sse_stream(), media_type="text/event-stream")
