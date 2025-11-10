"""
Text chunking utilities for Neura.

This module provides text chunking functionality for splitting long documents into 
smaller chunks suitable for embedding generation. Uses tiktoken for accurate token 
counting and implements a sliding window algorithm with configurable overlap to 
ensure semantic continuity across chunks.
"""

import logging
import math
from functools import lru_cache
from typing import List

import tiktoken

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CHUNK_SIZE = 1000  # Target tokens per chunk
DEFAULT_OVERLAP = 200  # Overlap tokens between consecutive chunks
DEFAULT_ENCODING = "cl100k_base"  # tiktoken encoding (GPT-3.5/4, reasonable approximation for Gemini)


@lru_cache(maxsize=None)
def get_encoder(encoding_name: str):
    """
    Get a tiktoken encoder with caching to avoid repeated lookups.
    
    Args:
        encoding_name: Name of the tiktoken encoding (e.g., "cl100k_base")
        
    Returns:
        tiktoken.Encoding instance
        
    Note:
        This function uses LRU cache to memoize encoders for better performance.
    """
    try:
        return tiktoken.get_encoding(encoding_name)
    except Exception as e:
        logger.error(f"Failed to load encoding '{encoding_name}': {e}, falling back to cl100k_base")
        return tiktoken.get_encoding("cl100k_base")


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    encoding_name: str = DEFAULT_ENCODING
) -> List[str]:
    """
    Split text into overlapping chunks of approximately chunk_size tokens.
    
    Args:
        text: Input text to chunk
        chunk_size: Target tokens per chunk (must be positive)
        overlap: Tokens to overlap between consecutive chunks (must be non-negative)
        encoding_name: tiktoken encoding to use for token counting
        
    Returns:
        List of text chunks as strings
        
    Raises:
        ValueError: If chunk_size <= overlap or chunk_size < 1 or overlap < 0
        
    Note:
        Actual chunk sizes may vary slightly due to token boundary alignment.
        The function uses tiktoken's cl100k_base encoding by default, which provides
        a reasonable approximation for Gemini token counting (~80-90% accuracy).
    """
    # Input validation - empty or whitespace-only text
    if not text or not text.strip():
        return []
    
    # Input validation - chunk size and overlap constraints
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    
    if overlap < 0:
        raise ValueError("overlap must be non-negative")
    
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")
    
    try:
        # Initialize tiktoken encoder (cached)
        encoder = get_encoder(encoding_name)
        
        # Encode text to tokens
        tokens = encoder.encode(text)
        
        # Handle short text - return as single chunk
        if len(tokens) <= chunk_size:
            return [text]
        
        # Sliding window chunking
        chunks = []
        start_idx = 0
        
        while start_idx < len(tokens):
            # Calculate end index, ensuring we don't exceed token list
            end_idx = min(start_idx + chunk_size, len(tokens))
            
            # Extract chunk tokens
            chunk_tokens = tokens[start_idx:end_idx]
            
            # Decode chunk tokens back to text
            try:
                chunk_text = encoder.decode(chunk_tokens)
                chunks.append(chunk_text)
            except Exception as e:
                logger.warning(f"Failed to decode chunk at position {start_idx}: {e}, skipping")
            
            # Move window forward
            start_idx += (chunk_size - overlap)
            
            # Prevent infinite loop
            if start_idx >= len(tokens):
                break
        
        return chunks
        
    except Exception as e:
        logger.error(f"Failed to chunk text with tiktoken: {e}, falling back to character-based chunking")
        
        # Fallback: simple character-based chunking
        # Approximate: 1 token ≈ 4 characters
        char_chunk_size = chunk_size * 4
        char_overlap = overlap * 4
        
        chunks = []
        start_idx = 0
        
        while start_idx < len(text):
            end_idx = min(start_idx + char_chunk_size, len(text))
            chunk = text[start_idx:end_idx]
            chunks.append(chunk)
            start_idx += (char_chunk_size - char_overlap)
            
            if start_idx >= len(text):
                break
        
        return chunks


def get_chunk_count(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    encoding_name: str = DEFAULT_ENCODING
) -> int:
    """
    Calculate how many chunks will be generated without actually chunking.
    Useful for progress tracking in embedding generation.
    
    Args:
        text: Input text to analyze
        chunk_size: Target tokens per chunk
        overlap: Tokens to overlap between consecutive chunks
        encoding_name: tiktoken encoding to use for token counting
        
    Returns:
        Number of chunks that will be generated
        
    Raises:
        ValueError: If chunk_size <= overlap or chunk_size < 1 or overlap < 0
    """
    # Input validation
    if not text or not text.strip():
        return 0
    
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    
    if overlap < 0:
        raise ValueError("overlap must be non-negative")
    
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")
    
    try:
        # Get cached encoder
        encoder = get_encoder(encoding_name)
        
        # Encode text to tokens
        tokens = encoder.encode(text)
        total_tokens = len(tokens)
        
        # Handle short text
        if total_tokens <= chunk_size:
            return 1
        
        # Calculate chunk count
        # Formula: ceil((total_tokens - overlap) / (chunk_size - overlap))
        chunk_count = math.ceil((total_tokens - overlap) / (chunk_size - overlap))
        return max(1, chunk_count)
        
    except Exception as e:
        logger.error(f"Failed to count chunks: {e}")
        # Fallback approximation accounting for overlap
        # Approximate: 1 token ≈ 4 characters
        char_chunk_size = chunk_size * 4
        char_overlap = overlap * 4
        return max(1, math.ceil((len(text) - char_overlap) / (char_chunk_size - char_overlap)))


def count_tokens(
    text: str,
    encoding_name: str = DEFAULT_ENCODING
) -> int:
    """
    Count the number of tokens in a text string.
    
    Args:
        text: Input text to count tokens for
        encoding_name: tiktoken encoding to use for token counting
        
    Returns:
        Number of tokens in the text
        
    Note:
        Returns 0 for empty or whitespace-only strings.
        Uses LRU-cached encoder for better performance.
    """
    if not text or not text.strip():
        return 0
    
    try:
        encoder = get_encoder(encoding_name)
        tokens = encoder.encode(text)
        return len(tokens)
    except Exception as e:
        logger.error(f"Failed to count tokens: {e}, falling back to character approximation")
        # Fallback: 1 token ≈ 4 characters
        return len(text) // 4
