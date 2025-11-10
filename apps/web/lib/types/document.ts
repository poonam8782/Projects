/**
 * TypeScript types for document data matching backend Pydantic schemas.
 */

/**
 * Document metadata for history listings.
 */
export interface DocumentMetadata {
  id: string;
  filename: string;
  size_bytes: number;
  mime_type: string;
  status: 'uploaded' | 'extracted' | 'embedded' | 'failed';
  created_at: string;
  updated_at: string;
}

/**
 * Response from document history endpoint.
 */
export interface HistoryResponse {
  documents: DocumentMetadata[];
  total: number;
  message?: string;
}

/**
 * Response from download URL generation endpoint.
 */
export interface DownloadUrlResponse {
  url: string;
  expires_in: number;
}

/**
 * Response from embedding generation endpoint (Sprint 2).
 */
export interface EmbeddingResponse {
  document_id: string;
  chunk_count: number;
  embedding_count: number;
  status: 'embedded' | 'failed';
  message: string;
  processing_time_seconds: number;
}

/**
 * Chat message exchanged between user and model.
 */
export interface ChatMessage {
  role: 'user' | 'model';
  content: string;
}

/**
 * Provenance information for a matched chunk used in RAG context.
 */
export interface ChunkProvenance {
  chunk_id: number;
  chunk_index: number;
  chunk_text: string;
  similarity: number;
}

/**
 * Chat request payload matching backend Pydantic schema.
 */
export interface ChatRequest {
  document_id: string;
  query: string;
  history: ChatMessage[];
  max_chunks?: number;
  similarity_threshold?: number;
}

/**
 * Streamed SSE event from chat endpoint.
 */
export interface ChatStreamEvent {
  event: 'token' | 'provenance' | 'done' | 'error';
  token?: string;
  chunks?: ChunkProvenance[];
  finish_reason?: string;
  error?: string;
}

/**
 * Response from notes generation endpoint.
 */
export interface GenerateNotesResponse {
  document_id: string;
  filename: string;
  storage_path: string;
  download_url: string;
  content_preview: string;
  size_bytes: number;
  status: 'success' | 'failed';
  message: string;
  processing_time_seconds: number;
}

/**
 * Response when fetching existing notes content from the backend.
 * Returns the full markdown content of previously generated study notes.
 */
export interface GetNotesResponse {
  document_id: string;
  filename: string;
  content: string;
  size_bytes: number;
  status: string;
  message: string;
}

/**
 * Response from mindmap generation endpoint.
 */
export interface GenerateMindmapResponse {
  document_id: string;
  filename: string;
  storage_path: string;
  download_url: string;
  svg_preview: string | null;
  size_bytes: number;
  node_count?: number | null;
  status: 'success' | 'failed';
  message: string;
  processing_time_seconds: number;
}

/**
 * Flashcard with SM-2 scheduling parameters (Sprint 5).
 */
export interface FlashcardResponse {
  id: string;
  question: string;
  answer: string;
  efactor: number;
  repetitions: number;
  interval: number;
  next_review: string;
  last_reviewed: string | null;
  document_id: string | null;
  created_at: string;
}

/**
 * Response from flashcard generation endpoint (Sprint 5).
 */
export interface GenerateFlashcardsResponse {
  document_id: string;
  flashcard_count: number;
  flashcards: FlashcardResponse[];
  status: string;
  message: string;
  processing_time_seconds: number;
}

/**
 * Request payload for flashcard review endpoint (Sprint 5).
 */
export interface ReviewRequest {
  flashcard_id: string;
  quality: number;
}

/**
 * Response from flashcard review endpoint (Sprint 5).
 */
export interface ReviewResponse {
  reviewed_flashcard: FlashcardResponse;
  next_flashcard: FlashcardResponse | null;
  due_count: number;
  message: string;
}

/**
 * Request to export a single document (Sprint 6).
 */
export interface ExportRequest {
  document_id: string;
  format: 'markdown' | 'pdf';
  include_notes?: boolean;
  include_flashcards?: boolean;
  include_chat_history?: boolean;
}

/**
 * Response from document export endpoint (Sprint 6).
 */
export interface ExportResponse {
  document_id: string;
  format: string;
  filename: string;
  storage_path: string;
  download_url: string;
  size_bytes: number;
  included_sections: string[];
  status: string;
  message: string;
  processing_time_seconds: number;
}

/**
 * Request to synthesize multiple documents (Sprint 6).
 */
export interface SynthesizeRequest {
  document_ids: string[];
  synthesis_type: 'summary' | 'comparison';
  include_embeddings?: boolean;
}

/**
 * Source document with attribution for synthesis (Sprint 6).
 */
export interface DocumentSource {
  document_id: string;
  filename: string;
  key_points: string[];
}

/**
 * Response from multi-document synthesis endpoint (Sprint 6).
 */
export interface SynthesizeResponse {
  synthesis_type: string;
  markdown_output: string;
  sources: DocumentSource[];
  document_count: number;
  total_text_length: number;
  status: string;
  message: string;
  processing_time_seconds: number;
}
