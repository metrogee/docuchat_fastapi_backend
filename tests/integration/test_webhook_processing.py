
import json

from sqlalchemy.orm import sessionmaker

from database.models import WebhookEvent
from queues.webhook_tasks import process_webhook


def test_webhook_worker_processes_event_once(
    test_db,
    monkeypatch,
):
    # Redirect worker database access to docuchat_test.
    TestSessionFactory = sessionmaker(
        bind=test_db.get_bind(),
        autoflush=False,
    )

    monkeypatch.setattr(
        "queues.webhook_tasks.SessionLocal",
        TestSessionFactory,
    )

    event = WebhookEvent(
        id="example:worker_test_001",
        provider="example",
        event_type="document.imported",
        payload=json.dumps({
            "id": "worker_test_001",
            "type": "document.imported",
        }),
        status="pending",
    )

    test_db.add(event)
    test_db.commit()

    # First execution processes the event.
    first_result = process_webhook.run(event.id)

    test_db.expire_all()
    stored_event = test_db.get(WebhookEvent, event.id)

    assert first_result["status"] == "processed"
    assert stored_event.status == "processed"
    assert stored_event.processed_at is not None

    # Second execution must not process it again.
    second_result = process_webhook.run(event.id)

    assert second_result["status"] == "skipped"

    test_db.expire_all()
    stored_event = test_db.get(WebhookEvent, event.id)

    assert stored_event.status == "processed"
