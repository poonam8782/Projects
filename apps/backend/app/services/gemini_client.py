"""
Gemini AI Embedding Generation Service

This module provides Gemini AI embedding generation for document chunks and user queries.
It uses the google-generativeai SDK with the models/embedding-001 model configured for
1536-dimensional vectors. The client handles API errors, rate limiting with exponential
backoff, and provides both single and batch embedding generation.

Key features:
- Generates embeddings using Gemini's embedding-001 model
- Supports configurable dimensions (default: 1536)
- Handles rate limiting with exponential backoff
- Provides both single and batch embedding generation
- Comprehensive error handling and logging
"""

import logging
import time
from typing import Iterator, List, Optional, TypedDict

import google.generativeai as genai
from google.generativeai import GenerativeModel

from app.core.config import get_settings

# Logger setup
logger = logging.getLogger(__name__)

# Constants
DEFAULT_MODEL = "models/embedding-001"  # Recommended Gemini embedding model
DEFAULT_DIMENSIONS = 1536  # Target embedding dimensions (user requirement)
MAX_RETRIES = 5  # Maximum retry attempts for rate limiting (increased for free tier)
INITIAL_RETRY_DELAY = 2.0  # Initial delay in seconds for exponential backoff (increased from 1.0)
MAX_RETRY_DELAY = 120.0  # Maximum delay between retries (increased from 60.0)
BATCH_DELAY = 4.5  # Delay between embedding requests to stay under free tier limit (15/min = 4s spacing)
DEFAULT_CHAT_MODEL = get_settings().gemini_chat_model  # Configurable via env (defaults to gemini-2.5-pro)
CHAT_TEMPERATURE = 0.7  # Balanced creativity
MAX_OUTPUT_TOKENS = get_settings().gemini_max_output_tokens  # Can be overridden per call


class ChatHistoryEntry(TypedDict):
    """Gemini chat history entry structure."""

    role: str
    parts: List[str]

# Track initialization state
_client_initialized = False


def _initialize_gemini_client() -> None:
    """
    Initialize the Gemini client with API key from settings.
    
    This function should be called once at module import time or lazily on first use.
    
    Raises:
        ValueError: If GEMINI_API_KEY is not configured
        RuntimeError: If client initialization fails
    """
    global _client_initialized
    
    if _client_initialized:
        return
    
    try:
        settings = get_settings()
        
        # Validate API key is configured
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not configured")
        
        # Configure the SDK with API key
        genai.configure(api_key=settings.gemini_api_key)
        
        logger.info(f"Gemini client initialized with model {DEFAULT_MODEL}")
        _client_initialized = True
        
    except ValueError:
        # Re-raise ValueError for missing API key
        raise
    except Exception as e:
        logger.error(f"Failed to initialize Gemini client: {e}")
        raise RuntimeError(f"Failed to initialize Gemini client: {e}")


def init_gemini_client() -> None:
    """
    Public function to initialize the Gemini client.
    
    Should be called at application startup.
    
    Raises:
        ValueError: If GEMINI_API_KEY is not configured
        RuntimeError: If client initialization fails
    """
    _initialize_gemini_client()


def generate_embedding(
    text: str,
    task_type: str = "RETRIEVAL_DOCUMENT",
    model: str = DEFAULT_MODEL,
    dimensions: int = DEFAULT_DIMENSIONS
) -> List[float]:
    """
    Generate embedding vector for a single text using Gemini API.
    
    Args:
        text: Input string to generate embedding for
        task_type: Either "RETRIEVAL_DOCUMENT" (for document chunks) or 
                   "RETRIEVAL_QUERY" (for user queries). Affects embedding optimization.
        model: Gemini model name (default: models/embedding-001)
        dimensions: Output dimensionality (default: 1536, max: 3072)
    
    Returns:
        List of floats representing the embedding vector
    
    Raises:
        ValueError: If input is invalid (empty text, invalid task_type, invalid dimensions)
        RuntimeError: If API call fails after retries (rate limiting, invalid API key, network errors)
    
    Note:
        Uses exponential backoff for rate limiting (429 errors). Retries up to MAX_RETRIES times
        with delays: 1s, 2s, 4s (capped at MAX_RETRY_DELAY).
    """
    # Input validation
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")
    
    valid_task_types = ["RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"]
    if task_type not in valid_task_types:
        raise ValueError(f"Invalid task_type: {task_type}. Must be one of {valid_task_types}")
    
    if dimensions <= 0 or dimensions > 3072:
        raise ValueError(f"Invalid dimensions: {dimensions}. Must be between 1 and 3072")
    
    # Ensure client is initialized
    _initialize_gemini_client()
    
    # Retry loop with exponential backoff
    retry_count = 0
    retry_delay = INITIAL_RETRY_DELAY
    
    while retry_count <= MAX_RETRIES:
        try:
            # Call Gemini API
            response = genai.embed_content(
                model=model,
                content=text,
                task_type=task_type,
                output_dimensionality=dimensions
            )
            
            # Extract embedding from response
            raw = response.get('embedding')
            if isinstance(raw, dict) and 'values' in raw:
                embedding = raw['values']
            elif isinstance(raw, list):
                embedding = raw
            else:
                raise RuntimeError('Unexpected embedding response shape')
            
            # Validate embedding length
            if len(embedding) != dimensions:
                raise RuntimeError(
                    f"Embedding dimension mismatch: expected {dimensions}, got {len(embedding)}"
                )
            
            return embedding
            
        except Exception as e:
            error_message = str(e).lower()
            
            # Check for rate limiting
            if "429" in error_message or "quota" in error_message or "rate limit" in error_message:
                if retry_count < MAX_RETRIES:
                    logger.warning(
                        f"Rate limited by Gemini API, retrying in {retry_delay}s "
                        f"(attempt {retry_count + 1}/{MAX_RETRIES})"
                    )
                    time.sleep(retry_delay)
                    retry_count += 1
                    retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)
                    continue
                else:
                    # Max retries exceeded
                    break
            
            # Check for invalid API key
            if "api key" in error_message or "authentication" in error_message:
                logger.error(f"Invalid Gemini API key: {e}")
                raise RuntimeError("Invalid Gemini API key")
            
            # Check for invalid input
            if "invalid argument" in error_message or "invalid input" in error_message:
                logger.error(f"Invalid input for embedding generation: {e}")
                raise ValueError(f"Invalid input for embedding generation: {e}")
            
            # General exception
            logger.error(f"Failed to generate embedding: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate embedding: {e}")
    
    # If we exit the loop, max retries were exceeded
    raise RuntimeError(
        f"Failed to generate embedding after {MAX_RETRIES} retries due to rate limiting"
    )


def generate_embeddings_batch(
    texts: List[str],
    task_type: str = "RETRIEVAL_DOCUMENT",
    model: str = DEFAULT_MODEL,
    dimensions: int = DEFAULT_DIMENSIONS
) -> List[List[float]]:
    """
    Generate embeddings for multiple texts.
    
    Note: Processes texts sequentially since the SDK doesn't support true batching.
    Each text is processed with full rate limiting handling.
    
    Args:
        texts: List of input strings to generate embeddings for
        task_type: Either "RETRIEVAL_DOCUMENT" or "RETRIEVAL_QUERY"
        model: Gemini model name (default: models/embedding-001)
        dimensions: Output dimensionality (default: 1536)
    
    Returns:
        List of embedding vectors (List[List[float]])
    
    Raises:
        ValueError: If texts list is empty or contains empty strings
        RuntimeError: If any embedding generation fails after retries
    
    Note:
        Processes texts sequentially with rate limiting handling. For large batches,
        this may take several minutes due to API rate limits.
    """
    # Input validation
    if not texts:
        raise ValueError("Texts list cannot be empty")
    
    if any(not text or not text.strip() for text in texts):
        raise ValueError("All texts must be non-empty")
    
    # Process each text
    embeddings = []
    for i, text in enumerate(texts):
        try:
            embedding = generate_embedding(text, task_type, model, dimensions)
            embeddings.append(embedding)
            
            # Add delay between requests to avoid rate limiting (except for last item)
            if i < len(texts) - 1:
                time.sleep(BATCH_DELAY)
                
        except Exception as e:
            logger.error(f"Failed to generate embedding for text {i + 1}/{len(texts)}: {e}")
            raise RuntimeError(
                f"Failed to generate embedding for text {i + 1}/{len(texts)}: {e}"
            )
    
    return embeddings


def get_embedding_dimensions(model: str = DEFAULT_MODEL) -> int:
    """
    Return the default embedding dimensions for a given model.
    
    Args:
        model: Gemini model name (default: models/embedding-001)
    
    Returns:
        Default embedding dimensions (1536)
    
    Note:
        Currently returns DEFAULT_DIMENSIONS (1536) for all models.
        Can be extended to support model-specific dimensions in the future.
    """
    return DEFAULT_DIMENSIONS


def format_chat_history(messages: Optional[List[dict]]) -> List[ChatHistoryEntry]:
    """Validate and normalize conversation history for Gemini chat sessions."""

    if not messages:
        return []

    formatted: List[ChatHistoryEntry] = []
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            raise ValueError(f"History entry {index} must be a dictionary")

        role = message.get("role")
        if role not in {"user", "model"}:
            raise ValueError(
                f"History entry {index} has invalid role '{role}'. Expected 'user' or 'model'."
            )

        parts = message.get("parts")
        if not isinstance(parts, list) or any(not isinstance(part, str) for part in parts):
            raise ValueError(
                f"History entry {index} must provide parts as a list of strings"
            )

        # Append each validated message preserving order
        formatted.append({"role": role, "parts": parts})

    return formatted


def stream_chat_response(
    prompt: str,
    context: str = "",
    history: Optional[List[dict]] = None,
    model: str = DEFAULT_CHAT_MODEL,
    temperature: float = CHAT_TEMPERATURE,
    max_output_tokens: int = MAX_OUTPUT_TOKENS
) -> Iterator[str]:
    """Stream chat response from Gemini using optional RAG context and conversation history.

    Args:
        prompt: User query or latest message to answer.
        context: Retrieved document snippets to ground the response.
        history: Prior turns formatted as dicts with role/parts (Gemini format).
        model: Gemini chat model to use.
        temperature: Controls response creativity (0.0-1.0).
        max_output_tokens: Upper bound on generated tokens.

    Yields:
        Incremental text chunks as Gemini streams the response.

    Raises:
        ValueError: If inputs are invalid.
        RuntimeError: If the Gemini API raises an error.
    """

    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty")

    validated_history = format_chat_history(history)

    _initialize_gemini_client()

    full_prompt = prompt.strip()
    if context and context.strip():
        full_prompt = (
            "Context from document:\n\n" + context.strip() + "\n\nUser question: " + prompt.strip()
        )

    generation_config = {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens or MAX_OUTPUT_TOKENS,
        "top_p": 0.95,
        "top_k": 40,
    }

    logger.info(
        "Starting Gemini chat stream",
        extra={
            "model": model,
            "history_length": len(validated_history),
            "prompt_chars": len(prompt),
            "context_chars": len(context),
        },
    )

    try:
        model_instance: GenerativeModel = genai.GenerativeModel(
            model_name=model,
            generation_config=generation_config,
        )
        chat_session = model_instance.start_chat(history=validated_history)
        response_stream = chat_session.send_message(full_prompt, stream=True)

        for chunk in response_stream:
            text = getattr(chunk, "text", None)
            if not text:
                continue
            yield text

        logger.info(
            "Completed Gemini chat stream",
            extra={
                "model": model,
                "history_length": len(validated_history),
            },
        )

    except Exception as exc:  # noqa: BLE001
        message = str(exc)
        lower_message = message.lower()

        if any(keyword in lower_message for keyword in ("429", "quota", "rate limit")):
            logger.warning("Gemini API rate limit while streaming: %s", message)
            raise RuntimeError("Gemini API rate limit exceeded") from exc

        if "api key" in lower_message or "authentication" in lower_message:
            logger.error("Gemini API authentication error: %s", message)
            raise RuntimeError("Invalid Gemini API key") from exc

        if any(keyword in lower_message for keyword in ("blocked", "safety")):
            logger.warning("Gemini blocked response due to safety filters: %s", message)
            raise RuntimeError("Response blocked by safety filters") from exc

        logger.error("Failed to stream chat response: %s", message, exc_info=True)
        raise RuntimeError(f"Failed to stream chat response: {message}") from exc


def generate_notes(
    text: str,
    model: str = DEFAULT_CHAT_MODEL,
    temperature: float = 0.3,
    max_output_tokens: int = 4096,
) -> str:
    """Generate structured markdown study notes from document text using Gemini.

    This uses non-streaming content generation to obtain the complete markdown
    before returning so that the caller can persist it to storage.

    Args:
        text: Full extracted document text to summarize into notes.
        model: Gemini model name (default: gemini-1.5-flash for speed).
        temperature: Lower temperature (default 0.3) for focused factual output.
        max_output_tokens: Upper bound on output length (default 4096 for longer notes).

    Returns:
        Markdown string containing structured study notes.

    Raises:
        ValueError: If input text is empty.
        RuntimeError: If Gemini API call fails (rate limit, auth, safety, general error).
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty for note generation")

    _initialize_gemini_client()

    # Prompt engineering: explicit markdown structure for consistency.
    prompt = (
        "Generate comprehensive study notes from the following document in markdown format. "
        "Structure the notes with clear sections using second-level headers (## Introduction, ## Key Points, ## Main Topics, ## Summary). "
        "Use bullet lists where appropriate, short paragraphs for explanations, and emphasize important terms with **bold**. "
        "Be concise but thorough. Do not include extraneous commentary or disclaimers. If the document seems incomplete, still produce best-effort notes.\n\n"
        "Document text:\n" + text.strip()
    )

    generation_config = {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens or MAX_OUTPUT_TOKENS,
        "top_p": 0.95,
        "top_k": 40,
    }

    logger.info(
        "Generating notes via Gemini",
        extra={
            "model": model,
            "text_chars": len(text),
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        },
    )

    try:
        model_instance: GenerativeModel = genai.GenerativeModel(
            model_name=model,
            generation_config=generation_config,
        )
        response = model_instance.generate_content(prompt)

        notes_markdown = getattr(response, "text", None)
        if not notes_markdown or not notes_markdown.strip():
            logger.error("Gemini returned empty notes content")
            raise RuntimeError("Empty notes generated")

        # Basic markdown validation (headers or lists)
        if not any(token in notes_markdown for token in ("## ", "- ", "* ")):
            logger.warning("Generated notes may lack expected markdown structure")

        logger.info(
            "Notes generation completed",
            extra={"chars": len(notes_markdown)},
        )
        return notes_markdown

    except Exception as exc:  # noqa: BLE001
        message = str(exc)
        lower_message = message.lower()

        if any(keyword in lower_message for keyword in ("429", "quota", "rate limit")):
            logger.warning("Gemini API rate limit during notes generation: %s", message)
            raise RuntimeError("Gemini API rate limit exceeded") from exc

        if "api key" in lower_message or "authentication" in lower_message:
            logger.error("Gemini API authentication error during notes generation: %s", message)
            raise RuntimeError("Invalid Gemini API key") from exc

        if any(keyword in lower_message for keyword in ("blocked", "safety")):
            logger.warning("Gemini blocked notes due to safety filters: %s", message)
            raise RuntimeError("Notes generation blocked by safety filters") from exc

        logger.error("Failed to generate notes: %s", message, exc_info=True)
        raise RuntimeError(f"Failed to generate notes: {message}") from exc


def generate_mindmap(
    text: str,
    model: str = DEFAULT_CHAT_MODEL,
    temperature: float = 0.5,
    max_output_tokens: int = 8192,
) -> str:
    """Generate SVG mindmap visualization from document text using Gemini.

    Uses non-streaming generation to obtain complete SVG markup before returning.

    Args:
        text: Full extracted document text to visualize as a mindmap.
        model: Gemini model name (default: gemini-1.5-flash for speed).
        temperature: Moderately higher temperature (default 0.5) for layout creativity.
        max_output_tokens: Upper bound on output length (default 8192 for complex SVG).

    Returns:
        Raw SVG string (UNSANITIZED). The caller must sanitize with bleach before storage/display.

    Raises:
        ValueError: If input text is empty.
        RuntimeError: If Gemini API call fails (rate limit, auth, safety, general error).
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty for mindmap generation")

    _initialize_gemini_client()

    # Prompt engineering: explicit SVG structure and safety constraints.
    prompt = (
        "Analyze the following document and create a beautiful, well-spaced hierarchical mindmap visualization in SVG format. "
        "The mindmap should show the main topic at the center with subtopics radiating outward in a balanced, non-overlapping layout. "
        "Use ONLY SVG markup; do not include markdown code fences or explanations. "
        "\n"
        "CRITICAL LAYOUT RULES:\n"
        "- Canvas: width='1600' height='1000' viewBox='0 0 1600 1000'\n"
        "- Background: <rect width='1600' height='1000' fill='#ffffff'/> as first element\n"
        "- Central node: Position at (800, 500) - make it larger and distinct (200px wide, 60px tall)\n"
        "- First level nodes: Place 300-400px away from center in radial pattern (6-8 directions)\n"
        "- Second level nodes: Place 200-250px away from their parent nodes\n"
        "- Minimum spacing: 180px between any two nodes to prevent overlap\n"
        "- Use curved paths for connections: <path d='M x1,y1 Q cx,cy x2,y2' /> for smooth curves\n"
        "\n"
        "STYLING:\n"
        "- Central node: fill='#FF6B6B' (coral red) with larger text (font-size='18' font-weight='bold')\n"
        "- Level 1 nodes: Use vibrant colors (#4CAF50 green, #2196F3 blue, #FF9800 orange, #9C27B0 purple, #00BCD4 cyan)\n"
        "- Level 2 nodes: Use lighter versions of parent colors (add opacity='0.8')\n"
        "- Node shape: <rect rx='8' ry='8' with min width='140' height='50' and padding\n"
        "- Text: font-family='Arial,sans-serif' font-size='14' fill='#212121' text-anchor='middle' dominant-baseline='middle'\n"
        "- Connections: stroke='#9E9E9E' stroke-width='2' fill='none' opacity='0.6'\n"
        "\n"
        "EXAMPLE STRUCTURE:\n"
        "<svg width='1600' height='1000' viewBox='0 0 1600 1000' xmlns='http://www.w3.org/2000/svg'>\n"
        "  <rect width='1600' height='1000' fill='#ffffff'/>\n"
        "  <!-- Connections drawn first -->\n"
        "  <path d='M 800,500 Q 750,350 600,300' stroke='#9E9E9E' stroke-width='2' fill='none'/>\n"
        "  <!-- Central node -->\n"
        "  <rect x='700' y='470' width='200' height='60' rx='8' fill='#FF6B6B'/>\n"
        "  <text x='800' y='500' font-size='18' font-weight='bold' fill='#212121' text-anchor='middle' dominant-baseline='middle'>Main Topic</text>\n"
        "  <!-- Level 1 node -->\n"
        "  <rect x='530' y='275' width='140' height='50' rx='8' fill='#4CAF50'/>\n"
        "  <text x='600' y='300' font-size='14' fill='#212121' text-anchor='middle' dominant-baseline='middle'>Subtopic</text>\n"
        "</svg>\n"
        "\n"
        "Document text:\n" + text.strip()
    )

    generation_config = {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens or MAX_OUTPUT_TOKENS,
        "top_p": 0.95,
        "top_k": 40,
    }

    logger.info(
        "Generating mindmap via Gemini",
        extra={
            "model": model,
            "text_chars": len(text),
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        },
    )

    try:
        model_instance: GenerativeModel = genai.GenerativeModel(
            model_name=model,
            generation_config=generation_config,
        )
        response = model_instance.generate_content(prompt)

        svg = getattr(response, "text", None)
        if not svg or not svg.strip():
            logger.error("Gemini returned empty mindmap content")
            raise RuntimeError("Empty mindmap generated")

        # Basic SVG validation
        lower_svg = svg.lower()
        if "<svg" not in lower_svg or "</svg>" not in lower_svg:
            logger.warning("Generated mindmap may not be valid SVG structure")

        logger.info(
            "Mindmap generation completed",
            extra={"chars": len(svg)},
        )
        return svg

    except Exception as exc:  # noqa: BLE001
        message = str(exc)
        lower_message = message.lower()

        if any(keyword in lower_message for keyword in ("429", "quota", "rate limit")):
            logger.warning("Gemini API rate limit during mindmap generation: %s", message)
            raise RuntimeError("Gemini API rate limit exceeded") from exc

        if "api key" in lower_message or "authentication" in lower_message:
            logger.error("Gemini API authentication error during mindmap generation: %s", message)
            raise RuntimeError("Invalid Gemini API key") from exc

        if any(keyword in lower_message for keyword in ("blocked", "safety")):
            logger.warning("Gemini blocked mindmap due to safety filters: %s", message)
            raise RuntimeError("Mindmap generation blocked by safety filters") from exc

        logger.error("Failed to generate mindmap: %s", message, exc_info=True)
        raise RuntimeError(f"Failed to generate mindmap: {message}") from exc


def generate_flashcards(
    text: str,
    model: str = DEFAULT_CHAT_MODEL,
    temperature: float = 0.4,
    max_output_tokens: int = 4096,
    target_count: int = 10,
) -> str:
    """Generate Q&A flashcard pairs from document text using Gemini.

    Uses non-streaming generation to obtain complete JSON response with flashcards.

    Args:
        text: Full extracted document text to generate flashcards from.
        model: Gemini model name (default: gemini-1.5-flash for speed).
        temperature: Balanced temperature (default 0.4) for factual accuracy with diversity.
        max_output_tokens: Upper bound on output length (default 4096).
        target_count: Target number of flashcards to generate (default 10, range 1-50).

    Returns:
        JSON string with structure: {"flashcards": [{"question": "...", "answer": "..."}, ...]}.
        The caller must parse and validate the JSON before database insertion.

    Raises:
        ValueError: If input text is empty or target_count is invalid.
        RuntimeError: If Gemini API call fails (rate limit, auth, safety, general error).
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty for flashcard generation")
    if not isinstance(target_count, int) or target_count < 1 or target_count > 50:
        raise ValueError("target_count must be a positive integer between 1 and 50")

    _initialize_gemini_client()

    # Prompt engineering: explicit JSON structure for structured parsing.
    prompt = (
        f"Generate {target_count} flashcard Q&A pairs from the following document in JSON format. "
        "Create diverse questions covering key concepts, facts, definitions, and relationships. "
        "Questions should be concise and specific. Answers should be comprehensive but not overly long. "
        f'Output ONLY valid JSON with structure: {{"flashcards": [{{"question": "...", "answer": "..."}}]}}. '
        "Do not include markdown code blocks, explanations, or any text outside the JSON structure.\n\n"
        "Document text:\n" + text.strip()
    )

    generation_config = {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens or MAX_OUTPUT_TOKENS,
        "top_p": 0.95,
        "top_k": 40,
    }

    logger.info(
        "Generating flashcards via Gemini",
        extra={
            "model": model,
            "text_chars": len(text),
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
            "target_count": target_count,
        },
    )

    try:
        model_instance: GenerativeModel = genai.GenerativeModel(
            model_name=model,
            generation_config=generation_config,
        )
        response = model_instance.generate_content(prompt)

        flashcards_json = getattr(response, "text", None)
        if not flashcards_json or not flashcards_json.strip():
            logger.error("Gemini returned empty flashcards content")
            raise RuntimeError("Empty flashcards generated")

        # Basic JSON validation (check if it looks like JSON)
        stripped_json = flashcards_json.strip()
        if not (stripped_json.startswith("{") and stripped_json.endswith("}")):
            logger.warning("Generated flashcards may not be valid JSON structure")

        logger.info(
            "Flashcard generation completed",
            extra={"json_chars": len(flashcards_json)},
        )
        return flashcards_json

    except Exception as exc:  # noqa: BLE001
        message = str(exc)
        lower_message = message.lower()

        if any(keyword in lower_message for keyword in ("429", "quota", "rate limit")):
            logger.warning("Gemini API rate limit during flashcard generation: %s", message)
            raise RuntimeError("Gemini API rate limit exceeded") from exc

        if "api key" in lower_message or "authentication" in lower_message:
            logger.error("Gemini API authentication error during flashcard generation: %s", message)
            raise RuntimeError("Invalid Gemini API key") from exc

        if any(keyword in lower_message for keyword in ("blocked", "safety")):
            logger.warning("Gemini blocked flashcards due to safety filters: %s", message)
            raise RuntimeError("Flashcard generation blocked by safety filters") from exc

        logger.error("Failed to generate flashcards: %s", message, exc_info=True)
        raise RuntimeError(f"Failed to generate flashcards: {message}") from exc


def synthesize_documents(
    documents_text: List[dict],
    synthesis_type: str = "summary",
    model: str = DEFAULT_CHAT_MODEL,
    temperature: float = 0.5,
    max_output_tokens: int = 8192
) -> str:
    """Generate multi-document synthesis using Gemini AI.
    
    Creates either a unified summary (combining insights) or comparative analysis
    (highlighting differences) from multiple documents with source attribution.
    
    Args:
        documents_text: List of dicts with structure {"filename": str, "text": str}
        synthesis_type: Either "summary" or "comparison"
        model: Gemini model name (default: gemini-1.5-flash)
        temperature: Controls randomness (0.5 for balanced creativity/accuracy)
        max_output_tokens: Maximum output length (8192 for comprehensive synthesis)
        
    Returns:
        Complete markdown synthesis with Introduction, Analysis, Conclusion, Sources sections
        
    Raises:
        ValueError: If documents_text is invalid or synthesis_type is invalid
        RuntimeError: If Gemini API fails (rate limit, safety filters, etc.)
    """
    # Input validation
    if not documents_text or len(documents_text) < 2:
        raise ValueError("At least 2 documents are required for synthesis")
    
    if synthesis_type not in ["summary", "comparison"]:
        raise ValueError("synthesis_type must be 'summary' or 'comparison'")
    
    for doc in documents_text:
        if "filename" not in doc or "text" not in doc:
            raise ValueError("Each document must have 'filename' and 'text' fields")
        if not doc["text"].strip():
            raise ValueError(f"Document {doc['filename']} has empty text")
    
    # Ensure client is initialized
    _initialize_gemini_client()
    
    # Calculate total text length
    total_length = sum(len(doc["text"]) for doc in documents_text)
    document_count = len(documents_text)
    
    # Context window management (Comment 5)
    # gemini-2.5-pro offers extended context (up to ~2M tokens). We conservatively budget input.
    # Approximate chars per token ~4; reserve 40% for output + safety.
    MAX_INPUT_CHARS = 3_200_000  # ~800K tokens reserved for input portion
    
    if total_length > MAX_INPUT_CHARS:
        # Calculate proportional truncation
        truncation_ratio = MAX_INPUT_CHARS / total_length
        logger.warning(
            "Total text length %d exceeds budget %d. Proportional truncation ratio: %.2f",
            total_length,
            MAX_INPUT_CHARS,
            truncation_ratio
        )
        
        # Truncate each document proportionally
        truncated_docs = []
        for doc in documents_text:
            original_len = len(doc["text"])
            target_len = int(original_len * truncation_ratio)
            truncated_text = doc["text"][:target_len]
            truncated_docs.append({
                "filename": doc["filename"],
                "text": truncated_text
            })
            logger.info(
                "Truncated %s: %d → %d chars",
                doc["filename"],
                original_len,
                target_len
            )
        
        documents_text = truncated_docs
        total_length = sum(len(doc["text"]) for doc in documents_text)
    
    logger.info(
        "Starting synthesis: type=%s, documents=%d, total_chars=%d, model=%s",
        synthesis_type,
        document_count,
        total_length,
        model
    )
    
    # Format documents with clear separators
    formatted_documents = []
    for i, doc in enumerate(documents_text, 1):
        formatted_documents.append(
            f"Document {i}: {doc['filename']}\n{doc['text']}\n"
        )
    documents_block = "\n---\n\n".join(formatted_documents)
    
    # Build synthesis prompt based on type
    if synthesis_type == "summary":
        prompt = f"""Analyze the following {document_count} documents and create a unified summary that combines insights and identifies common themes across all documents.

Structure the output in markdown with the following sections:
## Introduction
Brief overview of the documents and their common context.

## Key Findings
Main insights and themes that appear across the documents. Use bullet points.

## Synthesis
Detailed analysis combining insights from all documents. Identify patterns, commonalities, and synthesize key points into a cohesive narrative.

## Conclusion
Summary of the most important takeaways from the combined analysis.

## Sources
List each document with 3-5 key points extracted from it. Format:
**Document 1: filename**
- Key point 1
- Key point 2
- Key point 3

Documents:
{documents_block}
"""
    else:  # comparison
        prompt = f"""Analyze the following {document_count} documents and create a comparative analysis that highlights similarities, differences, and unique insights per document.

Structure the output in markdown with the following sections:
## Introduction
Brief overview of the documents being compared.

## Similarities
Common themes, agreements, and shared insights across documents. Use bullet points.

## Differences
Contrasting viewpoints, unique insights per document, and disagreements. Use structured comparison.

## Comparative Analysis
Detailed analysis highlighting what each document contributes uniquely and where documents align or diverge.

## Conclusion
Summary of the key similarities and differences, and what can be learned from comparing these documents.

## Sources
List each document with 3-5 key points extracted from it. Format:
**Document 1: filename**
- Key point 1
- Key point 2
- Key point 3

Documents:
{documents_block}
"""
    
    # Create model instance with generation config
    generation_config = {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens or MAX_OUTPUT_TOKENS,
        "top_p": 0.95,
        "top_k": 40,
    }
    
    try:
        model_instance = genai.GenerativeModel(
            model_name=model,
            generation_config=generation_config,
        )
        
        # Generate synthesis (non-streaming)
        response = model_instance.generate_content(prompt)
        
        # Extract and validate markdown
        if not response.text:
            raise RuntimeError("Gemini returned empty synthesis")
        
        markdown = response.text.strip()
        
        # Validate markdown structure (should have headers)
        if "##" not in markdown:
            logger.warning("Synthesis lacks markdown structure (no headers found)")
        
        logger.info(
            "Synthesis completed: type=%s, output_chars=%d",
            synthesis_type,
            len(markdown)
        )
        
        return markdown
        
    except Exception as exc:
        message = str(exc)
        lower_message = message.lower()
        
        # Check for rate limiting
        if "429" in message or "quota" in lower_message or "rate limit" in lower_message:
            logger.warning("Gemini API rate limit exceeded: %s", message)
            raise RuntimeError("Gemini API rate limit exceeded. Please try again later.") from exc
        
        # Check for invalid API key
        if "api key" in lower_message or "authentication" in lower_message:
            logger.error("Gemini API authentication failed: %s", message)
            raise RuntimeError("Gemini API authentication failed") from exc
        
        # Check for safety filters
        if any(keyword in lower_message for keyword in ("blocked", "safety")):
            logger.warning("Gemini blocked synthesis due to safety filters: %s", message)
            raise RuntimeError("Synthesis blocked by safety filters") from exc
        
        logger.error("Failed to generate synthesis: %s", message, exc_info=True)
        raise RuntimeError(f"Failed to generate synthesis: {message}") from exc

