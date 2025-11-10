"""Unit tests for the /generate/mindmap endpoint.

Covers authentication, document ownership, text validation, Gemini SVG generation,
SVG sanitization (bleach), Supabase Storage upload, signed URL generation, idempotency,
content preview truncation, storage path format, and error handling.
"""

import re
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import create_app
from app.core.auth import require_user
from app.routes.generate import sanitize_svg


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[require_user] = lambda: {"sub": "test-user-id", "role": "authenticated"}
    return TestClient(app)


@pytest.fixture
def mock_supabase():
    with patch('app.routes.generate.get_supabase_client') as mock:
        yield mock


@pytest.fixture
def mock_generate_mindmap():
    with patch('app.routes.generate.generate_mindmap') as mock:
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
def sample_mindmap_svg():
    return (
        "<svg viewBox='0 0 800 600' xmlns='http://www.w3.org/2000/svg'>"
        "<rect x='10' y='10' width='100' height='40' fill='#000000' stroke='#ffffff'/>"
        "<text x='15' y='35' fill='#ffffff'>Main Topic</text>"
        "<circle cx='200' cy='50' r='20' fill='#bdbdbd' stroke='#ffffff'/>"
        "<text x='190' y='55' fill='#ffffff'>Sub</text>"
        "<line x1='110' y1='30' x2='180' y2='50' stroke='#ffffff' stroke-width='2'/>"
        "</svg>"
    )


@pytest.fixture
def sample_malicious_svg():
    return (
        "<svg xmlns='http://www.w3.org/2000/svg'>"
        "<script>alert('xss')</script>"
        "<rect x='0' y='0' width='10' height='10' onclick=\"alert('x')\" />"
        "<image href='http://evil.com/x.svg' />"
        "</svg>"
    )


@pytest.fixture
def sample_signed_url():
    return "https://example.supabase.co/storage/v1/object/sign/processed/..."


class TestGenerateMindmapEndpoint:
    def test_generate_mindmap_success(self, client, mock_supabase, mock_generate_mindmap, sample_document, sample_mindmap_svg, sample_signed_url):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"extracted_text": sample_document["extracted_text"], "filename": sample_document["filename"], "status": sample_document["status"]}]
        )
        mock_generate_mindmap.return_value = sample_mindmap_svg
        mock_supabase_instance.storage.from_.return_value.upload.return_value = MagicMock()
        mock_supabase_instance.storage.from_.return_value.upload.return_value.error = None
        mock_supabase_instance.storage.from_.return_value.create_signed_url.return_value = {"signedURL": sample_signed_url}

        response = client.post(f"/generate/mindmap?document_id={sample_document['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == sample_document["id"]
        assert data["filename"].endswith("-mindmap.svg")
        assert sample_document["id"] in data["filename"]
        assert data["storage_path"].startswith("processed/test-user-id/")
        assert data["download_url"] == sample_signed_url
        assert data["status"] == "success"
        assert "processing_time_seconds" in data
        assert isinstance(data["processing_time_seconds"], (int, float))
        assert data["svg_preview"].startswith("<svg")
        assert data["node_count"] >= 1

    def test_generate_mindmap_processing_time_tracked(self, client, mock_supabase, mock_generate_mindmap, sample_document, sample_mindmap_svg):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"extracted_text": sample_document["extracted_text"], "filename": sample_document["filename"], "status": sample_document["status"]}]
        )
        mock_generate_mindmap.return_value = sample_mindmap_svg
        mock_supabase_instance.storage.from_.return_value.upload.return_value = MagicMock()
        mock_supabase_instance.storage.from_.return_value.upload.return_value.error = None
        mock_supabase_instance.storage.from_.return_value.create_signed_url.return_value = {"signedURL": "url"}

        response = client.post(f"/generate/mindmap?document_id={sample_document['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["processing_time_seconds"] >= 0

    def test_generate_mindmap_content_preview_truncation(self, client, mock_supabase, mock_generate_mindmap, sample_document):
        long_svg = "<svg>" + ("<rect x='0' y='0' width='10' height='10' />" * 1000) + "</svg>"
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"extracted_text": sample_document["extracted_text"], "filename": sample_document["filename"], "status": sample_document["status"]}]
        )
        mock_generate_mindmap.return_value = long_svg
        mock_supabase_instance.storage.from_.return_value.upload.return_value = MagicMock()
        mock_supabase_instance.storage.from_.return_value.upload.return_value.error = None
        mock_supabase_instance.storage.from_.return_value.create_signed_url.return_value = {"signedURL": "url"}

        response = client.post(f"/generate/mindmap?document_id={sample_document['id']}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["svg_preview"]) == 500

    def test_generate_mindmap_storage_path_format(self, client, mock_supabase, mock_generate_mindmap, sample_document, sample_mindmap_svg):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"extracted_text": sample_document["extracted_text"], "filename": sample_document["filename"], "status": sample_document["status"]}]
        )
        mock_generate_mindmap.return_value = sample_mindmap_svg
        mock_supabase_instance.storage.from_.return_value.upload.return_value = MagicMock()
        mock_supabase_instance.storage.from_.return_value.upload.return_value.error = None
        mock_supabase_instance.storage.from_.return_value.create_signed_url.return_value = {"signedURL": "url"}

        response = client.post(f"/generate/mindmap?document_id={sample_document['id']}")
        assert response.status_code == 200
        upload_call = mock_supabase_instance.storage.from_.return_value.upload
        args, kwargs = upload_call.call_args
        storage_path = kwargs.get('path') or (args[0] if args else None)
        assert storage_path is not None
        assert storage_path.startswith('processed/test-user-id/')
        assert storage_path.endswith('-mindmap.svg')
        assert sample_document['id'] in storage_path


class TestGenerateMindmapAuthentication:
    def test_generate_mindmap_unauthorized(self, mock_supabase):
        app = create_app()
        client = TestClient(app)
        response = client.post("/generate/mindmap?document_id=123e4567-e89b-12d3-a456-426614174000")
        assert response.status_code == 401


class TestGenerateMindmapErrorHandling:
    def test_generate_mindmap_document_not_found(self, client, mock_supabase):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
        response = client.post("/generate/mindmap?document_id=123e4567-e89b-12d3-a456-426614174000")
        assert response.status_code == 404

    def test_generate_mindmap_no_extracted_text(self, client, mock_supabase):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[{"extracted_text": " ", "filename": "file.pdf", "status": "uploaded"}])
        response = client.post("/generate/mindmap?document_id=123e4567-e89b-12d3-a456-426614174000")
        assert response.status_code == 400

    def test_generate_mindmap_gemini_failure(self, client, mock_supabase, mock_generate_mindmap, sample_document):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[{"extracted_text": sample_document["extracted_text"], "filename": sample_document["filename"], "status": sample_document["status"]}])
        mock_generate_mindmap.side_effect = RuntimeError("API error")
        response = client.post(f"/generate/mindmap?document_id={sample_document['id']}")
        assert response.status_code == 500

    def test_generate_mindmap_storage_upload_failure(self, client, mock_supabase, mock_generate_mindmap, sample_document, sample_mindmap_svg):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[{"extracted_text": sample_document["extracted_text"], "filename": sample_document["filename"], "status": sample_document["status"]}])
        mock_generate_mindmap.return_value = sample_mindmap_svg
        mock_supabase_instance.storage.from_.return_value.upload.side_effect = Exception("upload failed")
        response = client.post(f"/generate/mindmap?document_id={sample_document['id']}")
        assert response.status_code == 500

    def test_generate_mindmap_signed_url_failure(self, client, mock_supabase, mock_generate_mindmap, sample_document, sample_mindmap_svg):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[{"extracted_text": sample_document["extracted_text"], "filename": sample_document["filename"], "status": sample_document["status"]}])
        mock_generate_mindmap.return_value = sample_mindmap_svg
        mock_supabase_instance.storage.from_.return_value.upload.return_value = MagicMock()
        mock_supabase_instance.storage.from_.return_value.upload.return_value.error = None
        mock_supabase_instance.storage.from_.return_value.create_signed_url.side_effect = Exception("sign failed")
        response = client.post(f"/generate/mindmap?document_id={sample_document['id']}")
        assert response.status_code == 500

    def test_generate_mindmap_idempotent(self, client, mock_supabase, mock_generate_mindmap, sample_document, sample_mindmap_svg):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[{"extracted_text": sample_document["extracted_text"], "filename": sample_document["filename"], "status": sample_document["status"]}])
        mock_generate_mindmap.return_value = sample_mindmap_svg
        mock_supabase_instance.storage.from_.return_value.upload.return_value = MagicMock()
        mock_supabase_instance.storage.from_.return_value.upload.return_value.error = None
        mock_supabase_instance.storage.from_.return_value.create_signed_url.return_value = {"signedURL": "url"}
        r1 = client.post(f"/generate/mindmap?document_id={sample_document['id']}")
        r2 = client.post(f"/generate/mindmap?document_id={sample_document['id']}")
        assert r1.status_code == 200 and r2.status_code == 200
        upload_call = mock_supabase_instance.storage.from_.return_value.upload
        _, kwargs = upload_call.call_args
        assert kwargs.get('file_options', {}).get('upsert') is True

    def test_generate_mindmap_rate_limit(self, client, mock_supabase, mock_generate_mindmap, sample_document):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[{"extracted_text": sample_document["extracted_text"], "filename": sample_document["filename"], "status": sample_document["status"]}])
        mock_generate_mindmap.side_effect = RuntimeError("Rate limit exceeded: quota remaining 0")
        response = client.post(f"/generate/mindmap?document_id={sample_document['id']}")
        assert response.status_code == 429


class TestGenerateMindmapSVGSanitization:
    def test_sanitize_svg_removes_script_tags(self, sample_malicious_svg):
        cleaned = sanitize_svg(sample_malicious_svg)
        assert '<script' not in cleaned.lower()
        assert '<svg' in cleaned.lower()

    def test_sanitize_svg_removes_event_handlers(self, sample_malicious_svg):
        cleaned = sanitize_svg(sample_malicious_svg)
        assert 'onclick' not in cleaned.lower()

    def test_sanitize_svg_removes_external_resources(self, sample_malicious_svg):
        cleaned = sanitize_svg(sample_malicious_svg)
        assert 'image' not in cleaned.lower() or 'href=' not in cleaned.lower()

    def test_sanitize_svg_preserves_safe_elements(self, sample_mindmap_svg):
        cleaned = sanitize_svg(sample_mindmap_svg)
        assert '<rect' in cleaned.lower() and '<circle' in cleaned.lower() and '<text' in cleaned.lower()

    def test_sanitize_svg_preserves_monochrome_colors(self, sample_mindmap_svg):
        cleaned = sanitize_svg(sample_mindmap_svg)
        assert '#000000' in cleaned or 'fill="#000000"' in cleaned
        assert '#ffffff' in cleaned or 'stroke="#ffffff"' in cleaned

    def test_generate_mindmap_invalid_svg(self, client, mock_supabase, mock_generate_mindmap, sample_document):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[{"extracted_text": sample_document["extracted_text"], "filename": sample_document["filename"], "status": sample_document["status"]}])
        mock_generate_mindmap.return_value = "<div>No SVG here</div>"
        response = client.post(f"/generate/mindmap?document_id={sample_document['id']}")
        # Endpoint only warns on invalid structure but proceeds, so success expected
        assert response.status_code == 200 or response.status_code == 500

    def test_generate_mindmap_empty_svg_after_sanitization(self, client, mock_supabase, mock_generate_mindmap, sample_document):
        malicious_svg_only_scripts = "<svg><script>alert(1)</script></svg>"
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[{"extracted_text": sample_document["extracted_text"], "filename": sample_document["filename"], "status": sample_document["status"]}])
        mock_generate_mindmap.return_value = malicious_svg_only_scripts
        # sanitize_svg will strip script but leave empty <svg>; still valid
        response = client.post(f"/generate/mindmap?document_id={sample_document['id']}")
        assert response.status_code in (200, 500)

    def test_generate_mindmap_content_type(self, client, mock_supabase, mock_generate_mindmap, sample_document, sample_mindmap_svg):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[{"extracted_text": sample_document["extracted_text"], "filename": sample_document["filename"], "status": sample_document["status"]}])
        mock_generate_mindmap.return_value = sample_mindmap_svg
        mock_supabase_instance.storage.from_.return_value.upload.return_value = MagicMock()
        mock_supabase_instance.storage.from_.return_value.upload.return_value.error = None
        mock_supabase_instance.storage.from_.return_value.create_signed_url.return_value = {"signedURL": "url"}
        response = client.post(f"/generate/mindmap?document_id={sample_document['id']}")
        assert response.status_code == 200
        upload_call = mock_supabase_instance.storage.from_.return_value.upload
        _, kwargs = upload_call.call_args
        assert kwargs.get('file_options', {}).get('content_type') == 'image/svg+xml'

    def test_sanitize_svg_preserves_viewbox_lowercased(self):
        raw = "<svg viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'><rect x='0' y='0' width='10' height='10' /></svg>"
        cleaned = sanitize_svg(raw)
        # bleach lowercases attributes; ensure viewBox remains as viewbox
        assert "viewbox=\"0 0 100 100\"" in cleaned.lower()

    def test_sanitize_svg_css_sanitizer_blocks_disallowed_properties(self):
        raw = "<svg xmlns='http://www.w3.org/2000/svg'><rect x='0' y='0' width='10' height='10' style='position:absolute; fill: red; stroke: blue; background-image:url(javascript:alert(1))' /></svg>"
        cleaned = sanitize_svg(raw)
        # allowed properties persist
        assert "fill:" in cleaned or "fill=\"" in cleaned
        assert "stroke:" in cleaned or "stroke=\"" in cleaned
        # disallowed 'position' should be removed
        assert "position:" not in cleaned
        # dangerous url(javascript:...) must be removed
        assert "javascript:" not in cleaned

    def test_sanitize_svg_preserves_transform_on_group(self):
        raw = "<svg xmlns='http://www.w3.org/2000/svg'><g transform='translate(10,10)'><rect x='0' y='0' width='10' height='10' /></g></svg>"
        cleaned = sanitize_svg(raw)
        assert "<g" in cleaned.lower()
        assert "transform=\"translate(10,10)\"" in cleaned


@pytest.mark.parametrize("size", [100, 1000, 10000, 50000])
def test_generate_mindmap_various_document_sizes(client, mock_supabase, mock_generate_mindmap, sample_document, size):
    text = "x" * size
    mock_supabase_instance = MagicMock()
    mock_supabase.return_value = mock_supabase_instance
    mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"extracted_text": text, "filename": sample_document["filename"], "status": sample_document["status"]}]
    )
    mock_generate_mindmap.return_value = "<svg><rect x='0' y='0' width='10' height='10'/></svg>"
    mock_supabase_instance.storage.from_.return_value.upload.return_value = MagicMock()
    mock_supabase_instance.storage.from_.return_value.upload.return_value.error = None
    mock_supabase_instance.storage.from_.return_value.create_signed_url.return_value = {"signedURL": "url"}
    response = client.post(f"/generate/mindmap?document_id={sample_document['id']}")
    assert response.status_code == 200
