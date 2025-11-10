"""
Unit tests for the /generate/notes endpoint (app.routes.generate).

Tests cover authentication, document ownership, text validation, Gemini note generation,
Supabase Storage upload, signed URL generation, idempotency, preview truncation, processing time,
and storage path format. External services are mocked.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import create_app
from app.core.auth import require_user


# Fixtures

@pytest.fixture
def client():
    """Return TestClient with require_user overridden for most tests."""
    app = create_app()
    app.dependency_overrides[require_user] = lambda: {"sub": "test-user-id", "role": "authenticated"}
    return TestClient(app)


@pytest.fixture
def mock_supabase():
    """Mock get_supabase_client inside generate route to avoid real DB/Storage calls."""
    with patch('app.routes.generate.get_supabase_client') as mock:
        yield mock


@pytest.fixture
def mock_generate_notes():
    """Mock generate_notes to avoid real Gemini calls."""
    with patch('app.routes.generate.generate_notes') as mock:
        yield mock


@pytest.fixture
def sample_document():
    return {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "user_id": "test-user-id",
        "filename": "example.pdf",
        "extracted_text": "This is the extracted text of the document.",
        "status": "extracted",
    }


@pytest.fixture
def sample_notes_markdown():
    return (
        "## Introduction\n\nThis document covers...\n\n"
        "## Key Points\n\n- Point 1\n- Point 2\n\n"
        "## Main Topics\n\n* Topic A\n* Topic B\n\n"
        "## Summary\n\nKey takeaways...\n"
    )


@pytest.fixture
def sample_signed_url():
    return "https://example.supabase.co/storage/v1/object/sign/processed/..."


# Test classes

class TestGenerateNotesEndpoint:
    def test_generate_notes_success(self, client, mock_supabase, mock_generate_notes, sample_document, sample_notes_markdown, sample_signed_url):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance

        # Document query returns the document
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{
                "extracted_text": sample_document["extracted_text"],
                "filename": sample_document["filename"],
                "status": sample_document["status"],
            }]
        )

        mock_generate_notes.return_value = sample_notes_markdown

        # Storage upload success
        mock_supabase_instance.storage.from_.return_value.upload.return_value = MagicMock()
        mock_supabase_instance.storage.from_.return_value.upload.return_value.error = None
        # Signed URL success
        mock_supabase_instance.storage.from_.return_value.create_signed_url.return_value = {"signedURL": sample_signed_url}

        response = client.post(f"/generate/notes?document_id={sample_document['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == sample_document["id"]
        assert data["filename"].endswith("-notes.md")
        assert data["storage_path"].startswith("processed/")
        assert sample_document["id"] in data["filename"] or sample_document["id"] in data["storage_path"]
        assert data["download_url"] == sample_signed_url
        assert data["status"] == "success"
        assert "processing_time_seconds" in data
        assert isinstance(data["processing_time_seconds"], (int, float))
        assert data["content_preview"].startswith("## Introduction")

    def test_generate_notes_processing_time_tracked(self, client, mock_supabase, mock_generate_notes, sample_document, sample_notes_markdown):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"extracted_text": sample_document["extracted_text"], "filename": sample_document["filename"], "status": sample_document["status"]}]
        )
        mock_generate_notes.return_value = sample_notes_markdown
        mock_supabase_instance.storage.from_.return_value.upload.return_value = MagicMock()
        mock_supabase_instance.storage.from_.return_value.upload.return_value.error = None
        mock_supabase_instance.storage.from_.return_value.create_signed_url.return_value = {"signedURL": "url"}

        response = client.post(f"/generate/notes?document_id={sample_document['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["processing_time_seconds"] >= 0

    def test_generate_notes_content_preview_truncation(self, client, mock_supabase, mock_generate_notes, sample_document):
        long_content = "# Title\n\n" + ("Lorem ipsum ") * 1000
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"extracted_text": sample_document["extracted_text"], "filename": sample_document["filename"], "status": sample_document["status"]}]
        )
        mock_generate_notes.return_value = long_content
        mock_supabase_instance.storage.from_.return_value.upload.return_value = MagicMock()
        mock_supabase_instance.storage.from_.return_value.upload.return_value.error = None
        mock_supabase_instance.storage.from_.return_value.create_signed_url.return_value = {"signedURL": "url"}

        response = client.post(f"/generate/notes?document_id={sample_document['id']}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["content_preview"]) == 500

    def test_generate_notes_storage_path_format(self, client, mock_supabase, mock_generate_notes, sample_document, sample_notes_markdown):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"extracted_text": sample_document["extracted_text"], "filename": sample_document["filename"], "status": sample_document["status"]}]
        )
        mock_generate_notes.return_value = sample_notes_markdown
        mock_supabase_instance.storage.from_.return_value.upload.return_value = MagicMock()
        mock_supabase_instance.storage.from_.return_value.upload.return_value.error = None
        mock_supabase_instance.storage.from_.return_value.create_signed_url.return_value = {"signedURL": "url"}

        response = client.post(f"/generate/notes?document_id={sample_document['id']}")
        assert response.status_code == 200
        # Capture call arguments to upload
        upload_call = mock_supabase_instance.storage.from_.return_value.upload
        args, kwargs = upload_call.call_args
        storage_path = kwargs.get('path') or (args[0] if args else None)
        assert storage_path is not None
        assert storage_path.startswith('processed/test-user-id/')
        assert storage_path.endswith('-notes.md')
        # Ensure document_id uniqueness baked into filename
        assert 'notes.md' in storage_path and sample_document['id'] in storage_path


class TestGenerateNotesAuthentication:
    def test_generate_notes_unauthorized(self, mock_supabase):
        app = create_app()
        client = TestClient(app)
        response = client.post("/generate/notes?document_id=123e4567-e89b-12d3-a456-426614174000")
        assert response.status_code == 401


class TestGenerateNotesErrorHandling:
    def test_generate_notes_document_not_found(self, client, mock_supabase):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        response = client.post("/generate/notes?document_id=123e4567-e89b-12d3-a456-426614174000")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_generate_notes_no_extracted_text(self, client, mock_supabase):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"extracted_text": " ", "filename": "file.pdf", "status": "uploaded"}]
        )
        response = client.post("/generate/notes?document_id=123e4567-e89b-12d3-a456-426614174000")
        assert response.status_code == 400
        assert "no extracted text" in response.json()["detail"].lower()

    def test_generate_notes_gemini_failure(self, client, mock_supabase, mock_generate_notes, sample_document):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"extracted_text": sample_document["extracted_text"], "filename": sample_document["filename"], "status": sample_document["status"]}]
        )
        mock_generate_notes.side_effect = RuntimeError("API error")
        response = client.post(f"/generate/notes?document_id={sample_document['id']}")
        assert response.status_code == 500
        assert "failed to generate notes" in response.json()["detail"].lower()

    def test_generate_notes_storage_upload_failure(self, client, mock_supabase, mock_generate_notes, sample_document, sample_notes_markdown):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"extracted_text": sample_document["extracted_text"], "filename": sample_document["filename"], "status": sample_document["status"]}]
        )
        mock_generate_notes.return_value = sample_notes_markdown
        mock_supabase_instance.storage.from_.return_value.upload.side_effect = Exception("upload failed")
        response = client.post(f"/generate/notes?document_id={sample_document['id']}")
        assert response.status_code == 500
        assert "failed to upload notes" in response.json()["detail"].lower()

    def test_generate_notes_signed_url_failure(self, client, mock_supabase, mock_generate_notes, sample_document, sample_notes_markdown):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"extracted_text": sample_document["extracted_text"], "filename": sample_document["filename"], "status": sample_document["status"]}]
        )
        mock_generate_notes.return_value = sample_notes_markdown
        mock_supabase_instance.storage.from_.return_value.upload.return_value = MagicMock()
        mock_supabase_instance.storage.from_.return_value.upload.return_value.error = None
        mock_supabase_instance.storage.from_.return_value.create_signed_url.side_effect = Exception("sign failed")
        response = client.post(f"/generate/notes?document_id={sample_document['id']}")
        assert response.status_code == 500
        assert "failed to generate download url" in response.json()["detail"].lower()

    def test_generate_notes_idempotent(self, client, mock_supabase, mock_generate_notes, sample_document, sample_notes_markdown):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"extracted_text": sample_document["extracted_text"], "filename": sample_document["filename"], "status": sample_document["status"]}]
        )
        mock_generate_notes.return_value = sample_notes_markdown
        mock_supabase_instance.storage.from_.return_value.upload.return_value = MagicMock()
        mock_supabase_instance.storage.from_.return_value.upload.return_value.error = None
        mock_supabase_instance.storage.from_.return_value.create_signed_url.return_value = {"signedURL": "url"}

        # Call twice
        r1 = client.post(f"/generate/notes?document_id={sample_document['id']}")
        r2 = client.post(f"/generate/notes?document_id={sample_document['id']}")
        assert r1.status_code == 200 and r2.status_code == 200
        # Verify upsert is string "true" (not boolean)
        upload_call = mock_supabase_instance.storage.from_.return_value.upload
        _, kwargs = upload_call.call_args
        assert kwargs.get('file_options', {}).get('upsert') == "true"

    def test_generate_notes_rate_limit(self, client, mock_supabase, mock_generate_notes, sample_document):
        """Gemini rate limit errors should map to HTTP 429."""
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"extracted_text": sample_document["extracted_text"], "filename": sample_document["filename"], "status": sample_document["status"]}]
        )
        mock_generate_notes.side_effect = RuntimeError("Rate limit exceeded: quota remaining 0")
        response = client.post(f"/generate/notes?document_id={sample_document['id']}")
        assert response.status_code == 429
        assert "rate" in response.json()["detail"].lower()


@pytest.mark.parametrize("size", [100, 1000, 10000])
def test_generate_notes_various_document_sizes(client, mock_supabase, mock_generate_notes, sample_document, size):
    text = "x" * size
    mock_supabase_instance = MagicMock()
    mock_supabase.return_value = mock_supabase_instance
    mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"extracted_text": text, "filename": sample_document["filename"], "status": sample_document["status"]}]
    )
    mock_generate_notes.return_value = "## Intro\n\n- a\n" * 10
    mock_supabase_instance.storage.from_.return_value.upload.return_value = MagicMock()
    mock_supabase_instance.storage.from_.return_value.upload.return_value.error = None
    mock_supabase_instance.storage.from_.return_value.create_signed_url.return_value = {"signedURL": "url"}

    response = client.post(f"/generate/notes?document_id={sample_document['id']}")
    assert response.status_code == 200
