"""
Mindmap Data Endpoint (deterministic JSON)

Builds a mindmap tree from generated notes markdown stored in Supabase Storage.
This avoids LLM-drawn SVG variability and produces a stable structure for
frontend rendering (e.g., with React Flow + Dagre).
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.auth import require_user
from app.supabase_client import get_supabase_client


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mindmap", tags=["mindmap"])

NOTES_BUCKET = "processed"


class MindmapNode(BaseModel):
    id: str
    label: str
    children: List["MindmapNode"] = []


MindmapNode.model_rebuild()


def _parse_markdown_headings(md: str) -> MindmapNode:
    """Parse markdown using ATX headings (#..######) to a tree.

    Fallback: if no headings, create up to 8 children using first sentence of paragraphs.
    """
    lines = [l.rstrip() for l in md.splitlines()]
    heading_re = re.compile(r"^(#{1,6})\s+(.+)$")

    root = MindmapNode(id="root", label="Document", children=[])
    # stack entries: (level, node)
    stack: List[tuple[int, MindmapNode]] = [(0, root)]
    counter = 0

    for line in lines:
        m = heading_re.match(line)
        if not m:
            continue
        level = len(m.group(1))
        label = re.sub(r"\s{2,}", " ", m.group(2)).strip()
        if not label:
            continue
        counter += 1
        node = MindmapNode(id=f"n{counter}", label=label, children=[])
        while stack and stack[-1][0] >= level:
            stack.pop()
        parent = stack[-1][1] if stack else root
        parent.children.append(node)
        stack.append((level, node))

    # Fallback: derive from paragraphs if no headings discovered
    if len(root.children) == 0:
        paras = [p.strip() for p in md.split("\n\n") if p.strip()]
        for p in paras[:8]:
            counter += 1
            # take first sentence or first 80 chars
            first_sentence = re.split(r"(?<=[.!?])\s+", p)[0]
            label = (first_sentence[:80] + ("…" if len(first_sentence) > 80 else "")).strip()
            root.children.append(MindmapNode(id=f"n{counter}", label=label, children=[]))

    return root


@router.get("/data")
def get_mindmap_data(
    document_id: str = Query(..., description="Document UUID"),
    user=Depends(require_user),
):
    """Return deterministic mindmap JSON from notes stored in Supabase Storage.

    Notes path: processed/{user_id}/{document_id}-notes.md in bucket 'processed'.
    """
    user_id = user["sub"]
    supabase = get_supabase_client()

    storage_path = f"processed/{user_id}/{document_id}-notes.md"
    logger.info("Building mindmap from notes: %s", storage_path)

    try:
        resp = supabase.storage.from_(NOTES_BUCKET).download(storage_path)
        if not resp:
            raise FileNotFoundError("Notes not found in storage")
        md = resp.decode("utf-8", errors="ignore") if isinstance(resp, (bytes, bytearray)) else str(resp)
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to download notes for %s: %s", document_id, e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notes not found. Generate notes first.",
        )

    try:
        tree = _parse_markdown_headings(md)
        return {"document_id": document_id, "root": tree.model_dump()}
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to parse notes for mindmap %s: %s", document_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to build mindmap from notes",
        )
