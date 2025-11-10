"""
Document Export Endpoints

Provides endpoints for document export operations (Sprint 6).
Aggregates document metadata, generated notes (from Storage), flashcards (from database),
and optionally chat history (from conversations table if exists) into a unified export file.
Supports Markdown and PDF formats.
"""

import logging
import time
from io import BytesIO
from typing import List, Optional
from uuid import UUID

import bleach
from fastapi import APIRouter, HTTPException, Depends, status
try:  # Markdown is required for both markdown and PDF export flows
    import markdown  # type: ignore
except ImportError:  # pragma: no cover - fallback only triggers if dependency missing
    markdown = None  # type: ignore

try:  # WeasyPrint may be unavailable in minimal test environments (system deps)
    from weasyprint import HTML, CSS  # type: ignore
    WEASYPRINT_AVAILABLE = True
except ImportError:  # pragma: no cover - fallback only triggers if dependency missing
    HTML = CSS = None  # type: ignore
    WEASYPRINT_AVAILABLE = False

from app.supabase_client import get_supabase_client
from app.core.auth import require_user
from app.schemas import ExportRequest, ExportResponse


# Constants
EXPORT_BUCKET = "processed"
SIGNED_URL_EXPIRY = 60  # 60 seconds for download URL

# Monochrome CSS for professional PDF exports. Uses black text on white background for print compatibility.
PDF_CSS_TEMPLATE = """
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #000;
    background: #fff;
    line-height: 1.6;
    padding: 2cm;
    margin: 0;
}

h1, h2, h3, h4, h5, h6 {
    font-weight: bold;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    color: #000;
}

h1 { font-size: 2em; }
h2 { font-size: 1.5em; }
h3 { font-size: 1.25em; }

p {
    margin: 0.5em 0;
}

ul, ol {
    margin-left: 1.5em;
    margin-top: 0.5em;
    margin-bottom: 0.5em;
}

li {
    margin: 0.25em 0;
}

code {
    background: #f5f5f5;
    padding: 0.2em 0.4em;
    border: 1px solid #ddd;
    border-radius: 3px;
    font-family: "Courier New", Courier, monospace;
    font-size: 0.9em;
}

pre {
    background: #f5f5f5;
    padding: 1em;
    border: 1px solid #ddd;
    border-radius: 3px;
    overflow-x: auto;
}

pre code {
    background: none;
    border: none;
    padding: 0;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
}

th, td {
    border: 1px solid #ddd;
    padding: 0.5em;
    text-align: left;
}

th {
    background: #f5f5f5;
    font-weight: bold;
}

strong {
    font-weight: bold;
}

em {
    font-style: italic;
}

hr {
    border: none;
    border-top: 1px solid #ddd;
    margin: 2em 0;
}
"""

router = APIRouter(prefix="/export", tags=["export"])
logger = logging.getLogger(__name__)


def fetch_notes_from_storage(supabase, user_id: str, document_id: str) -> Optional[str]:
    """
    Fetch generated notes markdown from Supabase Storage if it exists.
    
    Args:
        supabase: Supabase client
        user_id: User ID
        document_id: Document UUID
        
    Returns:
        Notes markdown content or None if not found
    """
    try:
        storage_path = f"processed/{user_id}/{document_id}-notes.md"
        logger.info(f"Fetching notes from storage: {storage_path}")
        
        response = supabase.storage.from_(EXPORT_BUCKET).download(storage_path)
        if response:
            notes_content = response.decode('utf-8')
            logger.info(f"Found notes: {len(notes_content)} characters")
            return notes_content
        
        logger.info("Notes not found in storage")
        return None
        
    except Exception as e:
        logger.warning(f"Failed to fetch notes from storage: {e}")
        return None


def fetch_flashcards_from_db(supabase, user_id: str, document_id: str) -> List[dict]:
    """
    Fetch all flashcards for a document from the database.
    
    Args:
        supabase: Supabase client
        user_id: User ID
        document_id: Document UUID
        
    Returns:
        List of flashcard dicts or empty list if none exist
    """
    try:
        logger.info(f"Fetching flashcards for document: {document_id}")
        
        result = (
            supabase.table("flashcards")
            .select("question, answer, efactor, repetitions, interval, next_review")
            .eq("document_id", document_id)
            .eq("user_id", user_id)
            .order("created_at")
            .execute()
        )
        
        flashcards = result.data if result.data else []
        logger.info(f"Found {len(flashcards)} flashcards")
        return flashcards
        
    except Exception as e:
        logger.warning(f"Failed to fetch flashcards: {e}")
        return []


def fetch_chat_history_from_db(supabase, user_id: str, document_id: str) -> List[dict]:
    """
    Fetch chat conversation history from the conversations table if it exists.
    
    Args:
        supabase: Supabase client
        user_id: User ID
        document_id: Document UUID
        
    Returns:
        List of message dicts or empty list if table doesn't exist or no data
    """
    try:
        logger.info(f"Fetching chat history for document: {document_id}")
        
        # Try to query conversations table
        result = (
            supabase.table("conversations")
            .select("role, content, created_at")
            .eq("document_id", document_id)
            .eq("user_id", user_id)
            .order("created_at")
            .execute()
        )
        
        chat_history = result.data if result.data else []
        logger.info(f"Found {len(chat_history)} chat messages")
        return chat_history
        
    except Exception as e:
        # Table doesn't exist or other error
        logger.info(f"Chat history not available (table may not exist): {e}")
        return []


def build_markdown_export(
    document: dict,
    notes: Optional[str],
    flashcards: List[dict],
    chat_history: List[dict]
) -> str:
    """
    Assemble all data into a structured markdown document.
    
    Args:
        document: Document metadata dict
        notes: Generated notes markdown (or None)
        flashcards: List of flashcard dicts
        chat_history: List of message dicts
        
    Returns:
        Complete markdown string
    """
    lines = []
    
    # Title
    lines.append(f"# Document Export: {document['filename']}")
    lines.append("")
    
    # Document Information
    lines.append("## Document Information")
    lines.append("")
    lines.append(f"- **Filename**: {document['filename']}")
    
    if document.get('created_at'):
        created_at = document['created_at']
        lines.append(f"- **Upload Date**: {created_at}")
    
    if document.get('size_bytes'):
        size_mb = document['size_bytes'] / (1024 * 1024)
        lines.append(f"- **Size**: {size_mb:.2f} MB")
    
    if document.get('status'):
        lines.append(f"- **Status**: {document['status']}")
    
    if document.get('mime_type'):
        lines.append(f"- **Type**: {document['mime_type']}")
    
    lines.append("")
    
    # Generated Notes
    if notes:
        lines.append("## Generated Notes")
        lines.append("")
        lines.append(notes)
        lines.append("")
    
    # Flashcards
    if flashcards:
        lines.append(f"## Flashcards ({len(flashcards)} cards)")
        lines.append("")
        
        for i, card in enumerate(flashcards, 1):
            lines.append(f"### {i}. Question")
            lines.append(f"{card['question']}")
            lines.append("")
            lines.append(f"**Answer**: {card['answer']}")
            lines.append("")
            
            # SM-2 metadata
            metadata_parts = []
            if card.get('efactor'):
                metadata_parts.append(f"Easiness: {card['efactor']:.2f}")
            if card.get('repetitions') is not None:
                metadata_parts.append(f"Repetitions: {card['repetitions']}")
            if card.get('interval'):
                metadata_parts.append(f"Interval: {card['interval']} days")
            if card.get('next_review'):
                metadata_parts.append(f"Next review: {card['next_review']}")
            
            if metadata_parts:
                lines.append(f"*{', '.join(metadata_parts)}*")
                lines.append("")
    
    # Chat History
    if chat_history:
        lines.append(f"## Chat History ({len(chat_history)} messages)")
        lines.append("")
        
        for msg in chat_history:
            role = "User" if msg['role'] == 'user' else "Assistant"
            timestamp = msg.get('created_at', '')
            lines.append(f"**{role}** ({timestamp}):")
            lines.append(f"{msg['content']}")
            lines.append("")
    
    # Export Metadata
    lines.append("## Export Metadata")
    lines.append("")
    
    from datetime import datetime
    export_date = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    lines.append(f"- **Export Date**: {export_date}")
    
    # Determine included sections
    sections = ["metadata"]
    if notes:
        sections.append("notes")
    if flashcards:
        sections.append("flashcards")
    if chat_history:
        sections.append("chat_history")
    
    lines.append(f"- **Included Sections**: {', '.join(sections)}")
    lines.append("")
    
    return "\n".join(lines)


def convert_markdown_to_pdf(markdown_content: str) -> bytes:
    """
    Convert markdown to PDF using weasyprint.
    
    Args:
        markdown_content: Markdown text
        
    Returns:
        PDF bytes
        
    Raises:
        RuntimeError: If PDF generation fails
    """
    if not WEASYPRINT_AVAILABLE:
        raise RuntimeError("PDF export unavailable: weasyprint dependency not installed")
    if markdown is None:
        raise RuntimeError("PDF export unavailable: markdown dependency not installed")
    try:
        logger.info("Converting markdown to HTML")
        
        # Convert markdown to HTML with extensions
        html_content = markdown.markdown(
            markdown_content,
            extensions=['extra', 'codehilite', 'tables']
        )
        
        # Sanitize HTML to prevent injection (Comment 4)
        # Use allowlist suitable for PDFs (common HTML tags for document content)
        allowed_tags = [
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'p', 'br', 'hr',
            'strong', 'em', 'u', 'b', 'i',
            'ul', 'ol', 'li',
            'table', 'thead', 'tbody', 'tr', 'th', 'td',
            'code', 'pre',
            'blockquote',
            'a', 'span', 'div'
        ]
        allowed_attributes = {
            'a': ['href', 'title'],
            'code': ['class'],
            'pre': ['class'],
            '*': ['class']
        }
        
        sanitized_html = bleach.clean(
            html_content,
            tags=allowed_tags,
            attributes=allowed_attributes,
            strip=True
        )
        
        # Wrap in complete HTML document
        html_document = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
{PDF_CSS_TEMPLATE}
    </style>
</head>
<body>
{sanitized_html}
</body>
</html>
"""
        
        logger.info("Generating PDF with weasyprint")
        
        # Create HTML object and generate PDF
        html_obj = HTML(string=html_document)
        pdf_bytes = html_obj.write_pdf()
        
        logger.info(f"Generated PDF: {len(pdf_bytes)} bytes")
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"PDF generation failed: {e}", exc_info=True)
        raise RuntimeError(f"PDF generation failed: {str(e)}")


@router.post("", response_model=ExportResponse)
def export_document(
    request: ExportRequest,
    user=Depends(require_user),
):
    """
    Generate comprehensive export file (Markdown or PDF) containing document metadata,
    generated notes, flashcards, and optionally chat history.
    
    Args:
        request: ExportRequest with document_id, format, and include flags
        user: Authenticated user from JWT token
        
    Returns:
        ExportResponse with download_url, filename, size_bytes, included_sections,
        status, message, and processing_time_seconds
        
    Raises:
        HTTPException 404: Document not found or access denied
        HTTPException 422: Invalid format
        HTTPException 500: PDF generation failed, storage upload failed, signed URL generation failed
    """
    user_id = user["sub"]
    start_time = time.time()
    
    logger.info(
        "Starting export for user %s: document=%s, format=%s",
        user_id,
        request.document_id,
        request.format
    )
    
    supabase = get_supabase_client()
    
    try:
        # Fetch document and verify ownership
        try:
            result = (
                supabase.table("documents")
                .select("*")
                .eq("id", str(request.document_id))
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as e:
            logger.error("Database error fetching document: %s", e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error",
            )
        
        if not result.data:
            logger.warning(
                "Document %s not found or access denied for user %s",
                request.document_id,
                user_id
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or access denied",
            )
        
        document = result.data[0]
        
        # Fetch optional data sources
        notes = None
        flashcards = []
        chat_history = []
        
        if request.include_notes:
            notes = fetch_notes_from_storage(supabase, user_id, str(request.document_id))
        
        if request.include_flashcards:
            flashcards = fetch_flashcards_from_db(supabase, user_id, str(request.document_id))
        
        if request.include_chat_history:
            chat_history = fetch_chat_history_from_db(supabase, user_id, str(request.document_id))
        
        logger.info(
            "Export for document %s: notes=%s, flashcards=%d, chat_history=%d",
            request.document_id,
            bool(notes),
            len(flashcards),
            len(chat_history)
        )
        
        # Build markdown export
        markdown_content = build_markdown_export(document, notes, flashcards, chat_history)
        
        # Generate export file based on format
        if request.format == "markdown":
            export_bytes = markdown_content.encode('utf-8')
            content_type = "text/markdown"
            file_extension = ".md"
        elif request.format == "pdf":
            try:
                export_bytes = convert_markdown_to_pdf(markdown_content)
                content_type = "application/pdf"
                file_extension = ".pdf"
            except RuntimeError as e:
                logger.error("PDF generation failed: %s", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"PDF generation failed: {str(e)}",
                )
        else:
            # Should not reach here due to Pydantic validation
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid format",
            )
        
        # Prepare storage path and filename
        filename = f"{request.document_id}-export{file_extension}"
        storage_path = f"processed/{user_id}/{filename}"
        
        logger.info(
            "Uploading export to storage: %s (%d bytes)",
            storage_path,
            len(export_bytes)
        )
        
        # Upload to Supabase Storage (Comment 2: match generate.py pattern)
        try:
            upload_response = supabase.storage.from_(EXPORT_BUCKET).upload(
                path=storage_path,
                file=export_bytes,
                file_options={
                    "content-type": content_type,  # use dash not underscore
                    "upsert": "true",  # must be string, not boolean
                },
            )
            if hasattr(upload_response, "error") and upload_response.error:
                logger.error("Storage upload returned error: %s", upload_response.error)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to upload export to storage",
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Storage upload failed: %s", e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload export to storage",
            )
        
        # Generate signed download URL (Comment 3: robust parsing like generate.py)
        try:
            url_response = supabase.storage.from_(EXPORT_BUCKET).create_signed_url(
                storage_path,
                expires_in=SIGNED_URL_EXPIRY
            )
            
            # Normalize response shape (dict or object)
            signed_url = None
            if isinstance(url_response, dict):
                signed_url = url_response.get("signedURL") or url_response.get("signedUrl") or url_response.get("signed_url")
            else:
                signed_url = getattr(url_response, "signedURL", None)
            
            if not signed_url:
                raise ValueError("Signed URL missing in response")
            
            download_url = signed_url
            
        except Exception as e:
            logger.error("Signed URL generation failed: %s", e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate download URL",
            )
        
        # Determine included sections
        included_sections = ["metadata"]
        if notes:
            included_sections.append("notes")
        if flashcards:
            included_sections.append("flashcards")
        if chat_history:
            included_sections.append("chat_history")
        
        # Build response
        processing_time = time.time() - start_time
        
        response = ExportResponse(
            document_id=request.document_id,
            format=request.format,
            filename=filename,
            storage_path=storage_path,
            download_url=download_url,
            size_bytes=len(export_bytes),
            included_sections=included_sections,
            status="success",
            message="Export generated successfully",
            processing_time_seconds=processing_time
        )
        
        logger.info(
            "Export completed: format=%s, size=%d bytes, sections=%s, time=%.2fs",
            request.format,
            len(export_bytes),
            included_sections,
            processing_time
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in export: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )
