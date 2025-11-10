"""
Tests for the /export endpoint

Tests cover authentication, document ownership, multi-source data fetching
(notes from Storage, flashcards from database, chat history from database),
markdown assembly, PDF generation with weasyprint, storage upload, signed URL
generation, and error handling.
"""

import pytest
from unittest.mock import patch, MagicMock, call
from io import BytesIO
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def sample_document():
    """Return dict representing a document with all metadata fields."""
    return {
        "id": str(uuid4()),
        "filename": "test-document.pdf",
        "size_bytes": 1500000,
        "mime_type": "application/pdf",
        "status": "embedded",
        "created_at": "2024-01-15T10:30:00Z",
        "extracted_text": "This is the extracted text content of the document."
    }


@pytest.fixture
def sample_notes_markdown():
    """Return realistic markdown notes content."""
    return """# Study Notes

## Introduction
This document covers key concepts in AI and machine learning.

## Main Topics
- Neural networks
- Deep learning
- Natural language processing

## Key Findings
The research demonstrates significant advances in AI capabilities.
"""


@pytest.fixture
def sample_flashcards():
    """Return list of 5 flashcard dicts with Q&A and SM-2 fields."""
    return [
        {
            "question": "What is a neural network?",
            "answer": "A computing system inspired by biological neural networks",
            "efactor": 2.5,
            "repetitions": 0,
            "interval": 0,
            "next_review": "2024-01-16T10:00:00Z"
        },
        {
            "question": "What is deep learning?",
            "answer": "A subset of machine learning using multi-layer neural networks",
            "efactor": 2.5,
            "repetitions": 1,
            "interval": 1,
            "next_review": "2024-01-17T10:00:00Z"
        },
        {
            "question": "What is NLP?",
            "answer": "Natural Language Processing - AI field focused on human language",
            "efactor": 2.6,
            "repetitions": 2,
            "interval": 6,
            "next_review": "2024-01-22T10:00:00Z"
        },
        {
            "question": "What is supervised learning?",
            "answer": "Machine learning with labeled training data",
            "efactor": 2.5,
            "repetitions": 0,
            "interval": 0,
            "next_review": "2024-01-16T10:00:00Z"
        },
        {
            "question": "What is unsupervised learning?",
            "answer": "Machine learning without labeled data, finding patterns autonomously",
            "efactor": 2.5,
            "repetitions": 0,
            "interval": 0,
            "next_review": "2024-01-16T10:00:00Z"
        }
    ]


@pytest.fixture
def sample_chat_history():
    """Return list of conversation message dicts with role, content, created_at."""
    return [
        {
            "role": "user",
            "content": "What are the main topics covered?",
            "created_at": "2024-01-15T10:30:00Z"
        },
        {
            "role": "model",
            "content": "The document covers neural networks, deep learning, and NLP.",
            "created_at": "2024-01-15T10:30:15Z"
        },
        {
            "role": "user",
            "content": "Can you explain deep learning?",
            "created_at": "2024-01-15T10:31:00Z"
        },
        {
            "role": "model",
            "content": "Deep learning is a subset of ML using multi-layer neural networks.",
            "created_at": "2024-01-15T10:31:10Z"
        }
    ]


@pytest.fixture
def sample_export_markdown(sample_document):
    """Return complete export markdown with all sections."""
    return f"""# Document Export: {sample_document['filename']}

## Document Information
- **Filename**: {sample_document['filename']}
- **Size**: 1.43 MB

## Generated Notes
# Study Notes
...

## Flashcards (5 cards)
...

## Chat History (4 messages)
...

## Export Metadata
- **Export Date**: January 15, 2024
"""


@pytest.fixture
def sample_pdf_bytes():
    """Return fake PDF bytes for testing."""
    return b"%PDF-1.4\n%fake pdf content for testing\n%%EOF"


class TestExportEndpoint:
    """Test export endpoint basic functionality."""
    
    @patch('app.routes.export.get_supabase_client')
    @patch('app.routes.export.fetch_notes_from_storage')
    @patch('app.routes.export.fetch_flashcards_from_db')
    @patch('app.routes.export.fetch_chat_history_from_db')
    @patch('app.core.auth.get_supabase_client')
    def test_export_markdown_success(
        self,
        mock_auth_supabase,
        mock_chat_history,
        mock_flashcards,
        mock_notes,
        mock_supabase,
        client,
        sample_document,
        sample_notes_markdown,
        sample_flashcards
    ):
        """Test successful markdown export flow."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock document fetch
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[sample_document])
        
        # Mock storage operations
        mock_storage = MagicMock()
        mock_storage.upload.return_value = None
        mock_storage.create_signed_url.return_value = {
            'signedURL': 'https://example.com/signed-url'
        }
        mock_client.storage.from_.return_value = mock_storage
        
        mock_supabase.return_value = mock_client
        
        # Mock data fetching
        mock_notes.return_value = sample_notes_markdown
        mock_flashcards.return_value = sample_flashcards
        mock_chat_history.return_value = []
        
        # Make request
        response = client.post(
            "/export",
            json={
                "document_id": sample_document["id"],
                "format": "markdown",
                "include_notes": True,
                "include_flashcards": True,
                "include_chat_history": False
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["format"] == "markdown"
        assert data["filename"].endswith(".md")
        assert "download_url" in data
        assert data["download_url"] == 'https://example.com/signed-url'
        assert "metadata" in data["included_sections"]
        assert "notes" in data["included_sections"]
        assert "flashcards" in data["included_sections"]
        assert data["status"] == "success"
        assert "processing_time_seconds" in data
    
    @patch('app.routes.export.get_supabase_client')
    @patch('app.routes.export.fetch_notes_from_storage')
    @patch('app.routes.export.fetch_flashcards_from_db')
    @patch('app.routes.export.fetch_chat_history_from_db')
    @patch('app.routes.export.convert_markdown_to_pdf')
    @patch('app.core.auth.get_supabase_client')
    def test_export_pdf_success(
        self,
        mock_auth_supabase,
        mock_pdf_converter,
        mock_chat_history,
        mock_flashcards,
        mock_notes,
        mock_supabase,
        client,
        sample_document,
        sample_pdf_bytes
    ):
        """Test successful PDF export flow."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock document fetch
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[sample_document])
        
        # Mock storage operations
        mock_storage = MagicMock()
        mock_storage.upload.return_value = None
        mock_storage.create_signed_url.return_value = {
            'signedURL': 'https://example.com/signed-pdf'
        }
        mock_client.storage.from_.return_value = mock_storage
        
        mock_supabase.return_value = mock_client
        
        # Mock data fetching
        mock_notes.return_value = None
        mock_flashcards.return_value = []
        mock_chat_history.return_value = []
        
        # Mock PDF conversion
        mock_pdf_converter.return_value = sample_pdf_bytes
        
        # Make request
        response = client.post(
            "/export",
            json={
                "document_id": sample_document["id"],
                "format": "pdf",
                "include_notes": False,
                "include_flashcards": False,
                "include_chat_history": False
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["format"] == "pdf"
        assert data["filename"].endswith(".pdf")
        assert mock_pdf_converter.called
        assert data["size_bytes"] == len(sample_pdf_bytes)


class TestExportAuthentication:
    """Test export authentication and authorization."""
    
    def test_export_unauthorized(self, client, sample_document):
        """Test JWT authentication is required."""
        response = client.post(
            "/export",
            json={
                "document_id": sample_document["id"],
                "format": "markdown"
            }
        )
        
        assert response.status_code == 401
    
    @patch('app.routes.export.get_supabase_client')
    @patch('app.core.auth.get_supabase_client')
    def test_export_document_not_found(
        self,
        mock_auth_supabase,
        mock_supabase,
        client
    ):
        """Test 404 for non-existent document."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock document not found
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        mock_supabase.return_value = mock_client
        
        response = client.post(
            "/export",
            json={
                "document_id": str(uuid4()),
                "format": "markdown"
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 404


class TestExportValidation:
    """Test export request validation."""
    
    def test_export_invalid_format(self, client):
        """Test 422 Pydantic validation error for invalid format."""
        response = client.post(
            "/export",
            json={
                "document_id": str(uuid4()),
                "format": "docx"  # Invalid format
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 422


class TestExportDataAggregation:
    """Test multi-source data aggregation."""
    
    @patch('app.routes.export.get_supabase_client')
    @patch('app.routes.export.fetch_notes_from_storage')
    @patch('app.routes.export.fetch_flashcards_from_db')
    @patch('app.routes.export.fetch_chat_history_from_db')
    @patch('app.core.auth.get_supabase_client')
    def test_export_with_all_sections(
        self,
        mock_auth_supabase,
        mock_chat_history,
        mock_flashcards,
        mock_notes,
        mock_supabase,
        client,
        sample_document,
        sample_notes_markdown,
        sample_flashcards,
        sample_chat_history
    ):
        """Test export includes all sections when data exists."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock document fetch
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[sample_document])
        
        # Mock storage operations
        mock_storage = MagicMock()
        mock_storage.upload.return_value = None
        mock_storage.create_signed_url.return_value = {
            'signedURL': 'https://example.com/signed-url'
        }
        mock_client.storage.from_.return_value = mock_storage
        
        mock_supabase.return_value = mock_client
        
        # Mock all data sources returning content
        mock_notes.return_value = sample_notes_markdown
        mock_flashcards.return_value = sample_flashcards
        mock_chat_history.return_value = sample_chat_history
        
        # Make request
        response = client.post(
            "/export",
            json={
                "document_id": sample_document["id"],
                "format": "markdown",
                "include_notes": True,
                "include_flashcards": True,
                "include_chat_history": True
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert set(data["included_sections"]) == {"metadata", "notes", "flashcards", "chat_history"}
    
    @patch('app.routes.export.get_supabase_client')
    @patch('app.routes.export.fetch_notes_from_storage')
    @patch('app.routes.export.fetch_flashcards_from_db')
    @patch('app.routes.export.fetch_chat_history_from_db')
    @patch('app.core.auth.get_supabase_client')
    def test_export_without_notes(
        self,
        mock_auth_supabase,
        mock_chat_history,
        mock_flashcards,
        mock_notes,
        mock_supabase,
        client,
        sample_document,
        sample_flashcards
    ):
        """Test export works when notes don't exist."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock document fetch
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[sample_document])
        
        # Mock storage operations
        mock_storage = MagicMock()
        mock_storage.upload.return_value = None
        mock_storage.create_signed_url.return_value = {
            'signedURL': 'https://example.com/signed-url'
        }
        mock_client.storage.from_.return_value = mock_storage
        
        mock_supabase.return_value = mock_client
        
        # Mock notes not found
        mock_notes.return_value = None
        mock_flashcards.return_value = sample_flashcards
        mock_chat_history.return_value = []
        
        # Make request
        response = client.post(
            "/export",
            json={
                "document_id": sample_document["id"],
                "format": "markdown",
                "include_notes": True,
                "include_flashcards": True
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "notes" not in data["included_sections"]
        assert "flashcards" in data["included_sections"]
    
    @patch('app.routes.export.get_supabase_client')
    @patch('app.routes.export.fetch_notes_from_storage')
    @patch('app.routes.export.fetch_flashcards_from_db')
    @patch('app.routes.export.fetch_chat_history_from_db')
    @patch('app.core.auth.get_supabase_client')
    def test_export_without_flashcards(
        self,
        mock_auth_supabase,
        mock_chat_history,
        mock_flashcards,
        mock_notes,
        mock_supabase,
        client,
        sample_document
    ):
        """Test export works when no flashcards exist."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock document fetch
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[sample_document])
        
        # Mock storage operations
        mock_storage = MagicMock()
        mock_storage.upload.return_value = None
        mock_storage.create_signed_url.return_value = {
            'signedURL': 'https://example.com/signed-url'
        }
        mock_client.storage.from_.return_value = mock_storage
        
        mock_supabase.return_value = mock_client
        
        # Mock empty flashcards
        mock_notes.return_value = None
        mock_flashcards.return_value = []
        mock_chat_history.return_value = []
        
        # Make request
        response = client.post(
            "/export",
            json={
                "document_id": sample_document["id"],
                "format": "markdown",
                "include_flashcards": True
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "flashcards" not in data["included_sections"]
    
    @patch('app.routes.export.get_supabase_client')
    @patch('app.routes.export.fetch_notes_from_storage')
    @patch('app.routes.export.fetch_flashcards_from_db')
    @patch('app.routes.export.fetch_chat_history_from_db')
    @patch('app.core.auth.get_supabase_client')
    def test_export_without_chat_history(
        self,
        mock_auth_supabase,
        mock_chat_history,
        mock_flashcards,
        mock_notes,
        mock_supabase,
        client,
        sample_document
    ):
        """Test export works when chat history doesn't exist."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock document fetch
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[sample_document])
        
        # Mock storage operations
        mock_storage = MagicMock()
        mock_storage.upload.return_value = None
        mock_storage.create_signed_url.return_value = {
            'signedURL': 'https://example.com/signed-url'
        }
        mock_client.storage.from_.return_value = mock_storage
        
        mock_supabase.return_value = mock_client
        
        # Mock chat history not available (table doesn't exist)
        mock_notes.return_value = None
        mock_flashcards.return_value = []
        mock_chat_history.return_value = []
        
        # Make request
        response = client.post(
            "/export",
            json={
                "document_id": sample_document["id"],
                "format": "markdown",
                "include_chat_history": True
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "chat_history" not in data["included_sections"]
    
    @patch('app.routes.export.get_supabase_client')
    @patch('app.routes.export.fetch_notes_from_storage')
    @patch('app.routes.export.fetch_flashcards_from_db')
    @patch('app.routes.export.fetch_chat_history_from_db')
    @patch('app.core.auth.get_supabase_client')
    def test_export_metadata_only(
        self,
        mock_auth_supabase,
        mock_chat_history,
        mock_flashcards,
        mock_notes,
        mock_supabase,
        client,
        sample_document
    ):
        """Test export works with only document metadata."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock document fetch
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[sample_document])
        
        # Mock storage operations
        mock_storage = MagicMock()
        mock_storage.upload.return_value = None
        mock_storage.create_signed_url.return_value = {
            'signedURL': 'https://example.com/signed-url'
        }
        mock_client.storage.from_.return_value = mock_storage
        
        mock_supabase.return_value = mock_client
        
        # All optional data is None/empty
        mock_notes.return_value = None
        mock_flashcards.return_value = []
        mock_chat_history.return_value = []
        
        # Make request
        response = client.post(
            "/export",
            json={
                "document_id": sample_document["id"],
                "format": "markdown"
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["included_sections"] == ["metadata"]


class TestExportPDFGeneration:
    """Test PDF generation functionality."""
    
    @patch('app.routes.export.HTML')
    @patch('app.routes.export.markdown.markdown')
    def test_export_pdf_generation(self, mock_markdown, mock_html_class):
        """Test weasyprint is called correctly."""
        from app.routes.export import convert_markdown_to_pdf
        
        # Mock markdown conversion
        mock_markdown.return_value = "<h1>Test</h1><p>Content</p>"
        
        # Mock weasyprint
        mock_html_instance = MagicMock()
        mock_html_instance.write_pdf.return_value = b"fake pdf bytes"
        mock_html_class.return_value = mock_html_instance
        
        # Call function
        result = convert_markdown_to_pdf("# Test\n\nContent")
        
        # Verify markdown was converted
        assert mock_markdown.called
        mock_markdown.assert_called_once()
        
        # Verify HTML was created and PDF generated
        assert mock_html_class.called
        assert mock_html_instance.write_pdf.called
        assert result == b"fake pdf bytes"
    
    @patch('app.routes.export.get_supabase_client')
    @patch('app.routes.export.fetch_notes_from_storage')
    @patch('app.routes.export.fetch_flashcards_from_db')
    @patch('app.routes.export.fetch_chat_history_from_db')
    @patch('app.routes.export.convert_markdown_to_pdf')
    @patch('app.core.auth.get_supabase_client')
    def test_export_pdf_generation_failure(
        self,
        mock_auth_supabase,
        mock_pdf_converter,
        mock_chat_history,
        mock_flashcards,
        mock_notes,
        mock_supabase,
        client,
        sample_document
    ):
        """Test error handling when weasyprint fails."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock document fetch
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[sample_document])
        mock_supabase.return_value = mock_client
        
        # Mock data fetching
        mock_notes.return_value = None
        mock_flashcards.return_value = []
        mock_chat_history.return_value = []
        
        # Mock PDF generation failure
        mock_pdf_converter.side_effect = RuntimeError("Weasyprint error")
        
        # Make request
        response = client.post(
            "/export",
            json={
                "document_id": sample_document["id"],
                "format": "pdf"
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 500
        assert "PDF generation failed" in response.json()["detail"]
    
    @patch('app.routes.export.markdown.markdown')
    def test_export_markdown_to_html_conversion(self, mock_markdown):
        """Test markdown is converted to HTML before PDF generation."""
        from app.routes.export import convert_markdown_to_pdf
        
        mock_markdown.return_value = "<h1>Test</h1>"
        
        with patch('app.routes.export.HTML') as mock_html:
            mock_html_instance = MagicMock()
            mock_html_instance.write_pdf.return_value = b"pdf"
            mock_html.return_value = mock_html_instance
            
            convert_markdown_to_pdf("# Test")
            
            # Verify markdown called with extensions
            mock_markdown.assert_called_once()
            call_args = mock_markdown.call_args
            assert 'extensions' in call_args.kwargs
            assert 'extra' in call_args.kwargs['extensions']
            assert 'codehilite' in call_args.kwargs['extensions']
            assert 'tables' in call_args.kwargs['extensions']


class TestExportStorage:
    """Test storage operations."""
    
    @patch('app.routes.export.get_supabase_client')
    @patch('app.routes.export.fetch_notes_from_storage')
    @patch('app.routes.export.fetch_flashcards_from_db')
    @patch('app.routes.export.fetch_chat_history_from_db')
    @patch('app.core.auth.get_supabase_client')
    def test_export_storage_upload(
        self,
        mock_auth_supabase,
        mock_chat_history,
        mock_flashcards,
        mock_notes,
        mock_supabase,
        client,
        sample_document
    ):
        """Test file is uploaded to correct path with correct content type."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock document fetch
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[sample_document])
        
        # Mock storage operations
        mock_storage = MagicMock()
        mock_storage.create_signed_url.return_value = {
            'signedURL': 'https://example.com/signed-url'
        }
        mock_client.storage.from_.return_value = mock_storage
        
        mock_supabase.return_value = mock_client
        
        # Mock data fetching
        mock_notes.return_value = None
        mock_flashcards.return_value = []
        mock_chat_history.return_value = []
        
        # Make request
        response = client.post(
            "/export",
            json={
                "document_id": sample_document["id"],
                "format": "markdown"
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 200
        
        # Verify upload was called
        assert mock_storage.upload.called
        upload_args = mock_storage.upload.call_args
        
        # Check path includes user_id and document_id
        assert "test-user-id" in upload_args[0][0]
        assert str(sample_document["id"]) in upload_args[0][0]
        assert upload_args[0][0].endswith("-export.md")
        
        # Check content type
        assert upload_args[1]["file_options"]["content-type"] == "text/markdown"
        assert upload_args[1]["file_options"]["upsert"] == "true"
    
    @patch('app.routes.export.get_supabase_client')
    @patch('app.routes.export.fetch_notes_from_storage')
    @patch('app.routes.export.fetch_flashcards_from_db')
    @patch('app.routes.export.fetch_chat_history_from_db')
    @patch('app.core.auth.get_supabase_client')
    def test_export_signed_url_generation(
        self,
        mock_auth_supabase,
        mock_chat_history,
        mock_flashcards,
        mock_notes,
        mock_supabase,
        client,
        sample_document
    ):
        """Test signed URL is generated and returned."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock document fetch
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[sample_document])
        
        # Mock storage operations
        mock_storage = MagicMock()
        mock_storage.upload.return_value = None
        mock_storage.create_signed_url.return_value = {
            'signedURL': 'https://example.com/test-signed-url'
        }
        mock_client.storage.from_.return_value = mock_storage
        
        mock_supabase.return_value = mock_client
        
        # Mock data fetching
        mock_notes.return_value = None
        mock_flashcards.return_value = []
        mock_chat_history.return_value = []
        
        # Make request
        response = client.post(
            "/export",
            json={
                "document_id": sample_document["id"],
                "format": "markdown"
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify signed URL in response
        assert data["download_url"] == 'https://example.com/test-signed-url'
        
        # Verify create_signed_url was called with correct expiry
        assert mock_storage.create_signed_url.called
        signed_url_args = mock_storage.create_signed_url.call_args
        assert signed_url_args[1]["expires_in"] == 60
    
    @patch('app.routes.export.get_supabase_client')
    @patch('app.routes.export.fetch_notes_from_storage')
    @patch('app.routes.export.fetch_flashcards_from_db')
    @patch('app.routes.export.fetch_chat_history_from_db')
    @patch('app.core.auth.get_supabase_client')
    def test_export_idempotent(
        self,
        mock_auth_supabase,
        mock_chat_history,
        mock_flashcards,
        mock_notes,
        mock_supabase,
        client,
        sample_document
    ):
        """Test re-exporting works (upsert behavior)."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock document fetch
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[sample_document])
        
        # Mock storage operations
        mock_storage = MagicMock()
        mock_storage.upload.return_value = None
        mock_storage.create_signed_url.return_value = {
            'signedURL': 'https://example.com/signed-url'
        }
        mock_client.storage.from_.return_value = mock_storage
        
        mock_supabase.return_value = mock_client
        
        # Mock data fetching
        mock_notes.return_value = None
        mock_flashcards.return_value = []
        mock_chat_history.return_value = []
        
        # Make request twice
        response1 = client.post(
            "/export",
            json={
                "document_id": sample_document["id"],
                "format": "markdown"
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        response2 = client.post(
            "/export",
            json={
                "document_id": sample_document["id"],
                "format": "markdown"
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Verify upsert was used
        upload_args = mock_storage.upload.call_args
        assert upload_args[1]["file_options"]["upsert"] == "true"


class TestExportMetrics:
    """Test export metrics tracking."""
    
    @patch('app.routes.export.get_supabase_client')
    @patch('app.routes.export.fetch_notes_from_storage')
    @patch('app.routes.export.fetch_flashcards_from_db')
    @patch('app.routes.export.fetch_chat_history_from_db')
    @patch('app.core.auth.get_supabase_client')
    def test_export_processing_time_tracked(
        self,
        mock_auth_supabase,
        mock_chat_history,
        mock_flashcards,
        mock_notes,
        mock_supabase,
        client,
        sample_document
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
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[sample_document])
        
        # Mock storage operations
        mock_storage = MagicMock()
        mock_storage.upload.return_value = None
        mock_storage.create_signed_url.return_value = {
            'signedURL': 'https://example.com/signed-url'
        }
        mock_client.storage.from_.return_value = mock_storage
        
        mock_supabase.return_value = mock_client
        
        # Mock data fetching
        mock_notes.return_value = None
        mock_flashcards.return_value = []
        mock_chat_history.return_value = []
        
        # Make request
        response = client.post(
            "/export",
            json={
                "document_id": sample_document["id"],
                "format": "markdown"
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "processing_time_seconds" in data
        assert isinstance(data["processing_time_seconds"], (int, float))
        assert data["processing_time_seconds"] >= 0


class TestExportParametrized:
    """Parametrized tests for various scenarios."""
    
    @pytest.mark.parametrize("export_format,expected_extension,expected_content_type", [
        ("markdown", ".md", "text/markdown"),
        ("pdf", ".pdf", "application/pdf"),
    ])
    @patch('app.routes.export.get_supabase_client')
    @patch('app.routes.export.fetch_notes_from_storage')
    @patch('app.routes.export.fetch_flashcards_from_db')
    @patch('app.routes.export.fetch_chat_history_from_db')
    @patch('app.routes.export.convert_markdown_to_pdf')
    @patch('app.core.auth.get_supabase_client')
    def test_export_both_formats(
        self,
        mock_auth_supabase,
        mock_pdf_converter,
        mock_chat_history,
        mock_flashcards,
        mock_notes,
        mock_supabase,
        client,
        sample_document,
        export_format,
        expected_extension,
        expected_content_type
    ):
        """Test both markdown and PDF formats."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock document fetch
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[sample_document])
        
        # Mock storage operations
        mock_storage = MagicMock()
        mock_storage.upload.return_value = None
        mock_storage.create_signed_url.return_value = {
            'signedURL': 'https://example.com/signed-url'
        }
        mock_client.storage.from_.return_value = mock_storage
        
        mock_supabase.return_value = mock_client
        
        # Mock data fetching
        mock_notes.return_value = None
        mock_flashcards.return_value = []
        mock_chat_history.return_value = []
        
        # Mock PDF conversion
        mock_pdf_converter.return_value = b"fake pdf"
        
        # Make request
        response = client.post(
            "/export",
            json={
                "document_id": sample_document["id"],
                "format": export_format
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["format"] == export_format
        assert data["filename"].endswith(expected_extension)
        
        # Verify content type in upload
        upload_args = mock_storage.upload.call_args
        assert upload_args[1]["file_options"]["content-type"] == expected_content_type
    
    @pytest.mark.parametrize("include_notes,include_flashcards,include_chat_history,expected_sections", [
        (True, True, True, ["metadata", "notes", "flashcards", "chat_history"]),
        (True, False, False, ["metadata", "notes"]),
        (False, True, False, ["metadata", "flashcards"]),
        (False, False, True, ["metadata", "chat_history"]),
        (False, False, False, ["metadata"]),
    ])
    @patch('app.routes.export.get_supabase_client')
    @patch('app.routes.export.fetch_notes_from_storage')
    @patch('app.routes.export.fetch_flashcards_from_db')
    @patch('app.routes.export.fetch_chat_history_from_db')
    @patch('app.core.auth.get_supabase_client')
    def test_export_various_section_combinations(
        self,
        mock_auth_supabase,
        mock_chat_history,
        mock_flashcards,
        mock_notes,
        mock_supabase,
        client,
        sample_document,
        sample_notes_markdown,
        sample_flashcards,
        sample_chat_history,
        include_notes,
        include_flashcards,
        include_chat_history,
        expected_sections
    ):
        """Test different combinations of include flags."""
        # Mock authentication
        mock_auth_client = MagicMock()
        mock_auth_client.auth.get_user.return_value.user.id = "test-user-id"
        mock_auth_supabase.return_value = mock_auth_client
        
        # Mock document fetch
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[sample_document])
        
        # Mock storage operations
        mock_storage = MagicMock()
        mock_storage.upload.return_value = None
        mock_storage.create_signed_url.return_value = {
            'signedURL': 'https://example.com/signed-url'
        }
        mock_client.storage.from_.return_value = mock_storage
        
        mock_supabase.return_value = mock_client
        
        # Mock data fetching based on include flags
        mock_notes.return_value = sample_notes_markdown if include_notes else None
        mock_flashcards.return_value = sample_flashcards if include_flashcards else []
        mock_chat_history.return_value = sample_chat_history if include_chat_history else []
        
        # Make request
        response = client.post(
            "/export",
            json={
                "document_id": sample_document["id"],
                "format": "markdown",
                "include_notes": include_notes,
                "include_flashcards": include_flashcards,
                "include_chat_history": include_chat_history
            },
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert set(data["included_sections"]) == set(expected_sections)
