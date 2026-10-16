import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from database.database import engine, get_db
from server import app


test_database_url = engine.url.set(database="docuchat_test")

test_engine = create_engine(
    test_database_url,
    pool_pre_ping=True,
)

TestSessionLocal = sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False,
)


def override_get_db():
    db = TestSessionLocal()

    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def clean_test_database():
    with test_engine.begin() as connection:
        connection.execute(
            text(
                """
                TRUNCATE TABLE
                    messages,
                    conversations,
                    document_chunks,
                    usage_logs,
                    audit_logs,
                    documents,
                    refresh_tokens,
                    users
                RESTART IDENTITY
                CASCADE
                """
            )
        )

    yield

@pytest.fixture
def test_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

from unittest.mock import Mock

from queues.document_tasks import process_document


@pytest.fixture(autouse=True)
def mock_document_queue(monkeypatch):
    """Prevent tests from publishing real Celery jobs."""

    def fake_apply_async(*args, **kwargs):
        task_id = kwargs.get("task_id", "test-document-job")
        return Mock(id=task_id)

    monkeypatch.setattr(
        process_document,
        "apply_async",
        fake_apply_async,
    )