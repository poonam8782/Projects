"""
Unit tests for the Gemini embedding client (app.services.gemini_client).

Tests cover normal operation, error handling, rate limiting, and batch processing.
Tests use mocking to avoid real API calls and associated costs.
"""

import pytest
from unittest.mock import patch, MagicMock

from app.services.gemini_client import (
    generate_embedding,
    generate_embeddings_batch,
    get_embedding_dimensions,
    DEFAULT_DIMENSIONS,
    MAX_RETRIES,
    format_chat_history,
)


# Test fixtures

@pytest.fixture(autouse=True)
def mock_initialization():
    """Patch initialization to avoid requiring GEMINI_API_KEY in tests."""
    with patch('app.services.gemini_client._initialize_gemini_client', return_value=None):
        yield


@pytest.fixture
def mock_genai():
    """Mock the entire genai module to prevent real API calls."""
    with patch('app.services.gemini_client.genai') as mock:
        yield mock


@pytest.fixture
def sample_embedding():
    """Return a simulated embedding vector of 768 dimensions."""
    return [0.1] * 768


@pytest.fixture
def sample_text():
    """Return a medium-length text string for testing."""
    return """
    This is a sample text for testing the Gemini embedding client.
    It contains multiple sentences and should be long enough to represent
    a typical document chunk. The text discusses various topics including
    artificial intelligence, machine learning, and natural language processing.
    These are all important concepts in modern software development and data science.
    """


# Test cases for generate_embedding

class TestGenerateEmbedding:
    """Tests for the generate_embedding function."""
    
    def test_generate_embedding_success(self, mock_genai, sample_embedding, sample_text):
        """Test basic embedding generation works."""
        # Setup mock
        mock_genai.embed_content.return_value = {'embedding': sample_embedding}
        
        # Action
        result = generate_embedding(sample_text)
        
        # Assertions
        assert isinstance(result, list)
        assert len(result) == 768
        assert all(isinstance(x, float) for x in result)
        
        # Verify API call
        mock_genai.embed_content.assert_called_once()
        call_kwargs = mock_genai.embed_content.call_args[1]
        assert call_kwargs['model'] == 'models/embedding-001'
        assert call_kwargs['content'] == sample_text
        assert call_kwargs['task_type'] == 'RETRIEVAL_DOCUMENT'
        assert call_kwargs['output_dimensionality'] == 768
    
    def test_generate_embedding_with_query_task_type(self, mock_genai, sample_embedding, sample_text):
        """Test that task_type parameter works correctly."""
        # Setup mock
        mock_genai.embed_content.return_value = {'embedding': sample_embedding}
        
        # Action
        result = generate_embedding(sample_text, task_type="RETRIEVAL_QUERY")
        
        # Assertions
        assert isinstance(result, list)
        assert len(result) == 1536
        
        # Verify task_type was passed correctly
        call_kwargs = mock_genai.embed_content.call_args[1]
        assert call_kwargs['task_type'] == 'RETRIEVAL_QUERY'
    
    def test_generate_embedding_custom_dimensions(self, mock_genai, sample_text):
        """Test that custom dimensions parameter works."""
        # Setup mock with 768-dimensional embedding
        custom_embedding = [0.1] * 768
        mock_genai.embed_content.return_value = {'embedding': custom_embedding}
        
        # Action
        result = generate_embedding(sample_text, dimensions=768)
        
        # Assertions
        assert len(result) == 768
        
        # Verify dimensions parameter was passed
        call_kwargs = mock_genai.embed_content.call_args[1]
        assert call_kwargs['output_dimensionality'] == 768
    
    def test_generate_embedding_handles_values_shape(self, mock_genai, sample_text):
        """Test that the nested values shape is handled correctly."""
        # Setup mock with nested values shape
        mock_genai.embed_content.return_value = {'embedding': {'values': [0.1] * 1536}}
        
        # Action
        result = generate_embedding(sample_text)
        
        # Assertions
        assert isinstance(result, list)
        assert len(result) == 1536
        
        # Verify API call arguments
        mock_genai.embed_content.assert_called_once()
        call_kwargs = mock_genai.embed_content.call_args[1]
        assert call_kwargs['model'] == 'models/embedding-001'
        assert call_kwargs['content'] == sample_text
        assert call_kwargs['task_type'] == 'RETRIEVAL_DOCUMENT'
        assert call_kwargs['output_dimensionality'] == 1536


class TestGenerateEmbeddingErrors:
    """Tests for error handling in generate_embedding."""
    
    def test_generate_embedding_empty_text(self, mock_genai):
        """Test error handling for empty text."""
        with pytest.raises(ValueError) as exc_info:
            generate_embedding("")
        
        assert "empty" in str(exc_info.value).lower()
    
    def test_generate_embedding_whitespace_only(self, mock_genai):
        """Test error handling for whitespace-only text."""
        with pytest.raises(ValueError) as exc_info:
            generate_embedding("   \n\t  ")
        
        assert "empty" in str(exc_info.value).lower()
    
    def test_generate_embedding_invalid_task_type(self, mock_genai, sample_text):
        """Test error handling for invalid task_type."""
        with pytest.raises(ValueError) as exc_info:
            generate_embedding(sample_text, task_type="INVALID_TYPE")
        
        assert "task_type" in str(exc_info.value).lower()
    
    def test_generate_embedding_invalid_api_key(self, mock_genai, sample_text):
        """Test error handling for invalid API key."""
        # Setup mock to raise API key error
        mock_genai.embed_content.side_effect = Exception("Invalid API key")
        
        # Action & Assertion
        with pytest.raises(RuntimeError) as exc_info:
            generate_embedding(sample_text)
        
        assert "api key" in str(exc_info.value).lower()
        
        # Verify no retries occurred
        assert mock_genai.embed_content.call_count == 1
    
    def test_generate_embedding_network_error(self, mock_genai, sample_text):
        """Test error handling for network errors."""
        # Setup mock to raise generic exception
        mock_genai.embed_content.side_effect = Exception("Network connection failed")
        
        # Action & Assertion
        with pytest.raises(RuntimeError) as exc_info:
            generate_embedding(sample_text)
        
        assert "failed to generate embedding" in str(exc_info.value).lower()


class TestRateLimiting:
    """Tests for rate limiting and retry logic."""
    
    @patch('app.services.gemini_client.time.sleep')  # Mock sleep to speed up tests
    def test_generate_embedding_rate_limiting_retry(
        self, mock_sleep, mock_genai, sample_embedding, sample_text
    ):
        """Test retry logic for rate limiting."""
        # Setup mock to fail twice with 429, then succeed
        mock_genai.embed_content.side_effect = [
            Exception("429 Rate limit exceeded"),
            Exception("429 Rate limit exceeded"),
            {'embedding': sample_embedding}
        ]
        
        # Action
        result = generate_embedding(sample_text)
        
        # Assertions
        assert isinstance(result, list)
        assert len(result) == 1536
        assert mock_genai.embed_content.call_count == 3
        
        # Verify retry delays occurred
        assert mock_sleep.call_count == 2
        # First retry: 1s delay, second retry: 2s delay
        mock_sleep.assert_any_call(1.0)
        mock_sleep.assert_any_call(2.0)
    
    @patch('app.services.gemini_client.time.sleep')
    def test_generate_embedding_rate_limiting_max_retries(
        self, mock_sleep, mock_genai, sample_text
    ):
        """Test failure after max retries exceeded."""
        # Setup mock to always return 429 error
        mock_genai.embed_content.side_effect = Exception("429 Rate limit exceeded")
        
        # Action & Assertion
        with pytest.raises(RuntimeError) as exc_info:
            generate_embedding(sample_text)
        
        error_message = str(exc_info.value).lower()
        assert "retries" in error_message or "rate limit" in error_message
        
        # Verify MAX_RETRIES + 1 attempts were made
        assert mock_genai.embed_content.call_count == MAX_RETRIES + 1


class TestGenerateEmbeddingsBatch:
    """Tests for the generate_embeddings_batch function."""
    
    def test_generate_embeddings_batch_success(self, mock_genai, sample_embedding):
        """Test batch embedding generation works."""
        # Setup mock to return different embeddings for each call
        mock_genai.embed_content.return_value = {'embedding': sample_embedding}
        
        # Action
        texts = ["text1", "text2", "text3"]
        result = generate_embeddings_batch(texts)
        
        # Assertions
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(emb, list) for emb in result)
        assert all(len(emb) == 1536 for emb in result)
        
        # Verify API was called 3 times
        assert mock_genai.embed_content.call_count == 3
    
    def test_generate_embeddings_batch_empty_list(self, mock_genai):
        """Test error handling for empty texts list."""
        with pytest.raises(ValueError) as exc_info:
            generate_embeddings_batch([])
        
        assert "empty" in str(exc_info.value).lower()
    
    def test_generate_embeddings_batch_with_empty_text(self, mock_genai):
        """Test error handling when batch contains empty text."""
        with pytest.raises(ValueError) as exc_info:
            generate_embeddings_batch(["text1", "", "text3"])
        
        assert "empty" in str(exc_info.value).lower()
    
    def test_generate_embeddings_batch_partial_failure(self, mock_genai, sample_embedding):
        """Test behavior when one text in batch fails."""
        # Setup mock to succeed for first text, fail for second
        mock_genai.embed_content.side_effect = [
            {'embedding': sample_embedding},
            Exception("API error")
        ]
        
        # Action & Assertion
        with pytest.raises(RuntimeError):
            generate_embeddings_batch(["text1", "text2"])
        
        # Verify only 2 API calls were made (first succeeds, second fails)
        assert mock_genai.embed_content.call_count == 2


class TestUtilityFunctions:
    """Tests for utility functions."""
    
    def test_get_embedding_dimensions(self):
        """Test that get_embedding_dimensions returns correct dimensions."""
        result = get_embedding_dimensions()
        assert result == 1536

    def test_format_chat_history_preserves_order(self):
        """format_chat_history should return both messages in original order."""
        messages = [
            {"role": "user", "parts": ["Hello"]},
            {"role": "model", "parts": ["Hi there!"]},
        ]
        formatted = format_chat_history(messages)
        assert isinstance(formatted, list)
        assert len(formatted) == 2
        assert formatted[0]["role"] == "user"
        assert formatted[0]["parts"] == ["Hello"]
        assert formatted[1]["role"] == "model"
        assert formatted[1]["parts"] == ["Hi there!"]


# Parametrized tests

@pytest.mark.parametrize("task_type", ["RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"])
def test_task_types_parametrized(mock_genai, sample_embedding, sample_text, task_type):
    """Test both task types work correctly."""
    # Setup mock
    mock_genai.embed_content.return_value = {'embedding': sample_embedding}
    
    # Action
    result = generate_embedding(sample_text, task_type=task_type)
    
    # Assertions
    assert isinstance(result, list)
    assert len(result) == 1536
    
    # Verify correct task_type was passed
    call_kwargs = mock_genai.embed_content.call_args[1]
    assert call_kwargs['task_type'] == task_type


@pytest.mark.parametrize("dimensions", [768, 1536, 3072])
def test_dimensions_parametrized(mock_genai, sample_text, dimensions):
    """Test various dimension sizes."""
    # Setup mock to return embeddings of appropriate size
    custom_embedding = [0.1] * dimensions
    mock_genai.embed_content.return_value = {'embedding': custom_embedding}
    
    # Action
    result = generate_embedding(sample_text, dimensions=dimensions)
    
    # Assertions
    assert len(result) == dimensions
    
    # Verify correct dimensions were passed
    call_kwargs = mock_genai.embed_content.call_args[1]
    assert call_kwargs['output_dimensionality'] == dimensions
