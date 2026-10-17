import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import os

os.environ["REDIS_RATE_LIMIT_DB"] = "3"

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
                    webhook_events,
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

from queues.webhook_tasks import process_webhook


@pytest.fixture(autouse=True)
def mock_webhook_queue(monkeypatch):
    """Prevent tests from publishing real webhook Celery jobs."""

    fake_delay = Mock(return_value=Mock(id="test-webhook-job"))

    monkeypatch.setattr(
        process_webhook,
        "delay",
        fake_delay,
    )

    return fake_delay



@pytest.fixture(autouse=True)
def isolate_http_rate_limiting(monkeypatch, request):
    """
    Bypass HTTP rate limiting in unrelated tests.
    Preserve the real middleware in dedicated tests.
    """
    if request.node.path.name == "test_http_rate_limit.py":
        return

    from middleware.rate_limit import APIRateLimitMiddleware

    async def bypass_rate_limit(
        self,
        http_request,
        call_next,
    ):
        return await call_next(http_request)

    monkeypatch.setattr(
        APIRateLimitMiddleware,
        "dispatch",
        bypass_rate_limit,
    )




@pytest.fixture(autouse=True)
def isolate_login_protection(monkeypatch, request):
    """
    Mock account login protection except when
    explicitly testing login lockout behaviour.
    """
    if request.node.path.name in {
        "test_login_protection.py",
        "test_login_lockout.py",
    }:
        return

    from utils.login_protection import LoginProtection

    monkeypatch.setattr(
        LoginProtection,
        "check_allowed",
        lambda self, email: None,
    )

    monkeypatch.setattr(
        LoginProtection,
        "record_failure",
        lambda self, email: None,
    )

    monkeypatch.setattr(
        LoginProtection,
        "reset",
        lambda self, email: None,
    )

