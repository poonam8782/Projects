from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator


class HealthResponse(BaseModel):
    status: str

    model_config = {"from_attributes": True}


class UserInfo(BaseModel):
    sub: str
    email: Optional[EmailStr] = None
    role: str

    model_config = {"from_attributes": True}


class AuthVerifyResponse(BaseModel):
    sub: str
    role: str
    message: str


class DocumentUploadResponse(BaseModel):
    """Response schema for document upload endpoint."""
    
    id: UUID
    filename: str
    size_bytes: int
    mime_type: str
    status: str
    storage_path: str
    extracted_text_preview: Optional[str] = None
    created_at: datetime
    message: str
    
    model_config = {"from_attributes": True}


class DocumentMetadata(BaseModel):
    """Document metadata for history listings (Sprint 1 Phase 2)."""
    
    id: UUID
    filename: str
    size_bytes: int
    mime_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class HistoryResponse(BaseModel):
    """Response schema for document history endpoint."""
    
    documents: list[DocumentMetadata]
    total: int
    message: Optional[str] = ""
    
    model_config = {"from_attributes": True}


class EmbeddingResponse(BaseModel):
    """Response schema for embedding generation endpoint (Sprint 2)."""
    
    document_id: UUID
    chunk_count: int
    embedding_count: int
    status: str
    message: str
    processing_time_seconds: float
    
    model_config = {"from_attributes": True}


class ChatMessage(BaseModel):
    """Single message in a conversation (user or assistant turn)."""

    role: str
    content: str

    model_config = {"from_attributes": True}

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in {"user", "model"}:
            raise ValueError("role must be either 'user' or 'model'")
        return value


class ChunkProvenance(BaseModel):
    """Provenance information for a retrieved chunk (source attribution)."""

    chunk_id: int
    chunk_index: int
    chunk_text: str
    similarity: float

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    """Request schema for RAG chat endpoint (Sprint 3)."""

    document_id: UUID
    query: str
    history: List[ChatMessage] = Field(default_factory=list)
    max_chunks: int = 5
    similarity_threshold: float = 0.3

    model_config = {"from_attributes": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("query cannot be empty")
        return value

    @field_validator("max_chunks")
    @classmethod
    def validate_max_chunks(cls, value: int) -> int:
        if value < 1 or value > 20:
            raise ValueError("max_chunks must be between 1 and 20")
        return value

    @field_validator("similarity_threshold")
    @classmethod
    def validate_similarity_threshold(cls, value: float) -> float:
        if value < 0.0 or value > 1.0:
            raise ValueError("similarity_threshold must be between 0.0 and 1.0")
        return value


class ChatStreamEvent(BaseModel):
    """SSE event schema for chat streaming (Sprint 3)."""

    event: str
    token: Optional[str] = None
    chunks: Optional[List[ChunkProvenance]] = None
    finish_reason: Optional[str] = None
    error: Optional[str] = None

    model_config = {"from_attributes": True}


class GenerateNotesResponse(BaseModel):
    """Response schema for notes generation endpoint (Sprint 4).

    Provides metadata about generated markdown study notes derived from a document's
    extracted text. Includes a short preview and a signed download URL.
    """
    document_id: UUID
    filename: str
    storage_path: str
    download_url: str
    content_preview: Optional[str] = None
    size_bytes: int
    status: str
    message: str
    processing_time_seconds: float

    model_config = {"from_attributes": True}


class GetNotesResponse(BaseModel):
    """Response schema for retrieving existing notes content from storage.

    Returns the full markdown content of previously generated study notes
    along with metadata. Used when viewing notes on the frontend.
    """
    document_id: UUID
    filename: str
    content: str
    size_bytes: int
    status: str
    message: str

    model_config = {"from_attributes": True}


class GenerateMindmapResponse(BaseModel):
    """Response schema for mindmap generation endpoint (Sprint 4).

    Provides metadata about an AI-generated mindmap derived from a document's
    extracted text. Supports multiple formats: SVG, Mermaid, and Markmap.
    Includes content preview and a signed download URL.
    """

    document_id: UUID
    filename: str
    storage_path: str
    download_url: str
    format: str  # "svg", "mermaid", or "markmap"
    content_preview: Optional[str] = None
    size_bytes: int
    node_count: Optional[int] = None
    status: str
    message: str
    processing_time_seconds: float

    model_config = {"from_attributes": True}


# ========================================================================
# Flashcard schemas (Sprint 5)
# ========================================================================


class FlashcardResponse(BaseModel):
    """Single flashcard with SM-2 scheduling parameters (Sprint 5).

    Represents a flashcard Q&A pair with spaced repetition metadata
    for optimal review scheduling using the SM-2 algorithm.
    """

    # Allow either UUID or arbitrary string identifiers used in tests. Using str prevents
    # validation failures for test fixtures that supply 'fc-uuid-1' style IDs.
    id: str
    question: str
    answer: str
    efactor: float
    repetitions: int
    interval: int
    next_review: datetime
    last_reviewed: Optional[datetime] = None
    document_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True, "extra": "ignore"}


class GenerateFlashcardsResponse(BaseModel):
    """Response schema for flashcard generation endpoint (Sprint 5).

    Provides metadata about AI-generated flashcards from document text,
    including the list of flashcards with initial SM-2 values.
    """

    document_id: UUID
    flashcard_count: int
    flashcards: List[FlashcardResponse]
    status: str
    message: str
    processing_time_seconds: float

    model_config = {"from_attributes": True, "extra": "ignore"}


class ReviewRequest(BaseModel):
    """Request schema for flashcard review endpoint (Sprint 5).

    Contains the flashcard identifier (string to allow custom id formats used in
    tests and potential future non-UUID keys) and quality rating for SM-2 calculation.
    """

    flashcard_id: str
    quality: int

    @field_validator("quality")
    @classmethod
    def validate_quality(cls, v: int) -> int:
        """Ensure quality rating is in valid range [0, 5]."""
        if not isinstance(v, int) or v < 0 or v > 5:
            raise ValueError("Quality must be an integer between 0 and 5")
        return v

    model_config = {"from_attributes": True, "extra": "ignore"}


class ReviewResponse(BaseModel):
    """Response schema for flashcard review endpoint (Sprint 5).

    Provides the updated flashcard, next due flashcard, and progress metrics.
    """


    reviewed_flashcard: FlashcardResponse
    next_flashcard: Optional[FlashcardResponse] = None
    due_count: int
    message: str

    model_config = {"from_attributes": True, "extra": "ignore"}


class SynthesizeRequest(BaseModel):
    """Request schema for multi-document synthesis endpoint (Sprint 6)."""

    document_ids: List[UUID]
    synthesis_type: str
    include_embeddings: bool = False

    @field_validator("document_ids")
    @classmethod
    def validate_document_ids(cls, v):
        if len(v) < 2:
            raise ValueError("At least 2 documents are required for synthesis")
        if len(v) > 10:
            raise ValueError("Maximum 10 documents allowed for synthesis")
        return v

    @field_validator("synthesis_type")
    @classmethod
    def validate_synthesis_type(cls, v):
        if v not in ["summary", "comparison"]:
            raise ValueError("synthesis_type must be 'summary' or 'comparison'")
        return v

    model_config = {"from_attributes": True}


class DocumentSource(BaseModel):
    """Source attribution for a document in synthesis output."""

    document_id: UUID
    filename: str
    key_points: List[str]

    model_config = {"from_attributes": True}


class SynthesizeResponse(BaseModel):
    """Response schema for multi-document synthesis endpoint (Sprint 6)."""

    synthesis_type: str
    markdown_output: str
    sources: List[DocumentSource]
    document_count: int
    total_text_length: int
    status: str
    message: str
    processing_time_seconds: float

    model_config = {"from_attributes": True}


class ExportRequest(BaseModel):
    """Request schema for document export endpoint (Sprint 6)."""

    document_id: UUID
    format: str
    include_notes: bool = True
    include_flashcards: bool = True
    include_chat_history: bool = False

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate export format."""
        if v not in ["markdown", "pdf"]:
            raise ValueError("format must be 'markdown' or 'pdf'")
        return v

    model_config = {"from_attributes": True}


class ExportResponse(BaseModel):
    """Response schema for document export endpoint (Sprint 6)."""

    document_id: UUID
    format: str
    filename: str
    storage_path: str
    download_url: str
    size_bytes: int
    included_sections: List[str]
    status: str
    message: str
    processing_time_seconds: float

    model_config = {"from_attributes": True}


# Future schemas roadmap (to be implemented in upcoming sprints):
# Sprint 1: DocumentUploadResponse ✓, DocumentMetadata ✓, HistoryResponse ✓
# Sprint 2: EmbeddingResponse ✓, EmbedRequest (pending), EmbedResponse (pending)
# Sprint 3: ChatRequest ✓, ChatMessage ✓, ChatStreamEvent ✓, ChunkProvenance ✓
# Sprint 4: GenerateNotesResponse ✓, GenerateMindmapResponse ✓
# Sprint 5: FlashcardResponse ✓, GenerateFlashcardsResponse ✓, ReviewRequest ✓, ReviewResponse ✓
# Sprint 6: SynthesizeRequest ✓, DocumentSource ✓, SynthesizeResponse ✓, ExportRequest ✓, ExportResponse ✓

