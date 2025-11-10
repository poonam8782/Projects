"""
Unit tests for the /flashcards/review endpoint (app.routes.flashcards).

Tests cover authentication, flashcard ownership, SM-2 calculation integration,
database update, next flashcard retrieval, and error handling.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import create_app
from app.core.auth import require_user
from app.utils.sm2 import SM2Result


# Fixtures

@pytest.fixture
def client():
    """Return TestClient with require_user overridden for most tests."""
    app = create_app()
    app.dependency_overrides[require_user] = lambda: {"sub": "test-user-id", "role": "authenticated"}
    return TestClient(app)


@pytest.fixture
def mock_supabase():
    """Mock get_supabase_client inside flashcards route to avoid real DB calls."""
    with patch('app.routes.flashcards.get_supabase_client') as mock:
        yield mock


@pytest.fixture
def mock_calculate_sm2():
    """Mock calculate_sm2 to return predictable SM2Result."""
    with patch('app.routes.flashcards.calculate_sm2') as mock:
        yield mock


@pytest.fixture
def sample_flashcard():
    return {
        "id": "fc-uuid-1",
        "user_id": "test-user-id",
        "document_id": "doc-uuid-1",
        "question": "What is Q1?",
        "answer": "A1",
        "efactor": 2.5,
        "repetitions": 0,
        "interval": 1,
        "next_review": "2024-01-15T10:00:00Z",
        "last_reviewed": None,
        "created_at": "2024-01-15T10:00:00Z",
    }


@pytest.fixture
def sample_sm2_result():
    return SM2Result(
        efactor=2.6,
        repetitions=1,
        interval=1,
        next_review=datetime(2024, 1, 16, 10, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_next_flashcard():
    return {
        "id": "fc-uuid-2",
        "user_id": "test-user-id",
        "document_id": "doc-uuid-1",
        "question": "What is Q2?",
        "answer": "A2",
        "efactor": 2.5,
        "repetitions": 0,
        "interval": 1,
        "next_review": "2024-01-15T09:00:00Z",
        "last_reviewed": None,
        "created_at": "2024-01-15T09:00:00Z",
    }


# Test classes

class TestReviewFlashcardEndpoint:
    def test_review_flashcard_success(self, client, mock_supabase, mock_calculate_sm2, sample_flashcard, sample_sm2_result, sample_next_flashcard):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance

        # Flashcard query returns the flashcard
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[sample_flashcard]
        )

        mock_calculate_sm2.return_value = sample_sm2_result

        # Update success
        updated_flashcard = {**sample_flashcard, "efactor": 2.6, "repetitions": 1, "interval": 1, "next_review": "2024-01-16T10:00:00Z", "last_reviewed": "2024-01-15T10:30:00Z"}
        mock_supabase_instance.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[updated_flashcard]
        )

        # Next flashcard query
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.lte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[sample_next_flashcard]
        )

        # Due count query
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.lte.return_value.execute.return_value = MagicMock(
            count=5
        )

        response = client.post("/flashcards/review", json={"flashcard_id": "fc-uuid-1", "quality": 4})
        assert response.status_code == 200
        data = response.json()
        assert data["reviewed_flashcard"]["efactor"] == 2.6
        assert data["reviewed_flashcard"]["repetitions"] == 1
        assert data["reviewed_flashcard"]["interval"] == 1
        assert data["next_flashcard"] is not None
        assert data["due_count"] == 5
        assert "1 day" in data["message"]

    def test_review_flashcard_unauthorized(self, client):
        app = create_app()
        # No auth override
        test_client = TestClient(app)
        response = test_client.post("/flashcards/review", json={"flashcard_id": "fc-uuid-1", "quality": 4})
        assert response.status_code == 401

    def test_review_flashcard_not_found(self, client, mock_supabase):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance

        # Flashcard query returns empty
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        response = client.post("/flashcards/review", json={"flashcard_id": "fc-uuid-1", "quality": 4})
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_review_flashcard_not_owned(self, client, mock_supabase):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance

        # Flashcard query returns empty (flashcard belongs to different user)
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        response = client.post("/flashcards/review", json={"flashcard_id": "fc-uuid-1", "quality": 4})
        assert response.status_code == 404
        assert "access denied" in response.json()["detail"].lower()

    def test_review_flashcard_invalid_quality(self, client):
        # Quality -1 (below min)
        response = client.post("/flashcards/review", json={"flashcard_id": "fc-uuid-1", "quality": -1})
        assert response.status_code == 422

        # Quality 6 (above max)
        response = client.post("/flashcards/review", json={"flashcard_id": "fc-uuid-1", "quality": 6})
        assert response.status_code == 422


class TestReviewFlashcardSM2Integration:
    def test_review_flashcard_sm2_calculation(self, client, mock_supabase, mock_calculate_sm2, sample_flashcard, sample_sm2_result):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance

        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[sample_flashcard]
        )

        mock_calculate_sm2.return_value = sample_sm2_result

        updated_flashcard = {**sample_flashcard, "efactor": 2.6, "repetitions": 1, "interval": 1}
        mock_supabase_instance.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[updated_flashcard]
        )

        # Mock next flashcard and count to avoid errors
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.lte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.lte.return_value.execute.return_value = MagicMock(
            count=0
        )

        response = client.post("/flashcards/review", json={"flashcard_id": "fc-uuid-1", "quality": 4})
        assert response.status_code == 200

        # Verify calculate_sm2 called with correct parameters
        mock_calculate_sm2.assert_called_once_with(
            quality=4,
            current_efactor=sample_flashcard["efactor"],
            current_repetitions=sample_flashcard["repetitions"],
            current_interval=sample_flashcard["interval"],
        )

    def test_review_flashcard_database_update(self, client, mock_supabase, mock_calculate_sm2, sample_flashcard, sample_sm2_result):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance

        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[sample_flashcard]
        )

        mock_calculate_sm2.return_value = sample_sm2_result

        update_dict_captured = None

        def capture_update(update_dict):
            nonlocal update_dict_captured
            update_dict_captured = update_dict
            return MagicMock(
                eq=lambda *args: MagicMock(
                    eq=lambda *args: MagicMock(
                        execute=lambda: MagicMock(data=[{**sample_flashcard, **update_dict}])
                    )
                )
            )

        mock_supabase_instance.table.return_value.update.side_effect = capture_update

        # Mock next flashcard and count to avoid errors
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.lte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.lte.return_value.execute.return_value = MagicMock(
            count=0
        )

        response = client.post("/flashcards/review", json={"flashcard_id": "fc-uuid-1", "quality": 4})
        assert response.status_code == 200

        # Verify database updated with SM2Result values
        assert update_dict_captured is not None
        assert update_dict_captured["efactor"] == sample_sm2_result.efactor
        assert update_dict_captured["repetitions"] == sample_sm2_result.repetitions
        assert update_dict_captured["interval"] == sample_sm2_result.interval
        assert "next_review" in update_dict_captured
        assert "last_reviewed" in update_dict_captured

    def test_review_flashcard_no_next_due(self, client, mock_supabase, mock_calculate_sm2, sample_flashcard, sample_sm2_result):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance

        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[sample_flashcard]
        )

        mock_calculate_sm2.return_value = sample_sm2_result

        updated_flashcard = {**sample_flashcard, "efactor": 2.6, "repetitions": 1, "interval": 1}
        mock_supabase_instance.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[updated_flashcard]
        )

        # Next flashcard query returns empty
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.lte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        # Due count query
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.lte.return_value.execute.return_value = MagicMock(
            count=0
        )

        response = client.post("/flashcards/review", json={"flashcard_id": "fc-uuid-1", "quality": 4})
        assert response.status_code == 200
        data = response.json()
        assert data["next_flashcard"] is None
        assert "no more flashcards due" in data["message"].lower()

    def test_review_flashcard_due_count(self, client, mock_supabase, mock_calculate_sm2, sample_flashcard, sample_sm2_result):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance

        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[sample_flashcard]
        )

        mock_calculate_sm2.return_value = sample_sm2_result

        updated_flashcard = {**sample_flashcard, "efactor": 2.6, "repetitions": 1, "interval": 1}
        mock_supabase_instance.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[updated_flashcard]
        )

        # Next flashcard query
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.lte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        # Due count query returns 5
        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.lte.return_value.execute.return_value = MagicMock(
            count=5
        )

        response = client.post("/flashcards/review", json={"flashcard_id": "fc-uuid-1", "quality": 4})
        assert response.status_code == 200
        data = response.json()
        assert data["due_count"] == 5

    def test_review_flashcard_update_failure(self, client, mock_supabase, mock_calculate_sm2, sample_flashcard, sample_sm2_result):
        mock_supabase_instance = MagicMock()
        mock_supabase.return_value = mock_supabase_instance

        mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[sample_flashcard]
        )

        mock_calculate_sm2.return_value = sample_sm2_result

        # Update fails
        mock_supabase_instance.table.return_value.update.side_effect = Exception("Database error")

        response = client.post("/flashcards/review", json={"flashcard_id": "fc-uuid-1", "quality": 4})
        assert response.status_code == 500
        assert "failed to update flashcard" in response.json()["detail"].lower()


@pytest.mark.parametrize("quality", [0, 1, 2, 3, 4, 5])
def test_review_flashcard_all_quality_ratings(client, mock_supabase, mock_calculate_sm2, sample_flashcard, quality):
    mock_supabase_instance = MagicMock()
    mock_supabase.return_value = mock_supabase_instance

    mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[sample_flashcard]
    )

    # SM-2 result varies by quality
    if quality < 3:
        sm2_result = SM2Result(efactor=2.4, repetitions=0, interval=1, next_review=datetime(2024, 1, 16, 10, 0, 0, tzinfo=timezone.utc))
    else:
        sm2_result = SM2Result(efactor=2.6, repetitions=1, interval=1, next_review=datetime(2024, 1, 16, 10, 0, 0, tzinfo=timezone.utc))

    mock_calculate_sm2.return_value = sm2_result

    updated_flashcard = {**sample_flashcard, "efactor": sm2_result.efactor, "repetitions": sm2_result.repetitions, "interval": sm2_result.interval}
    mock_supabase_instance.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[updated_flashcard]
    )

    # Mock next flashcard and count to avoid errors
    mock_supabase_instance.table.return_value.select.return_value.eq.return_value.lte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )
    mock_supabase_instance.table.return_value.select.return_value.eq.return_value.lte.return_value.execute.return_value = MagicMock(
        count=0
    )

    response = client.post("/flashcards/review", json={"flashcard_id": "fc-uuid-1", "quality": quality})
    assert response.status_code == 200

    # Verify SM-2 calculation called with correct quality
    mock_calculate_sm2.assert_called_once()
    assert mock_calculate_sm2.call_args.kwargs.get("quality") == quality


@pytest.mark.parametrize("interval,expected_desc", [
    (1, "1 day"),
    (6, "6 days"),
    (14, "2 weeks"),
    (30, "1 month"),
])
def test_review_flashcard_interval_descriptions(client, mock_supabase, mock_calculate_sm2, sample_flashcard, interval, expected_desc):
    mock_supabase_instance = MagicMock()
    mock_supabase.return_value = mock_supabase_instance

    mock_supabase_instance.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[sample_flashcard]
    )

    sm2_result = SM2Result(efactor=2.5, repetitions=1, interval=interval, next_review=datetime(2024, 1, 16, 10, 0, 0, tzinfo=timezone.utc))
    mock_calculate_sm2.return_value = sm2_result

    updated_flashcard = {**sample_flashcard, "efactor": 2.5, "repetitions": 1, "interval": interval}
    mock_supabase_instance.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[updated_flashcard]
    )

    # Mock next flashcard exists
    next_flashcard = {**sample_flashcard, "id": "fc-uuid-2"}
    mock_supabase_instance.table.return_value.select.return_value.eq.return_value.lte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[next_flashcard]
    )

    mock_supabase_instance.table.return_value.select.return_value.eq.return_value.lte.return_value.execute.return_value = MagicMock(
        count=1
    )

    response = client.post("/flashcards/review", json={"flashcard_id": "fc-uuid-1", "quality": 4})
    assert response.status_code == 200
    data = response.json()
    assert expected_desc in data["message"].lower()
