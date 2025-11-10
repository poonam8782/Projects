"""
Tests for the /synthesize endpoint

Tests cover authentication, multi-document ownership verification,
text aggregation, Gemini synthesis generation, source attribution parsing,
and error handling.
"""

import pytest
from unittest.mock import patch, MagicMock
import json
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def sample_document_ids():
    """Return list of 3 UUIDs for testing."""
    return [uuid4(), uuid4(), uuid4()]


@pytest.fixture
def sample_documents(sample_document_ids):
    """Return list of 3 mock documents with extracted_text."""
    return [
        {
            "id": str(sample_document_ids[0]),
            "filename": "report.pdf",
            "extracted_text": "This is the content of the first document about AI research. " * 100
        },
        {
            "id": str(sample_document_ids[1]),
            "filename": "analysis.docx",
            "extracted_text": "This is the content of the second document about machine learning. " * 100
        },
        {
            "id": str(sample_document_ids[2]),
            "filename": "notes.txt",
            "extracted_text": "This is the content of the third document about neural networks. " * 100
        }
    ]


@pytest.fixture
def sample_synthesis_markdown():
    """Return realistic markdown with Sources section."""
    return """## Introduction

This synthesis combines insights from 3 documents on AI and machine learning topics.

## Key Findings

- Common theme 1: AI research is advancing rapidly
- Common theme 2: Machine learning applications are diverse
- Common theme 3: Neural networks are fundamental to modern AI

## Synthesis

Detailed analysis combining insights from all documents. The documents collectively
demonstrate the progression from basic AI research to practical machine learning
applications, with neural networks serving as the foundation.

## Conclusion

The combined analysis reveals a cohesive narrative about AI advancement and its
practical applications through machine learning and neural networks.

## Sources

**Document 1: report.pdf**
- AI research is advancing rapidly
- New techniques are emerging
- Applications span multiple domains

**Document 2: analysis.docx**
- Machine learning has diverse applications
- Practical implementation is key
- Industry adoption is growing

**Document 3: notes.txt**
- Neural networks are fundamental
- Deep learning shows promise
- Future directions are exciting
"""


class TestSynthesizeEndpoint:
    """Test synthesize endpoint basic functionality."""
    
    @patch('app.routes.synthesis.get_supabase_client')
    @patch('app.routes.synthesis.synthesize_documents')
    @patch('app.core.auth.get_supabase_client')
    def test_synthesize_summary_success(
        self,
        mock_auth_supabase,
        mock_synthesize,
        mock_supabase,
        client,
        sample_document_ids,
        sample_documents,
        sample_synthesis_markdown
    ):
        """Test successful synthesis with type='summary'."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock document fetch
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=sample_documents)
        mock_supabase.return_value = mock_client
        
        # Mock Gemini synthesis
        mock_synthesize.return_value = sample_synthesis_markdown
        
        # Make request
        response = client.post(
            "/synthesize",
            json={
                "document_ids": [str(doc_id) for doc_id in sample_document_ids],
                "synthesis_type": "summary",
                "include_embeddings": False
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["synthesis_type"] == "summary"
        assert "markdown_output" in data
        assert len(data["markdown_output"]) > 0
        assert "sources" in data
        assert data["document_count"] == 3
        assert data["status"] == "success"
        assert "processing_time_seconds" in data
    
    @patch('app.routes.synthesis.get_supabase_client')
    @patch('app.routes.synthesis.synthesize_documents')
    @patch('app.core.auth.get_supabase_client')
    def test_synthesize_comparison_success(
        self,
        mock_auth_supabase,
        mock_synthesize,
        mock_supabase,
        client,
        sample_document_ids,
        sample_documents,
        sample_synthesis_markdown
    ):
        """Test successful synthesis with type='comparison'."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock document fetch
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=sample_documents)
        mock_supabase.return_value = mock_client
        
        # Mock Gemini synthesis
        mock_synthesize.return_value = sample_synthesis_markdown
        
        # Make request
        response = client.post(
            "/synthesize",
            json={
                "document_ids": [str(doc_id) for doc_id in sample_document_ids],
                "synthesis_type": "comparison",
                "include_embeddings": False
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["synthesis_type"] == "comparison"


class TestSynthesizeAuthentication:
    """Test synthesis authentication requirements."""
    
    def test_synthesize_unauthorized(self, client, sample_document_ids):
        """Test that synthesis requires authentication."""
        response = client.post(
            "/synthesize",
            json={
                "document_ids": [str(doc_id) for doc_id in sample_document_ids],
                "synthesis_type": "summary"
            }
        )
        
        assert response.status_code == 401


class TestSynthesizeMultiDocumentValidation:
    """Test multi-document ownership and validation."""
    
    @patch('app.routes.synthesis.get_supabase_client')
    @patch('app.core.auth.get_supabase_client')
    def test_synthesize_documents_not_found(
        self,
        mock_auth_supabase,
        mock_supabase,
        client,
        sample_document_ids
    ):
        """Test 404 error when documents don't exist or aren't owned."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock document fetch returning fewer documents
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])  # No documents found
        mock_supabase.return_value = mock_client
        
        # Make request
        response = client.post(
            "/synthesize",
            json={
                "document_ids": [str(doc_id) for doc_id in sample_document_ids],
                "synthesis_type": "summary"
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 404
        assert "not found or access denied" in response.json()["detail"]
    
    @patch('app.routes.synthesis.get_supabase_client')
    @patch('app.core.auth.get_supabase_client')
    def test_synthesize_partial_ownership(
        self,
        mock_auth_supabase,
        mock_supabase,
        client,
        sample_document_ids,
        sample_documents
    ):
        """Test 404 error when user owns some but not all documents."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock document fetch returning only 2 of 3 documents
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=sample_documents[:2])
        mock_supabase.return_value = mock_client
        
        # Make request
        response = client.post(
            "/synthesize",
            json={
                "document_ids": [str(doc_id) for doc_id in sample_document_ids],
                "synthesis_type": "summary"
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 404
    
    @patch('app.routes.synthesis.get_supabase_client')
    @patch('app.core.auth.get_supabase_client')
    def test_synthesize_missing_extracted_text(
        self,
        mock_auth_supabase,
        mock_supabase,
        client,
        sample_document_ids
    ):
        """Test 400 error when documents lack extracted_text."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock documents with missing extracted_text
        documents_missing_text = [
            {
                "id": str(sample_document_ids[0]),
                "filename": "doc1.pdf",
                "extracted_text": "Some text"
            },
            {
                "id": str(sample_document_ids[1]),
                "filename": "doc2.pdf",
                "extracted_text": ""  # Missing text
            },
            {
                "id": str(sample_document_ids[2]),
                "filename": "doc3.pdf",
                "extracted_text": "   "  # Empty text
            }
        ]
        
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=documents_missing_text)
        mock_supabase.return_value = mock_client
        
        # Make request
        response = client.post(
            "/synthesize",
            json={
                "document_ids": [str(doc_id) for doc_id in sample_document_ids],
                "synthesis_type": "summary"
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 400
        assert "missing extracted text" in response.json()["detail"].lower()
        assert "doc2.pdf" in response.json()["detail"]
        assert "doc3.pdf" in response.json()["detail"]
    
    def test_synthesize_minimum_documents(self, client):
        """Test validation requires at least 2 documents."""
        response = client.post(
            "/synthesize",
            json={
                "document_ids": [str(uuid4())],  # Only 1 document
                "synthesis_type": "summary"
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 422  # Pydantic validation error
    
    def test_synthesize_maximum_documents(self, client):
        """Test validation limits to 10 documents."""
        response = client.post(
            "/synthesize",
            json={
                "document_ids": [str(uuid4()) for _ in range(11)],  # 11 documents
                "synthesis_type": "summary"
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 422  # Pydantic validation error
    
    def test_synthesize_invalid_synthesis_type(self, client, sample_document_ids):
        """Test validation for synthesis_type."""
        response = client.post(
            "/synthesize",
            json={
                "document_ids": [str(doc_id) for doc_id in sample_document_ids],
                "synthesis_type": "invalid"  # Invalid type
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 422  # Pydantic validation error


class TestSynthesizeErrorHandling:
    """Test synthesis error handling."""
    
    @patch('app.routes.synthesis.get_supabase_client')
    @patch('app.routes.synthesis.synthesize_documents')
    @patch('app.core.auth.get_supabase_client')
    def test_synthesize_gemini_failure(
        self,
        mock_auth_supabase,
        mock_synthesize,
        mock_supabase,
        client,
        sample_document_ids,
        sample_documents
    ):
        """Test error handling when Gemini API fails."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock document fetch
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=sample_documents)
        mock_supabase.return_value = mock_client
        
        # Mock Gemini failure
        mock_synthesize.side_effect = RuntimeError("Gemini API error")
        
        # Make request
        response = client.post(
            "/synthesize",
            json={
                "document_ids": [str(doc_id) for doc_id in sample_document_ids],
                "synthesis_type": "summary"
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 500

    @patch('app.routes.synthesis.get_supabase_client')
    @patch('app.routes.synthesis.synthesize_documents')
    @patch('app.core.auth.get_supabase_client')
    def test_synthesize_rate_limit(
        self,
        mock_auth_supabase,
        mock_synthesize,
        mock_supabase,
        client,
        sample_document_ids,
        sample_documents
    ):
        """Test 429 mapping when Gemini rate limit occurs (Comment 6)."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock document fetch
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=sample_documents)
        mock_supabase.return_value = mock_client
        
        # Mock Gemini rate limit
        mock_synthesize.side_effect = RuntimeError("Gemini API rate limit exceeded")
        
        # Make request
        response = client.post(
            "/synthesize",
            json={
                "document_ids": [str(doc_id) for doc_id in sample_document_ids],
                "synthesis_type": "summary"
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 429
        assert "rate limit" in response.json()["detail"].lower()


class TestSynthesizeSourceAttribution:
    """Test source attribution parsing."""
    
    @patch('app.routes.synthesis.get_supabase_client')
    @patch('app.routes.synthesis.synthesize_documents')
    @patch('app.core.auth.get_supabase_client')
    def test_synthesize_source_attribution_parsing(
        self,
        mock_auth_supabase,
        mock_synthesize,
        mock_supabase,
        client,
        sample_document_ids,
        sample_documents,
        sample_synthesis_markdown
    ):
        """Test Sources section is parsed correctly."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock document fetch
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=sample_documents)
        mock_supabase.return_value = mock_client
        
        # Mock Gemini synthesis with Sources section
        mock_synthesize.return_value = sample_synthesis_markdown
        
        # Make request
        response = client.post(
            "/synthesize",
            json={
                "document_ids": [str(doc_id) for doc_id in sample_document_ids],
                "synthesis_type": "summary"
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check sources were parsed
        assert len(data["sources"]) > 0
        assert all("filename" in src for src in data["sources"])
        assert all("key_points" in src for src in data["sources"])
    
    @patch('app.routes.synthesis.get_supabase_client')
    @patch('app.routes.synthesis.synthesize_documents')
    @patch('app.core.auth.get_supabase_client')
    def test_synthesize_missing_sources_section(
        self,
        mock_auth_supabase,
        mock_synthesize,
        mock_supabase,
        client,
        sample_document_ids,
        sample_documents
    ):
        """Test graceful handling when markdown lacks Sources section."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock document fetch
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=sample_documents)
        mock_supabase.return_value = mock_client
        
        # Mock Gemini synthesis WITHOUT Sources section
        markdown_no_sources = """## Introduction
This is a synthesis without sources section.

## Analysis
Some analysis here."""
        mock_synthesize.return_value = markdown_no_sources
        
        # Make request
        response = client.post(
            "/synthesize",
            json={
                "document_ids": [str(doc_id) for doc_id in sample_document_ids],
                "synthesis_type": "summary"
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Sources should be created with empty key_points
        assert len(data["sources"]) == 3
        assert all(len(src["key_points"]) == 0 for src in data["sources"])


class TestSynthesizeMetrics:
    """Test synthesis metrics tracking."""
    
    @patch('app.routes.synthesis.get_supabase_client')
    @patch('app.routes.synthesis.synthesize_documents')
    @patch('app.core.auth.get_supabase_client')
    def test_synthesize_processing_time_tracked(
        self,
        mock_auth_supabase,
        mock_synthesize,
        mock_supabase,
        client,
        sample_document_ids,
        sample_documents,
        sample_synthesis_markdown
    ):
        """Test processing_time_seconds is measured and returned."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock document fetch
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=sample_documents)
        mock_supabase.return_value = mock_client
        
        # Mock Gemini synthesis
        mock_synthesize.return_value = sample_synthesis_markdown
        
        # Make request
        response = client.post(
            "/synthesize",
            json={
                "document_ids": [str(doc_id) for doc_id in sample_document_ids],
                "synthesis_type": "summary"
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "processing_time_seconds" in data
        assert data["processing_time_seconds"] >= 0
    
    @patch('app.routes.synthesis.get_supabase_client')
    @patch('app.routes.synthesis.synthesize_documents')
    @patch('app.core.auth.get_supabase_client')
    def test_synthesize_total_text_length(
        self,
        mock_auth_supabase,
        mock_synthesize,
        mock_supabase,
        client,
        sample_document_ids,
        sample_documents,
        sample_synthesis_markdown
    ):
        """Test total_text_length is calculated correctly."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock document fetch
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=sample_documents)
        mock_supabase.return_value = mock_client
        
        # Mock Gemini synthesis
        mock_synthesize.return_value = sample_synthesis_markdown
        
        # Calculate expected total length
        expected_length = sum(len(doc["extracted_text"]) for doc in sample_documents)
        
        # Make request
        response = client.post(
            "/synthesize",
            json={
                "document_ids": [str(doc_id) for doc_id in sample_document_ids],
                "synthesis_type": "summary"
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_text_length"] == expected_length


@pytest.mark.parametrize("document_count", [2, 5, 10])
@patch('app.routes.synthesis.get_supabase_client')
@patch('app.routes.synthesis.synthesize_documents')
@patch('app.core.auth.get_supabase_client')
def test_synthesize_various_document_counts(
    mock_auth_supabase,
    mock_synthesize,
    mock_supabase,
    client,
    sample_synthesis_markdown,
    document_count
):
    """Test synthesis with different document counts."""
    # Mock authentication
    mock_auth_client = MagicMock()
    mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
    mock_auth_supabase.return_value = mock_auth_client
    
    # Create documents
    document_ids = [uuid4() for _ in range(document_count)]
    documents = [
        {
            "id": str(doc_id),
            "filename": f"doc{i}.pdf",
            "extracted_text": f"Content of document {i}" * 100
        }
        for i, doc_id in enumerate(document_ids)
    ]
    
    # Mock document fetch
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.select.return_value = mock_table
    mock_table.in_.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = MagicMock(data=documents)
    mock_supabase.return_value = mock_client
    
    # Mock Gemini synthesis
    mock_synthesize.return_value = sample_synthesis_markdown
    
    # Make request
    response = client.post(
        "/synthesize",
        json={
            "document_ids": [str(doc_id) for doc_id in document_ids],
            "synthesis_type": "summary"
        },
        headers={"Authorization": "Bearer fake-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["document_count"] == document_count


@pytest.mark.parametrize("synthesis_type", ["summary", "comparison"])
@patch('app.routes.synthesis.get_supabase_client')
@patch('app.routes.synthesis.synthesize_documents')
@patch('app.core.auth.get_supabase_client')
def test_synthesize_both_synthesis_types(
    mock_auth_supabase,
    mock_synthesize,
    mock_supabase,
    client,
    sample_synthesis_markdown,
    synthesis_type
):
    """Test both summary and comparison synthesis types."""
    # Mock authentication
    mock_auth_client = MagicMock()
    mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
    mock_auth_supabase.return_value = mock_auth_client
    
    # Create documents
    document_ids = [uuid4(), uuid4(), uuid4()]
    documents = [
        {
            "id": str(doc_id),
            "filename": f"doc{i}.pdf",
            "extracted_text": f"Content {i}" * 100
        }
        for i, doc_id in enumerate(document_ids)
    ]
    
    # Mock document fetch
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.select.return_value = mock_table
    mock_table.in_.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.execute.return_value = MagicMock(data=documents)
    mock_supabase.return_value = mock_client
    
    # Mock Gemini synthesis
    mock_synthesize.return_value = sample_synthesis_markdown
    
    # Make request
    response = client.post(
        "/synthesize",
        json={
            "document_ids": [str(doc_id) for doc_id in document_ids],
            "synthesis_type": synthesis_type
        },
        headers={"Authorization": "Bearer fake-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["synthesis_type"] == synthesis_type
