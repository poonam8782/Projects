"""Unit tests for the /chat endpoint (app.routes.chat).

This suite validates authentication, document ownership, embedding status checks,
query embedding, similarity search orchestration, context assembly, conversation
history management, SSE event streaming, and error handling for the RAG chat flow.
"""

from __future__ import annotations

import json
from typing import Iterable, List
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.auth import require_user
from app.main import create_app
from app.schemas import ChatMessage


def create_test_client() -> TestClient:
    app = create_app()
    app.dependency_overrides[require_user] = lambda: {
        "sub": "test-user-id",
        "role": "authenticated",
    }
    return TestClient(app)


def configure_document_lookup(supabase: MagicMock, status: str = "embedded") -> None:
    table_mock = MagicMock()
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.execute.return_value = MagicMock(data=[{"status": status}])
    supabase.table.return_value = table_mock


def configure_rpc_matches(supabase: MagicMock, matches: List[dict]) -> None:
    rpc_mock = MagicMock()
    rpc_mock.execute.return_value = MagicMock(data=matches)
    supabase.rpc.return_value = rpc_mock


def parse_sse_stream(chunks: Iterable[str]) -> List[dict]:
    buffer = "".join(chunks)
    events: List[dict] = []
    for block in filter(None, buffer.split("\n\n")):
        event_type = None
        data_payload = None
        for line in block.split("\n"):
            if line.startswith(":"):  # heartbeat/ping comments
                continue
            if line.startswith("event:"):
                event_type = line[len("event:") :].strip()
            elif line.startswith("data:"):
                json_payload = line[len("data:") :].strip()
                data_payload = json.loads(json_payload) if json_payload else None
        if event_type:
            events.append({"event": event_type, "data": data_payload})
    return events


@pytest.fixture
def client() -> TestClient:
    return create_test_client()


@pytest.fixture
def supabase_mock():
    with patch("app.routes.chat.get_supabase_client") as mock_get_client:
        supabase_instance = MagicMock()
        mock_get_client.return_value = supabase_instance
        yield supabase_instance


@pytest.fixture
def mock_generate_embedding():
    with patch("app.routes.chat.generate_embedding") as mock:
        mock.return_value = [0.1] * 768
        yield mock


@pytest.fixture
def mock_stream_chat_response():
    with patch("app.routes.chat.stream_chat_response") as mock:
        mock.return_value = iter(["Hello", " world", "!"])
        yield mock


@pytest.fixture(autouse=True)
def mock_count_tokens():
    with patch("app.routes.chat.count_tokens") as mock:
        mock.side_effect = lambda text, encoding_name="cl100k_base": len(text)
        yield mock


@pytest.fixture
def sample_chunks() -> List[dict]:
    return [
        {
            "id": 1,
            "document_id": "doc-123",
            "chunk_index": 0,
            "chunk_text": "Alpha chunk",
            "similarity": 0.92,
        },
        {
            "id": 2,
            "document_id": "doc-123",
            "chunk_index": 1,
            "chunk_text": "Beta chunk",
            "similarity": 0.87,
        },
        {
            "id": 3,
            "document_id": "doc-123",
            "chunk_index": 2,
            "chunk_text": "Gamma chunk",
            "similarity": 0.81,
        },
    ]


@pytest.fixture
def sample_history() -> List[ChatMessage]:
    return [
        ChatMessage(role="user", content="Hi"),
        ChatMessage(role="model", content="Hello there"),
    ]


class TestChatEndpoint:
    def test_chat_success(
        self,
        client: TestClient,
        supabase_mock: MagicMock,
        mock_generate_embedding,
        mock_stream_chat_response,
        sample_chunks,
    ) -> None:
        configure_document_lookup(supabase_mock)
        configure_rpc_matches(supabase_mock, sample_chunks)

        payload = {
            "document_id": "123e4567-e89b-12d3-a456-426614174000",
            "query": "Summarize the content",
            "history": [],
        }

        with client.stream("POST", "/chat", json=payload) as response:
            assert response.status_code == 200
            events = parse_sse_stream(response.iter_text())

        assert events[0]["event"] == "provenance"
        assert len(events[0]["data"]["chunks"]) == 3
        token_events = [event for event in events if event["event"] == "token"]
        assert len(token_events) == 3
        assert events[-1]["event"] == "done"

    def test_chat_unauthorized(self, supabase_mock) -> None:
        app = create_app()
        client = TestClient(app)
        response = client.post(
            "/chat",
            json={
                "document_id": "123e4567-e89b-12d3-a456-426614174000",
                "query": "Test",
            },
        )
        assert response.status_code == 401

    def test_chat_document_not_found(
        self,
        client: TestClient,
        supabase_mock: MagicMock,
        mock_generate_embedding,
    ) -> None:
        table_mock = MagicMock()
        table_mock.select.return_value = table_mock
        table_mock.eq.return_value = table_mock
        table_mock.limit.return_value = table_mock
        table_mock.execute.return_value = MagicMock(data=[])
        supabase_mock.table.return_value = table_mock

        payload = {
            "document_id": "123e4567-e89b-12d3-a456-426614174000",
            "query": "Anything",
        }
        response = client.post("/chat", json=payload)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_chat_document_not_embedded(
        self,
        client: TestClient,
        supabase_mock: MagicMock,
        mock_generate_embedding,
    ) -> None:
        configure_document_lookup(supabase_mock, status="extracted")

        payload = {
            "document_id": "123e4567-e89b-12d3-a456-426614174000",
            "query": "Anything",
        }
        response = client.post("/chat", json=payload)
        assert response.status_code == 400
        assert "embedded" in response.json()["detail"].lower()

    def test_chat_query_embedding_failure(
        self,
        client: TestClient,
        supabase_mock: MagicMock,
        mock_generate_embedding,
    ) -> None:
        configure_document_lookup(supabase_mock)
        mock_generate_embedding.side_effect = RuntimeError("embedding boom")

        payload = {
            "document_id": "123e4567-e89b-12d3-a456-426614174000",
            "query": "Anything",
        }
        response = client.post("/chat", json=payload)
        assert response.status_code == 500
        assert "failed to embed query" in response.json()["detail"].lower()

    def test_chat_no_chunks_found(
        self,
        client: TestClient,
        supabase_mock: MagicMock,
        mock_generate_embedding,
    ) -> None:
        configure_document_lookup(supabase_mock)
        configure_rpc_matches(supabase_mock, [])

        payload = {
            "document_id": "123e4567-e89b-12d3-a456-426614174000",
            "query": "Anything",
        }
        response = client.post("/chat", json=payload)
        assert response.status_code == 404
        assert "no relevant chunks" in response.json()["detail"].lower()

    def test_chat_with_conversation_history(
        self,
        client: TestClient,
        supabase_mock: MagicMock,
        mock_generate_embedding,
        mock_stream_chat_response,
        sample_chunks,
        sample_history,
    ) -> None:
        configure_document_lookup(supabase_mock)
        configure_rpc_matches(supabase_mock, sample_chunks)

        payload = {
            "document_id": "123e4567-e89b-12d3-a456-426614174000",
            "query": "Continue",
            "history": [message.model_dump() for message in sample_history],
        }

        with client.stream("POST", "/chat", json=payload) as response:
            assert response.status_code == 200
            list(response.iter_text())

        args, kwargs = mock_stream_chat_response.call_args
        history_payload = kwargs.get("history") or args[2]
        assert len(history_payload) == 2
        assert history_payload[0]["role"] == "user"
        assert history_payload[0]["parts"] == ["Hi"]

    def test_chat_context_truncation(
        self,
        client: TestClient,
        supabase_mock: MagicMock,
        mock_generate_embedding,
        mock_stream_chat_response,
        mock_count_tokens,
    ) -> None:
        configure_document_lookup(supabase_mock)
        heavy_chunks = [
            {
                "id": idx,
                "document_id": "doc-123",
                "chunk_index": idx,
                # Use distinct texts per chunk to reliably assert drops
                "chunk_text": ("X" * 5000) + f"_{idx}",
                "similarity": 0.9 - idx * 0.01,
            }
            for idx in range(3)
        ]
        configure_rpc_matches(supabase_mock, heavy_chunks)

        mock_count_tokens.side_effect = lambda text, encoding_name="cl100k_base": len(text)

        payload = {
            "document_id": "123e4567-e89b-12d3-a456-426614174000",
            "query": "Trim please",
        }

        with client.stream("POST", "/chat", json=payload) as response:
            assert response.status_code == 200
            list(response.iter_text())

        args, kwargs = mock_stream_chat_response.call_args
        context = kwargs.get("context") or args[1]
        assert len(context) < 5000 * 3
        # Ensure the lowest-similarity chunk was dropped
        assert heavy_chunks[-1]["chunk_text"] not in context

    def test_chat_history_truncation(
        self,
        client: TestClient,
        supabase_mock: MagicMock,
        mock_generate_embedding,
        mock_stream_chat_response,
        mock_count_tokens,
        sample_chunks,
    ) -> None:
        configure_document_lookup(supabase_mock)
        configure_rpc_matches(supabase_mock, sample_chunks)

        long_history = [
            ChatMessage(role="user", content="A" * 6000),
            ChatMessage(role="model", content="B" * 6000),
            ChatMessage(role="user", content="C" * 10),
        ]
        mock_count_tokens.side_effect = lambda text, encoding_name="cl100k_base": len(text)

        payload = {
            "document_id": "123e4567-e89b-12d3-a456-426614174000",
            "query": "History trunc",
            "history": [message.model_dump() for message in long_history],
        }

        with client.stream("POST", "/chat", json=payload) as response:
            assert response.status_code == 200
            list(response.iter_text())

        args, kwargs = mock_stream_chat_response.call_args
        history_payload = kwargs.get("history") or args[2]
        assert len(history_payload) == 1
        assert history_payload[0]["parts"] == ["C" * 10]

    def test_chat_sse_event_format(
        self,
        client: TestClient,
        supabase_mock: MagicMock,
        mock_generate_embedding,
        mock_stream_chat_response,
        sample_chunks,
    ) -> None:
        configure_document_lookup(supabase_mock)
        configure_rpc_matches(supabase_mock, sample_chunks)

        payload = {
            "document_id": "123e4567-e89b-12d3-a456-426614174000",
            "query": "Format",
        }

        with client.stream("POST", "/chat", json=payload) as response:
            chunks = list(response.iter_text())

        events = parse_sse_stream(chunks)
        assert [event["event"] for event in events] == [
            "provenance",
            "token",
            "token",
            "token",
            "done",
        ]

    def test_chat_streaming_error(
        self,
        client: TestClient,
        supabase_mock: MagicMock,
        mock_generate_embedding,
        mock_stream_chat_response,
        sample_chunks,
    ) -> None:
        configure_document_lookup(supabase_mock)
        configure_rpc_matches(supabase_mock, sample_chunks)

        def failing_generator():
            yield "Start"
            raise RuntimeError("stream break")

        mock_stream_chat_response.return_value = failing_generator()

        payload = {
            "document_id": "123e4567-e89b-12d3-a456-426614174000",
            "query": "Handle errors",
        }

        with client.stream("POST", "/chat", json=payload) as response:
            chunks = list(response.iter_text())

        events = parse_sse_stream(chunks)
        assert events[-1]["event"] == "error"
        assert "stream break" in events[-1]["data"]["error"]

    def test_chat_empty_query(
        self,
        client: TestClient,
        supabase_mock: MagicMock,
        mock_generate_embedding,
    ) -> None:
        payload = {
            "document_id": "123e4567-e89b-12d3-a456-426614174000",
            "query": "",
        }
        response = client.post("/chat", json=payload)
        assert response.status_code == 422

    def test_chat_invalid_max_chunks(
        self,
        client: TestClient,
        supabase_mock: MagicMock,
        mock_generate_embedding,
    ) -> None:
        payload = {
            "document_id": "123e4567-e89b-12d3-a456-426614174000",
            "query": "valid",
            "max_chunks": 0,
        }
        response = client.post("/chat", json=payload)
        assert response.status_code == 422

    @pytest.mark.parametrize("max_chunks", [1, 3, 5, 10])
    def test_chat_various_chunk_counts(
        self,
        client: TestClient,
        supabase_mock: MagicMock,
        mock_generate_embedding,
        mock_stream_chat_response,
        sample_chunks,
        max_chunks: int,
    ) -> None:
        configure_document_lookup(supabase_mock)
        configure_rpc_matches(supabase_mock, sample_chunks[:max_chunks if max_chunks <= len(sample_chunks) else len(sample_chunks)])

        payload = {
            "document_id": "123e4567-e89b-12d3-a456-426614174000",
            "query": "Varied",
            "max_chunks": max_chunks,
        }

        with client.stream("POST", "/chat", json=payload) as response:
            assert response.status_code == 200
            list(response.iter_text())

        args, _ = supabase_mock.rpc.call_args
        assert args[1]["match_count"] == max_chunks

    @pytest.mark.parametrize("threshold", [0.0, 0.3, 0.5, 0.8])
    def test_chat_various_similarity_thresholds(
        self,
        client: TestClient,
        supabase_mock: MagicMock,
        mock_generate_embedding,
        mock_stream_chat_response,
        sample_chunks,
        threshold: float,
    ) -> None:
        configure_document_lookup(supabase_mock)
        configure_rpc_matches(supabase_mock, sample_chunks)

        payload = {
            "document_id": "123e4567-e89b-12d3-a456-426614174000",
            "query": "Threshold",
            "similarity_threshold": threshold,
        }

        with client.stream("POST", "/chat", json=payload) as response:
            assert response.status_code == 200
            list(response.iter_text())

        args, _ = supabase_mock.rpc.call_args
        assert pytest.approx(args[1]["similarity_threshold"]) == threshold


class TestChatSSEFormatting:
    def test_chat_done_event_includes_finish_reason(
        self,
        client: TestClient,
        supabase_mock: MagicMock,
        mock_generate_embedding,
        mock_stream_chat_response,
        sample_chunks,
    ) -> None:
        configure_document_lookup(supabase_mock)
        configure_rpc_matches(supabase_mock, sample_chunks)

        payload = {
            "document_id": "123e4567-e89b-12d3-a456-426614174000",
            "query": "finish",
        }

        with client.stream("POST", "/chat", json=payload) as response:
            events = parse_sse_stream(response.iter_text())

        assert events[-1] == {"event": "done", "data": {"finish_reason": "stop"}}