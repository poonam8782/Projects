/**
 * API service for Neura backend.
 * Provides typed methods for all endpoints with automatic JWT authentication and error handling.
 */

import { createClient } from '@/lib/supabase/client';
import { DocumentMetadata, HistoryResponse, DownloadUrlResponse, EmbeddingResponse, ChatRequest, ChunkProvenance, GenerateNotesResponse, GetNotesResponse, GenerateMindmapResponse, FlashcardResponse, GenerateFlashcardsResponse, ReviewResponse, ExportRequest, ExportResponse, SynthesizeRequest, SynthesizeResponse } from '@/lib/types/document';
import { createSSEConnection } from '@/lib/utils/sse-parser';
import type { MutableRefObject } from 'react';

// Backend URL from environment variable with fallback
const API_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

/**
 * Document upload response from backend
 */
export interface DocumentUploadResponse {
  id: string;
  filename: string;
  size_bytes: number;
  mime_type: string;
  status: string;
  storage_path: string;
  extracted_text_preview: string | null;
  created_at: string;
  message: string;
}

/**
 * Returns JWT access token from Supabase session for API authentication
 */
async function getAuthToken(): Promise<string | null> {
  try {
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    return session?.access_token || null;
  } catch (error) {
    console.error('Failed to get auth token:', error);
    return null;
  }
}

/**
 * Parses API error responses and throws with user-friendly messages
 */
async function handleApiError(response: Response): Promise<never> {
  let errorMessage = 'An error occurred';
  
  try {
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || errorData.error || errorMessage;
    } else {
      errorMessage = await response.text() || errorMessage;
    }
  } catch {
    // If parsing fails, use default message
  }
  
  // Prefix with status code and status text for diagnostics
  const statusPrefix = `[${response.status}] ${response.statusText}`;
  throw new Error(`${statusPrefix}: ${errorMessage}`);
}

/**
 * Uploads a document file with progress tracking.
 * Returns document metadata including extracted text preview.
 */
export async function uploadDocument(
  file: File,
  onProgress?: (progress: number) => void,
  xhrRef?: MutableRefObject<XMLHttpRequest | null>
): Promise<DocumentUploadResponse> {
  const token = await getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }

  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file);

    const xhr = new XMLHttpRequest();
    
    // Store XHR reference for cleanup
    if (xhrRef) {
      xhrRef.current = xhr;
    }

    // Track upload progress
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        const progress = Math.round((event.loaded / event.total) * 100);
        onProgress(progress);
      }
    };

    // Handle successful upload
    xhr.onload = () => {
      // Clear XHR reference when complete
      if (xhrRef) {
        xhrRef.current = null;
      }
      
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const response = JSON.parse(xhr.responseText);
          resolve(response);
  } catch {
          reject(new Error('Failed to parse upload response'));
        }
      } else {
        try {
          const errorData = JSON.parse(xhr.responseText);
          reject(new Error(errorData.detail || errorData.message || 'Failed to upload document'));
  } catch {
          reject(new Error('Failed to upload document'));
        }
      }
    };

    // Handle network errors
    xhr.onerror = () => {
      // Clear XHR reference on error
      if (xhrRef) {
        xhrRef.current = null;
      }
      reject(new Error('Failed to upload document'));
    };
    
    // Handle abort
    xhr.onabort = () => {
      // Clear XHR reference on abort
      if (xhrRef) {
        xhrRef.current = null;
      }
      reject(new Error('Upload cancelled'));
    };

    // Open and send request
    xhr.open('POST', `${API_BASE_URL}/upload`);
    xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    xhr.send(formData);
  });
}

/**
 * Fetches list of user's documents ordered by creation date (newest first)
 */
export async function getDocuments(): Promise<DocumentMetadata[]> {
  const token = await getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }

  try {
    const response = await fetch(`${API_BASE_URL}/history`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    const data: HistoryResponse = await response.json();
    return data.documents;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Failed to fetch documents');
  }
}

/**
 * Fetches metadata for a single document by ID.
 *
 * @param documentId - UUID of the document to fetch
 * @returns DocumentMetadata with all document fields
 * @throws Error if document not found or access denied (404) or other failures
 */
export async function getDocument(documentId: string): Promise<DocumentMetadata> {
  const token = await getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }

  try {
    const response = await fetch(`${API_BASE_URL}/history/${documentId}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    const data: DocumentMetadata = await response.json();
    return data;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Failed to fetch document');
  }
}

/**
 * Deletes a document and all associated data (embeddings, flashcards).
 * Requires document ownership.
 */
export async function deleteDocument(documentId: string): Promise<void> {
  const token = await getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }

  try {
    const response = await fetch(`${API_BASE_URL}/history/${documentId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      await handleApiError(response);
    }
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Failed to delete document');
  }
}

/**
 * Generates a signed download URL for a document (60 second TTL).
 * Opens in new tab.
 */
export async function getDownloadUrl(documentId: string): Promise<string> {
  const token = await getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }

  try {
    const response = await fetch(`${API_BASE_URL}/history/download/${documentId}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    const data: DownloadUrlResponse = await response.json();
    return data.url;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Failed to get download URL');
  }
}

/**
 * Generates embeddings for a document's text chunks using Gemini API.
 * 
 * @param documentId - UUID of the document to embed
 * @returns EmbeddingResponse with chunk count, embedding count, status, and processing time
 * 
 * Requires document to have extracted text (status 'extracted').
 * Processing time varies by document size (1-2 seconds per chunk).
 */
export async function embedDocument(documentId: string): Promise<EmbeddingResponse> {
  const token = await getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }

  try {
    const response = await fetch(`${API_BASE_URL}/embed?document_id=${documentId}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      await handleApiError(response);
    }

    const data: EmbeddingResponse = await response.json();
    return data;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Failed to generate embeddings');
  }
}

/**
 * Initiates a RAG chat session with a document using SSE streaming.
 *
 * Uses fetch + ReadableStream to parse Server-Sent Events (SSE) because EventSource
 * does not support POST requests or custom Authorization headers.
 * Conversation history is stateless; send full prior turns with each request.
 *
 * @param request ChatRequest payload (document_id, query, history, optional controls)
 * @param onToken Callback invoked for each streamed token
 * @param onProvenance Callback invoked once with source chunks for current answer
 * @param onComplete Callback invoked when model finishes streaming (finish_reason)
 * @param onError Callback invoked on any error (network or server)
 */
export async function chatWithDocument(
  request: ChatRequest,
  onToken: (token: string) => void,
  onProvenance: (chunks: ChunkProvenance[]) => void,
  onComplete: (finishReason: string) => void,
  onError: (error: string) => void,
  abortSignal?: AbortSignal
): Promise<void> {
  const token = await getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  try {
    await createSSEConnection(
      `${API_BASE_URL}/chat`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
        signal: abortSignal,
      },
      ({ event, data }) => {
        type SSEPayload = {
          chunks?: ChunkProvenance[];
          token?: string;
          finish_reason?: string;
          error?: string;
          [key: string]: unknown;
        };
        const payload: SSEPayload = (data ?? {}) as SSEPayload;
        switch (event) {
          case 'provenance':
            if (Array.isArray(payload.chunks)) {
              onProvenance(payload.chunks);
            }
            break;
          case 'token':
            if (typeof payload.token === 'string') {
              onToken(payload.token);
            }
            break;
          case 'done':
            onComplete(typeof payload.finish_reason === 'string' ? payload.finish_reason : 'stop');
            break;
            
          case 'error':
            if (typeof payload.error === 'string') {
              onError(payload.error);
            } else {
              onError('Unknown streaming error');
            }
            break;
          default:
            // Ignore other events or heartbeats
            break;
        }
      },
      (err) => {
        onError(err.message || 'Network error');
      }
    );
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Failed to start chat';
    onError(message);
  } finally {
    // No internal controller to clean up; caller manages abortion.
  }
}

/**
 * Generates study notes (markdown) for a document via backend Gemini integration.
 * Returns structured metadata including preview and signed URL.
 */
export async function generateNotes(documentId: string): Promise<GenerateNotesResponse> {
  const token = await getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  try {
    const response = await fetch(`${API_BASE_URL}/generate/notes?document_id=${documentId}` , {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    if (!response.ok) {
      await handleApiError(response);
    }
    const data: GenerateNotesResponse = await response.json();
    return data;
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('Failed to generate notes');
  }
}

/**
 * Fetches the full notes content for a document from storage.
 * Requires the document to have generated notes via POST /generate/notes.
 * Returns null if notes haven't been generated (404).
 * 
 * @throws Error if not authenticated or server error (500)
 */
export async function getNotes(documentId: string): Promise<GetNotesResponse | null> {
  const token = await getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  try {
    const response = await fetch(`${API_BASE_URL}/generate/notes/${documentId}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    
    // Handle 404 - notes not generated yet
    if (response.status === 404) {
      return null;
    }
    
    if (!response.ok) {
      await handleApiError(response);
    }
    const data: GetNotesResponse = await response.json();
    return data;
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('Failed to fetch notes');
  }
}

/**
 * Generates a mindmap for a document via backend.
 * Supports multiple formats: svg, mermaid (default), markmap
 * Returns metadata including preview and signed URL.
 */
export async function generateMindmap(
  documentId: string,
  format: 'svg' | 'mermaid' | 'markmap' = 'mermaid'
): Promise<GenerateMindmapResponse> {
  const token = await getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  try {
    const response = await fetch(
      `${API_BASE_URL}/generate/mindmap?document_id=${documentId}&format=${format}`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      }
    );
    if (!response.ok) {
      await handleApiError(response);
    }
    const data: GenerateMindmapResponse = await response.json();
    return data;
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('Failed to generate mindmap');
  }
}

// Mindmap JSON (deterministic) ---------------------------------------------
export interface MindmapNode {
  id: string;
  label: string;
  children?: MindmapNode[];
}

export async function getMindmapData(documentId: string): Promise<{ document_id: string; root: MindmapNode }>{
  const token = await getAuthToken();
  if (!token) throw new Error('Not authenticated');
  const response = await fetch(`${API_BASE_URL}/mindmap/data?document_id=${documentId}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    await handleApiError(response);
  }
  return response.json();
}

/**
 * Generate Q&A flashcard pairs from a document's extracted text.
 * 
 * Calls the Gemini API to generate flashcards in JSON format, parses and validates
 * the structure, then batch inserts into the flashcards table with SM-2 initial values.
 * 
 * @param documentId - UUID of the document to generate flashcards from
 * @param targetCount - Target number of flashcards (default 10, range 1-50)
 * @returns Response with flashcards list and SM-2 initial values
 * 
 * Requirements:
 * - Document must have extracted text
 * 
 * Note: Processing time ~5-15 seconds depending on document length and target count
 */
export async function generateFlashcards(documentId: string, targetCount: number = 10): Promise<GenerateFlashcardsResponse> {
  const token = await getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  try {
    const response = await fetch(`${API_BASE_URL}/generate/flashcards?document_id=${documentId}&target_count=${targetCount}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    if (!response.ok) {
      await handleApiError(response);
    }
    const data: GenerateFlashcardsResponse = await response.json();
    return data;
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('Failed to generate flashcards');
  }
}

/**
 * Submit flashcard review with quality rating and update SM-2 schedule.
 * 
 * Calls the backend to update the flashcard's SM-2 parameters (efactor, repetitions,
 * interval, next_review) based on the quality rating, and returns the next due flashcard.
 * 
 * @param flashcardId - UUID of the flashcard to review
 * @param quality - Quality rating (0-5 scale):
 *   - 0: Complete blackout
 *   - 1: Incorrect but familiar
 *   - 2: Incorrect but easy after seeing
 *   - 3: Correct with effort
 *   - 4: Correct with hesitation
 *   - 5: Perfect recall
 * @returns Response with updated flashcard, next due flashcard, and due count
 * 
 * Note: SM-2 algorithm adjusts interval based on quality (1d → 6d → exponential growth)
 */
export async function reviewFlashcard(flashcardId: string, quality: number): Promise<ReviewResponse> {
  const token = await getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  
  // Validate quality range
  if (!Number.isInteger(quality) || quality < 0 || quality > 5) {
    throw new Error('Quality must be an integer between 0 and 5');
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/flashcards/review`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ flashcard_id: flashcardId, quality }),
    });
    if (!response.ok) {
      await handleApiError(response);
    }
    const data: ReviewResponse = await response.json();
    return data;
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('Failed to review flashcard');
  }
}

/**
 * Fetches all flashcards for a specific document
 * 
 * @param documentId - UUID of the document to fetch flashcards for
 * @returns Array of FlashcardResponse objects with SM-2 scheduling data
 * 
 * Requirements:
 * - Requires document ownership (verified by backend)
 * 
 * Note: Returns all flashcards regardless of due status. Filter by next_review <= now() for due cards.
 */
export async function getFlashcardsByDocument(documentId: string): Promise<FlashcardResponse[]> {
  const token = await getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }
  try {
    const response = await fetch(`${API_BASE_URL}/flashcards?document_id=${documentId}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    if (!response.ok) {
      await handleApiError(response);
    }
    const data: FlashcardResponse[] = await response.json();
    return data;
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('Failed to fetch flashcards');
  }
}

/**
 * Generates a comprehensive export file (Markdown or PDF) with metadata, notes, flashcards, and chat history.
 * 
 * @param request - Export request with document_id, format, and include flags
 * @returns ExportResponse with download URL and included sections
 * @throws Error if export fails
 * 
 * Processing time: ~1-3s for Markdown, ~2-5s for PDF
 */
export async function exportDocument(request: ExportRequest): Promise<ExportResponse> {
  try {
    const token = await getAuthToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${API_BASE_URL}/export`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    if (!response.ok) {
      await handleApiError(response);
    }
    const data: ExportResponse = await response.json();
    return data;
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('Failed to export document');
  }
}

/**
 * Generates a unified summary or comparative analysis from multiple documents.
 * 
 * @param request - Synthesis request with document_ids, synthesis_type, and include_embeddings flag
 * @returns SynthesizeResponse with markdown output and source attribution
 * @throws Error if synthesis fails
 * 
 * Requirements: 2-10 documents, all must have extracted text
 * Processing time: ~15-35 seconds
 */
export async function synthesizeDocuments(request: SynthesizeRequest): Promise<SynthesizeResponse> {
  try {
    const token = await getAuthToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${API_BASE_URL}/synthesize`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    if (!response.ok) {
      await handleApiError(response);
    }
    const data: SynthesizeResponse = await response.json();
    return data;
  } catch (error) {
    if (error instanceof Error) throw error;
    throw new Error('Failed to synthesize documents');
  }
}

