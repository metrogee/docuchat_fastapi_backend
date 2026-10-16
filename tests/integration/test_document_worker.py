
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from database.models import Document, DocumentChunk
from queues.document_tasks import process_document


def create_test_document(client, content):
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Worker Test User",
            "email": f"worker-{uuid4().hex}@example.com",
            "password": "TestPassword123!",
        },
    )
    assert registration.status_code == 201, registration.text

    token = registration.json()["access_token"]

    response = client.post(
        "/api/v1/documents",
        json={
            "title": "Worker Integration Test",
            "content": content,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 202, response.text

    document = response.json()["document"]
    return document["id"], document["user_id"]


@pytest.fixture
def worker_database(monkeypatch, test_db):
    """
    Force worker execution to use docuchat_test,
    never the development database.
    """
    test_session_factory = sessionmaker(
        bind=test_db.get_bind(),
        expire_on_commit=False,
    )

    monkeypatch.setattr(
        "queues.document_tasks.SessionLocal",
        test_session_factory,
    )

    return test_session_factory


def run_with_retry_count(retries, document_id, user_id):
    process_document.push_request(retries=retries)

    try:
        return process_document.run(document_id, user_id)
    finally:
        process_document.pop_request()


def test_worker_processes_document_and_saves_chunks(
    client, worker_database
):
    content = " ".join(f"word{i}" for i in range(1200))
    document_id, user_id = create_test_document(
        client, content
    )

    with patch.object(process_document, "update_state"):
        result = run_with_retry_count(
            0, document_id, user_id
        )

    assert result["success"] is True
    assert result["chunks"] == 3

    with worker_database() as db:
        document = db.get(Document, document_id)

        chunks = db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        ).all()

        assert document.status == "ready"
        assert len(chunks) == 3
        assert [
            len(chunk.content.split()) for chunk in chunks
        ] == [500, 500, 200]


@pytest.mark.parametrize(
    "retries,expected_delay",
    [
        (0, 2),
        (1, 4),
    ],
)
def test_worker_retries_with_exponential_backoff(
    client,
    worker_database,
    monkeypatch,
    retries,
    expected_delay,
):
    document_id, user_id = create_test_document(
        client, "Valid content"
    )

    # Simulate a processing failure.
    monkeypatch.setattr(
        "queues.document_tasks.split_into_chunks",
        lambda *args, **kwargs: [],
    )

    with patch.object(process_document, "update_state"):
        with patch.object(
            process_document,
            "retry",
            side_effect=RuntimeError("Retry scheduled"),
        ) as retry_mock:
            with pytest.raises(
                RuntimeError, match="Retry scheduled"
            ):
                run_with_retry_count(
                    retries, document_id, user_id
                )

    assert retry_mock.call_count == 1
    assert retry_mock.call_args.kwargs["countdown"] == (
        expected_delay
    )

    with worker_database() as db:
        document = db.get(Document, document_id)
        assert document.status == "processing"


def test_worker_marks_permanent_failure_and_sends_to_dlq(
    client,
    worker_database,
    monkeypatch,
):
    document_id, user_id = create_test_document(
        client, "Valid content"
    )

    monkeypatch.setattr(
        "queues.document_tasks.split_into_chunks",
        lambda *args, **kwargs: [],
    )

    with patch.object(process_document, "update_state"):
        with patch(
            "queues.document_tasks.send_to_dead_letter_queue"
        ) as mock_dlq:
            with pytest.raises(
                ValueError,
                match="no processable text",
            ):
                run_with_retry_count(
                    2, document_id, user_id
                )

    mock_dlq.assert_called_once()

    arguments = mock_dlq.call_args.kwargs

    assert arguments["document_id"] == document_id
    assert arguments["user_id"] == user_id
    assert arguments["attempts"] == 3

    with worker_database() as db:
        document = db.get(Document, document_id)
        assert document.status == "failed"


def test_worker_does_not_duplicate_ready_document_chunks(
    client,
    worker_database,
):
    document_id, user_id = create_test_document(
        client, " ".join(["word"] * 600)
    )

    with patch.object(process_document, "update_state"):
        first = run_with_retry_count(
            0, document_id, user_id
        )
        second = run_with_retry_count(
            0, document_id, user_id
        )

    assert first["success"] is True
    assert second["already_processed"] is True

    with worker_database() as db:
        chunks = db.scalars(
            select(DocumentChunk).where(
                DocumentChunk.document_id == document_id
            )
        ).all()

        assert len(chunks) == 2
