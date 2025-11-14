"""
Unit tests for the /embed endpoint (app.routes.embed).

Tests cover authentication, document ownership, text chunking, embedding generation,
database operations, and error handling. Tests use mocking to avoid real API calls
and database operations.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import create_app
from app.core.auth import require_user


# Test fixtures

@pytest.fixture
def client():
    """Return TestClient for making HTTP requests."""
    app = create_app()
    # Override require_user dependency to bypass authentication in most tests
    app.dependency_overrides[require_user] = lambda: {"sub": "test-user-id", "role": "authenticated"}
    return TestClient(app)


@pytest.fixture
def mock_supabase():
    """Mock get_supabase_client to avoid real database calls."""
    with patch('app.routes.embed.get_supabase_client') as mock:
        yield mock


@pytest.fixture
def mock_chunker():
    """Mock chunk_text to return predictable chunks."""
    with patch('app.routes.embed.chunk_text') as mock:
        yield mock


@pytest.fixture
def mock_gemini():
    """Mock generate_embeddings_batch to return fake embeddings."""
    with patch('app.routes.embed.generate_embeddings_batch') as mock:
        yield mock


@pytest.fixture
def sample_document():
    """Return a dict representing a document with extracted_text."""
    return {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "extracted_text": "This is a sample document text that will be chunked and embedded. " * 100,
        "status": "extracted"
    }


@pytest.fixture
def sample_chunks():
    """Return a list of 3 text chunks."""
    return [
        "This is chunk 1 with some text content.",
        "This is chunk 2 with different text content.",
        "This is chunk 3 with more text content."
    ]


@pytest.fixture
def sample_embeddings():
    """Return a list of 3 embedding vectors (768 dimensions each)."""
    return [
        [0.1] * 768,
        [0.2] * 768,
        [0.3] * 768
    ]


# Test cases

class TestEmbedEndpoint:
    """Tests for the /embed endpoint core functionality."""
    
    def test_embed_success(
        self, client, mock_supabase, mock_chunker, mock_gemini, 
        sample_document, sample_chunks, sample_embeddings
    ):
        """Test successful embedding generation flow."""
        # Setup mocks
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        
        # Mock document fetch
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[sample_document]
        )
        
        # Mock delete existing embeddings
        mock_supabase_instance.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        
        # Mock insert embeddings
        mock_supabase_instance.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "emb1"}, {"id": "emb2"}, {"id": "emb3"}]
        )
        
        # Mock update document status
        mock_supabase_instance.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"status": "embedded"}]
        )
        
        mock_chunker.return_value = sample_chunks
        mock_gemini.return_value = sample_embeddings
        
        # Action
        response = client.post(f"/embed?document_id={sample_document['id']}")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == sample_document["id"]
        assert data["chunk_count"] == 3
        assert data["embedding_count"] == 3
        assert data["status"] == "embedded"
        assert data["message"] == "Embeddings generated successfully"
        assert "processing_time_seconds" in data
        assert data["processing_time_seconds"] >= 0
    
    def test_embed_processing_time_tracked(
        self, client, mock_supabase, mock_chunker, mock_gemini,
        sample_document, sample_chunks, sample_embeddings
    ):
        """Test that processing time is measured and returned."""
        # Setup mocks
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[sample_document]
        )
        mock_supabase_instance.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase_instance.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
        mock_supabase_instance.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
        
        mock_chunker.return_value = sample_chunks
        mock_gemini.return_value = sample_embeddings
        
        # Action
        response = client.post(f"/embed?document_id={sample_document['id']}")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "processing_time_seconds" in data
        assert isinstance(data["processing_time_seconds"], (int, float))
        assert data["processing_time_seconds"] >= 0
    
    def test_embed_batch_insert_called(
        self, client, mock_supabase, mock_chunker, mock_gemini,
        sample_document, sample_chunks, sample_embeddings
    ):
        """Test that embeddings are inserted in batch (not loop)."""
        # Setup mocks
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        
        mock_insert = MagicMock()
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[sample_document]
        )
        mock_supabase_instance.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase_instance.table.return_value.insert = mock_insert
        mock_insert.return_value.execute.return_value = MagicMock(data=[{}])
        mock_supabase_instance.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
        
        mock_chunker.return_value = sample_chunks
        mock_gemini.return_value = sample_embeddings
        
        # Action
        response = client.post(f"/embed?document_id={sample_document['id']}")
        
        # Assertions
        assert response.status_code == 200
        # Verify insert was called exactly once with a list of records
        assert mock_insert.call_count == 1
        call_args = mock_insert.call_args[0][0]
        assert isinstance(call_args, list)
        assert len(call_args) == 3


class TestEmbedAuthentication:
    """Tests for authentication and authorization."""
    
    def test_embed_unauthorized(self, mock_supabase):
        """Test that JWT authentication is required."""
        # Create a fresh app without dependency overrides
        app = create_app()
        client = TestClient(app)
        
        # Make request without authentication
        response = client.post("/embed?document_id=123e4567-e89b-12d3-a456-426614174000")
        
        # Should return 401 Unauthorized
        assert response.status_code == 401
    
    def test_embed_document_not_owned(
        self, client, mock_supabase
    ):
        """Test that ownership check prevents unauthorized access."""
        # Setup mock to return empty result (document exists but belongs to different user)
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        
        # Action
        response = client.post("/embed?document_id=123e4567-e89b-12d3-a456-426614174000")
        
        # Assertions
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower() or "access denied" in response.json()["detail"].lower()


class TestEmbedErrorHandling:
    """Tests for error handling scenarios."""
    
    def test_embed_invalid_document_id(self, client):
        """Test 422 error for invalid document_id format (FastAPI validation)."""
        # Action - use invalid UUID format
        response = client.post("/embed?document_id=invalid-uuid-format")
        
        # Assertions - FastAPI returns 422 for validation errors
        assert response.status_code == 422
    
    def test_embed_delete_embeddings_failure(
        self, client, mock_supabase, sample_document
    ):
        """Test error handling when deleting existing embeddings fails."""
        # Setup mocks
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        
        # Mock successful document fetch
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[sample_document]
        )
        
        # Mock delete to fail
        mock_supabase_instance.table.return_value.delete.return_value.eq.return_value.execute.side_effect = Exception("Delete error")
        
        # Action
        response = client.post(f"/embed?document_id={sample_document['id']}")
        
        # Assertions
        assert response.status_code == 500
        assert "failed to delete existing embeddings" in response.json()["detail"].lower()
    
    def test_embed_document_not_found(
        self, client, mock_supabase
    ):
        """Test 404 error for non-existent document."""
        # Setup mock to return empty result
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        
        # Action
        response = client.post("/embed?document_id=123e4567-e89b-12d3-a456-426614174000")
        
        # Assertions
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_embed_no_extracted_text(
        self, client, mock_supabase
    ):
        """Test 400 error for documents without extracted text."""
        # Setup mock to return document with null extracted_text
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"extracted_text": None, "status": "uploaded"}]
        )
        
        # Action
        response = client.post("/embed?document_id=123e4567-e89b-12d3-a456-426614174000")
        
        # Assertions
        assert response.status_code == 400
        assert "no extracted text" in response.json()["detail"].lower()
    
    def test_embed_empty_extracted_text(
        self, client, mock_supabase
    ):
        """Test 400 error for documents with empty extracted text."""
        # Setup mock to return document with empty string
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"extracted_text": "   ", "status": "extracted"}]
        )
        
        # Action
        response = client.post("/embed?document_id=123e4567-e89b-12d3-a456-426614174000")
        
        # Assertions
        assert response.status_code == 400
        assert "no extracted text" in response.json()["detail"].lower()
    
    def test_embed_chunking_failure(
        self, client, mock_supabase, mock_chunker, sample_document
    ):
        """Test error handling when chunking fails."""
        # Setup mocks
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        
        # Mock successful document fetch
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[sample_document]
        )
        
        # Mock update for status='failed'
        mock_update = MagicMock()
        mock_supabase_instance.table.return_value.update = mock_update
        mock_update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
        
        mock_chunker.side_effect = Exception("Chunking error")
        
        # Action
        response = client.post(f"/embed?document_id={sample_document['id']}")
        
        # Assertions
        assert response.status_code == 500
        assert "failed to chunk" in response.json()["detail"].lower()
        
        # Verify document status was updated to 'failed'
        mock_update.assert_called_once_with({"status": "failed"})
        # Verify the filter was applied correctly
        assert mock_update.return_value.eq.called
    
    def test_embed_empty_chunks(
        self, client, mock_supabase, mock_chunker, sample_document
    ):
        """Test error handling when chunking returns empty list."""
        # Setup mocks
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[sample_document]
        )
        
        mock_chunker.return_value = []
        
        # Action
        response = client.post(f"/embed?document_id={sample_document['id']}")
        
        # Assertions
        assert response.status_code == 400
        assert "no chunks" in response.json()["detail"].lower()
    
    def test_embed_gemini_api_failure(
        self, client, mock_supabase, mock_chunker, mock_gemini,
        sample_document, sample_chunks
    ):
        """Test error handling when Gemini API fails."""
        # Setup mocks
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        
        # Mock successful document fetch
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[sample_document]
        )
        
        # Mock successful delete
        mock_supabase_instance.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        # Mock update for status='failed'
        mock_update = MagicMock()
        mock_supabase_instance.table.return_value.update = mock_update
        mock_update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
        
        mock_chunker.return_value = sample_chunks
        mock_gemini.side_effect = RuntimeError("API error")
        
        # Action
        response = client.post(f"/embed?document_id={sample_document['id']}")
        
        # Assertions
        assert response.status_code == 500
        assert "failed to generate embeddings" in response.json()["detail"].lower()
        
        # Verify document status was updated to 'failed'
        mock_update.assert_called_once_with({"status": "failed"})
        # Verify the filter was applied correctly
        assert mock_update.return_value.eq.called
    
    def test_embed_embeddings_count_mismatch(
        self, client, mock_supabase, mock_chunker, mock_gemini,
        sample_document, sample_chunks
    ):
        """Test error handling when embeddings count doesn't match chunks count."""
        # Setup mocks
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        
        # Mock successful document fetch
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[sample_document]
        )
        
        # Mock successful delete
        mock_supabase_instance.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        # Mock update for status='failed'
        mock_update = MagicMock()
        mock_supabase_instance.table.return_value.update = mock_update
        mock_update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
        
        mock_chunker.return_value = sample_chunks  # 3 chunks
        # Return only 2 embeddings - mismatch!
        mock_gemini.return_value = [[0.1] * 768, [0.2] * 768]
        
        # Action
        response = client.post(f"/embed?document_id={sample_document['id']}")
        
        # Assertions
        assert response.status_code == 500
        assert "mismatch" in response.json()["detail"].lower()
        assert "2 embeddings" in response.json()["detail"]
        assert "3 chunks" in response.json()["detail"]
        
        # Verify document status was updated to 'failed'
        mock_update.assert_called_once_with({"status": "failed"})
        # Verify the filter was applied correctly
        assert mock_update.return_value.eq.called
    
    def test_embed_database_insert_failure(
        self, client, mock_supabase, mock_chunker, mock_gemini,
        sample_document, sample_chunks, sample_embeddings
    ):
        """Test error handling when database insert fails."""
        # Setup mocks
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        
        # Mock successful document fetch
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[sample_document]
        )
        
        # Mock successful delete
        mock_supabase_instance.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        # Mock insert to fail
        mock_supabase_instance.table.return_value.insert.return_value.execute.side_effect = Exception("Database error")
        
        # Mock update for status='failed'
        mock_update = MagicMock()
        mock_supabase_instance.table.return_value.update = mock_update
        mock_update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
        
        mock_chunker.return_value = sample_chunks
        mock_gemini.return_value = sample_embeddings
        
        # Action
        response = client.post(f"/embed?document_id={sample_document['id']}")
        
        # Assertions
        assert response.status_code == 500
        assert "failed to save embeddings" in response.json()["detail"].lower()
        
        # Verify document status was updated to 'failed'
        mock_update.assert_called_once_with({"status": "failed"})
        # Verify the filter was applied correctly
        assert mock_update.return_value.eq.called
    
    def test_embed_idempotent(
        self, client, mock_supabase, mock_chunker, mock_gemini,
        sample_document, sample_chunks, sample_embeddings
    ):
        """Test that re-embedding deletes old embeddings first."""
        # Setup mocks
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        
        mock_delete = MagicMock()
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[sample_document]
        )
        mock_supabase_instance.table.return_value.delete = mock_delete
        mock_delete.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "old1"}, {"id": "old2"}]  # Simulate existing embeddings
        )
        mock_supabase_instance.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
        mock_supabase_instance.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
        
        mock_chunker.return_value = sample_chunks
        mock_gemini.return_value = sample_embeddings
        
        # Action - call twice
        response1 = client.post(f"/embed?document_id={sample_document['id']}")
        response2 = client.post(f"/embed?document_id={sample_document['id']}")
        
        # Assertions
        assert response1.status_code == 200
        assert response2.status_code == 200
        # Verify delete was called before insert (idempotent behavior)
        assert mock_delete.call_count == 2


# Parametrized tests

@pytest.mark.parametrize("chunk_count", [1, 10, 100])
def test_embed_various_chunk_counts(
    client, mock_supabase, mock_chunker, mock_gemini,
    sample_document, chunk_count
):
    """Test with different document sizes (1 chunk, 10 chunks, 100 chunks)."""
    # Setup mocks
    mock_supabase_instance = MagicMock()
    with patch('app.routes.embed.get_supabase_client', return_value=mock_supabase_instance):
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[sample_document]
        )
        mock_supabase_instance.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase_instance.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
        mock_supabase_instance.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
        
        chunks = [f"Chunk {i}" for i in range(chunk_count)]
        embeddings = [[0.1] * 768 for _ in range(chunk_count)]
        
        with patch('app.routes.embed.chunk_text', return_value=chunks):
            with patch('app.routes.embed.generate_embeddings_batch', return_value=embeddings):
                # Action
                response = client.post(f"/embed?document_id={sample_document['id']}")
                
                # Assertions
                assert response.status_code == 200
                data = response.json()
                assert data["chunk_count"] == chunk_count
                assert data["embedding_count"] == chunk_count
