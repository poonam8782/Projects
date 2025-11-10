"""
Unit tests for the /generate/flashcards endpoint (app.routes.generate).

Tests cover authentication, document ownership, text validation, Gemini JSON generation,
JSON parsing and validation, database batch insertion with SM-2 initial values,
and error handling.
"""

import json
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
    """Mock get_supabase_client inside generate route to avoid real DB calls."""
    with patch('app.routes.generate.get_supabase_client') as mock:
        yield mock


@pytest.fixture
def mock_generate_flashcards():
    """Mock generate_flashcards to avoid real Gemini calls."""
    with patch('app.routes.generate.generate_flashcards') as mock:
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
def sample_flashcards_json():
    return json.dumps({
        "flashcards": [
            {"question": "What is Q1?", "answer": "A1"},
            {"question": "What is Q2?", "answer": "A2"},
        ]
    })


@pytest.fixture
def sample_flashcard_records():
    return [
        {
            "id": "fc-uuid-1",
            "user_id": "test-user-id",
            "document_id": "123e4567-e89b-12d3-a456-426614174000",
            "question": "What is Q1?",
            "answer": "A1",
            "efactor": 2.5,
            "repetitions": 0,
            "interval": 1,
            "next_review": "2024-01-15T10:00:00Z",
            "last_reviewed": None,
            "created_at": "2024-01-15T10:00:00Z",
        },
        {
            "id": "fc-uuid-2",
            "user_id": "test-user-id",
            "document_id": "123e4567-e89b-12d3-a456-426614174000",
            "question": "What is Q2?",
            "answer": "A2",
            "efactor": 2.5,
            "repetitions": 0,
            "interval": 1,
            "next_review": "2024-01-15T10:00:00Z",
            "last_reviewed": None,
            "created_at": "2024-01-15T10:00:00Z",
        },
    ]


# Test classes

class TestGenerateFlashcardsEndpoint:
    def test_generate_flashcards_success(self, client, mock_supabase, mock_generate_flashcards, sample_document, sample_flashcards_json, sample_flashcard_records):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance

        # Document query returns the document
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{
                "extracted_text": sample_document["extracted_text"],
                "filename": sample_document["filename"],
            }]
        )

        mock_generate_flashcards.return_value = sample_flashcards_json

        # Database insert success
        mock_supabase_instance.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=sample_flashcard_records
        )

        response = client.post(f"/generate/flashcards?document_id={sample_document['id']}&target_count=10")
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == sample_document["id"]
        assert data["flashcard_count"] == 2
        assert len(data["flashcards"]) == 2
        assert data["status"] == "success"
        assert "processing_time_seconds" in data
        # Verify SM-2 initial values
        for fc in data["flashcards"]:
            assert fc["efactor"] == 2.5
            assert fc["repetitions"] == 0
            assert fc["interval"] == 1

    def test_generate_flashcards_unauthorized(self, client, mock_supabase):
        app = create_app()
        # No auth override
        test_client = TestClient(app)
        response = test_client.post("/generate/flashcards?document_id=123e4567-e89b-12d3-a456-426614174000")
        assert response.status_code == 401

    def test_generate_flashcards_document_not_found(self, client, mock_supabase):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance

        # Document query returns empty
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        response = client.post("/generate/flashcards?document_id=123e4567-e89b-12d3-a456-426614174000")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_generate_flashcards_no_extracted_text(self, client, mock_supabase):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance

        # Document query returns document without text
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{
                "extracted_text": None,
                "filename": "example.pdf",
            }]
        )

        response = client.post("/generate/flashcards?document_id=123e4567-e89b-12d3-a456-426614174000")
        assert response.status_code == 400
        assert "no extracted text" in response.json()["detail"].lower()

    def test_generate_flashcards_gemini_failure(self, client, mock_supabase, mock_generate_flashcards, sample_document):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance

        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{
                "extracted_text": sample_document["extracted_text"],
                "filename": sample_document["filename"],
            }]
        )

        mock_generate_flashcards.side_effect = RuntimeError("Gemini API error")

        response = client.post(f"/generate/flashcards?document_id={sample_document['id']}")
        assert response.status_code == 500


class TestGenerateFlashcardsJSONParsing:
    def test_generate_flashcards_invalid_json(self, client, mock_supabase, mock_generate_flashcards, sample_document):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance

        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{
                "extracted_text": sample_document["extracted_text"],
                "filename": sample_document["filename"],
            }]
        )

        mock_generate_flashcards.return_value = "not valid json"

        response = client.post(f"/generate/flashcards?document_id={sample_document['id']}")
        assert response.status_code == 500
        assert "invalid json" in response.json()["detail"].lower()

    def test_generate_flashcards_missing_flashcards_key(self, client, mock_supabase, mock_generate_flashcards, sample_document):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance

        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{
                "extracted_text": sample_document["extracted_text"],
                "filename": sample_document["filename"],
            }]
        )

        mock_generate_flashcards.return_value = json.dumps({"data": []})

        response = client.post(f"/generate/flashcards?document_id={sample_document['id']}")
        assert response.status_code == 500
        assert "invalid" in response.json()["detail"].lower()

    def test_generate_flashcards_empty_flashcards_list(self, client, mock_supabase, mock_generate_flashcards, sample_document):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance

        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{
                "extracted_text": sample_document["extracted_text"],
                "filename": sample_document["filename"],
            }]
        )

        mock_generate_flashcards.return_value = json.dumps({"flashcards": []})

        response = client.post(f"/generate/flashcards?document_id={sample_document['id']}")
        assert response.status_code == 500
        assert "no flashcards" in response.json()["detail"].lower()

    def test_generate_flashcards_missing_question_field(self, client, mock_supabase, mock_generate_flashcards, sample_document):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance

        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{
                "extracted_text": sample_document["extracted_text"],
                "filename": sample_document["filename"],
            }]
        )

        mock_generate_flashcards.return_value = json.dumps({"flashcards": [{"answer": "A1"}]})

        response = client.post(f"/generate/flashcards?document_id={sample_document['id']}")
        assert response.status_code == 500
        assert "invalid" in response.json()["detail"].lower()


class TestGenerateFlashcardsDatabase:
    def test_generate_flashcards_sm2_initial_values(self, client, mock_supabase, mock_generate_flashcards, sample_document, sample_flashcards_json, sample_flashcard_records):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance

        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{
                "extracted_text": sample_document["extracted_text"],
                "filename": sample_document["filename"],
            }]
        )

        mock_generate_flashcards.return_value = sample_flashcards_json

        inserted_records = []

        def capture_insert(records):
            inserted_records.extend(records)
            # Return full records with id, created_at, and all required fields
            full_records = [
                {
                    **record,
                    "id": f"fc-uuid-{i}",
                    "created_at": "2024-01-15T10:00:00Z",
                    "last_reviewed": None,
                }
                for i, record in enumerate(records, start=1)
            ]
            return MagicMock(execute=lambda: MagicMock(data=full_records))

        mock_supabase_instance.table.return_value.insert.side_effect = capture_insert

        response = client.post(f"/generate/flashcards?document_id={sample_document['id']}")
        assert response.status_code == 200

        # Verify all records have SM-2 initial values
        assert len(inserted_records) == 2
        for record in inserted_records:
            assert record["efactor"] == 2.5
            assert record["repetitions"] == 0
            assert record["interval"] == 1
            assert "next_review" in record

    def test_generate_flashcards_batch_insert(self, client, mock_supabase, mock_generate_flashcards, sample_document, sample_flashcards_json, sample_flashcard_records):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance

        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{
                "extracted_text": sample_document["extracted_text"],
                "filename": sample_document["filename"],
            }]
        )

        mock_generate_flashcards.return_value = sample_flashcards_json

        insert_call_count = 0

        def count_insert_calls(records):
            nonlocal insert_call_count
            insert_call_count += 1
            # Return full records with id, created_at, and all required fields
            full_records = [
                {
                    **record,
                    "id": f"fc-uuid-{i}",
                    "created_at": "2024-01-15T10:00:00Z",
                    "last_reviewed": None,
                }
                for i, record in enumerate(records, start=1)
            ]
            return MagicMock(execute=lambda: MagicMock(data=full_records))

        mock_supabase_instance.table.return_value.insert.side_effect = count_insert_calls

        response = client.post(f"/generate/flashcards?document_id={sample_document['id']}")
        assert response.status_code == 200
        # Verify insert called exactly once (batch insert)
        assert insert_call_count == 1

    def test_generate_flashcards_database_insert_failure(self, client, mock_supabase, mock_generate_flashcards, sample_document, sample_flashcards_json):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance

        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{
                "extracted_text": sample_document["extracted_text"],
                "filename": sample_document["filename"],
            }]
        )

        mock_generate_flashcards.return_value = sample_flashcards_json

        mock_supabase_instance.table.return_value.insert.side_effect = Exception("Database error")

        response = client.post(f"/generate/flashcards?document_id={sample_document['id']}")
        assert response.status_code == 500
        assert "failed to save" in response.json()["detail"].lower()


@pytest.mark.parametrize("target_count", [5, 10, 20, 50])
def test_generate_flashcards_various_target_counts(client, mock_supabase, mock_generate_flashcards, sample_document, target_count):
    mock_supabase_instance = MagicMock()
    mock_supabase.return_value = mock_supabase_instance

    mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{
            "extracted_text": sample_document["extracted_text"],
            "filename": sample_document["filename"],
        }]
    )

    # Generate JSON with requested count
    flashcards_list = [{"question": f"Q{i}", "answer": f"A{i}"} for i in range(target_count)]
    mock_generate_flashcards.return_value = json.dumps({"flashcards": flashcards_list})

    mock_supabase_instance.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": f"fc-{i}", **fc, "efactor": 2.5, "repetitions": 0, "interval": 1, "next_review": "2024-01-15T10:00:00Z", "last_reviewed": None, "created_at": "2024-01-15T10:00:00Z", "user_id": "test-user-id", "document_id": sample_document["id"]} for i, fc in enumerate(flashcards_list)]
    )

    response = client.post(f"/generate/flashcards?document_id={sample_document['id']}&target_count={target_count}")
    assert response.status_code == 200
    # Verify Gemini called with correct target_count
    mock_generate_flashcards.assert_called_once()
    assert mock_generate_flashcards.call_args.kwargs.get("target_count") == target_count
