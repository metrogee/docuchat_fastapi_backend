
import json

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from sqlalchemy.orm import sessionmaker

from database.models import WebhookEvent
from queues.webhook_tasks import recover_webhooks


def test_recovery_requeues_pending_and_stale_events(
    test_db,
    monkeypatch,
):
    test_session_factory = sessionmaker(
        bind=test_db.get_bind(),
        autoflush=False,
    )

    monkeypatch.setattr(
        "queues.webhook_tasks.SessionLocal",
        test_session_factory,
    )

    fake_delay = Mock()

    monkeypatch.setattr(
        "queues.webhook_tasks.process_webhook.delay",
        fake_delay,
    )

    old_time = datetime.now(timezone.utc) - timedelta(
        minutes=10
    )

    events = [
        WebhookEvent(
            id="example:pending_001",
            provider="example",
            event_type="document.imported",
            payload=json.dumps({"id": "pending_001"}),
            status="pending",
        ),
        WebhookEvent(
            id="example:stale_001",
            provider="example",
            event_type="document.imported",
            payload=json.dumps({"id": "stale_001"}),
            status="processing",
            processing_started_at=old_time,
        ),
        WebhookEvent(
            id="example:processed_001",
            provider="example",
            event_type="document.imported",
            payload=json.dumps({"id": "processed_001"}),
            status="processed",
        ),
    ]

    test_db.add_all(events)
    test_db.commit()

    result = recover_webhooks.run()

    assert result["recovered"] == 1
    assert result["queued"] == 2

    test_db.expire_all()

    stale = test_db.get(
        WebhookEvent,
        "example:stale_001",
    )

    assert stale.status == "pending"
    assert stale.processing_started_at is None

    queued_ids = {
        call.args[0]
        for call in fake_delay.call_args_list
    }

    assert queued_ids == {
        "example:pending_001",
        "example:stale_001",
    }


def test_recovery_leaves_active_processing_alone(
    test_db,
    monkeypatch,
):
    test_session_factory = sessionmaker(
        bind=test_db.get_bind(),
        autoflush=False,
    )

    monkeypatch.setattr(
        "queues.webhook_tasks.SessionLocal",
        test_session_factory,
    )

    fake_delay = Mock()

    monkeypatch.setattr(
        "queues.webhook_tasks.process_webhook.delay",
        fake_delay,
    )

    event = WebhookEvent(
        id="example:active_001",
        provider="example",
        event_type="document.imported",
        payload=json.dumps({"id": "active_001"}),
        status="processing",
        processing_started_at=datetime.now(timezone.utc),
    )

    test_db.add(event)
    test_db.commit()

    result = recover_webhooks.run()

    assert result["recovered"] == 0
    assert result["queued"] == 0

    fake_delay.assert_not_called()
