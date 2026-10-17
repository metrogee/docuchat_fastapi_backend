
import json

from database.models import WebhookEvent
from utils.webhook_security import generate_signature


SECRET = "integration-test-webhook-secret"

ENDPOINT = "/api/v1/webhooks/example"


def make_payload(event_id="evt_123"):
    return json.dumps({
        "id": event_id,
        "type": "document.imported",
    }).encode("utf-8")


def send_webhook(client, payload, signature):
    return client.post(
        ENDPOINT,
        content=payload,
        headers={
            "X-Webhook-Signature": signature,
            "Content-Type": "application/json",
        },
    )


def test_invalid_signature_returns_401(
    client, monkeypatch
):
    monkeypatch.setenv("WEBHOOK_SECRET", SECRET)

    response = send_webhook(
        client,
        make_payload(),
        "a" * 64,
    )

    assert response.status_code == 401


def test_missing_signature_returns_401(
    client, monkeypatch
):
    monkeypatch.setenv("WEBHOOK_SECRET", SECRET)

    response = client.post(
        ENDPOINT,
        content=make_payload(),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 401


def test_valid_webhook_is_persisted(
    client, test_db, monkeypatch, mock_webhook_queue
):
    monkeypatch.setenv("WEBHOOK_SECRET", SECRET)

    payload = make_payload()
    signature = generate_signature(payload, SECRET)

    response = send_webhook(client, payload, signature)

    assert response.status_code == 200
    assert response.json()["received"] is True
    assert response.json()["status"] == "queued"

    event = test_db.get(WebhookEvent, "example:evt_123")

    assert event is not None
    assert event.status == "pending"
    assert event.event_type == "document.imported"
    assert event.processed_at is None

    mock_webhook_queue.assert_called_once_with(
        "example:evt_123"
    )


def test_duplicate_delivery_creates_one_record(
    client, test_db, monkeypatch, mock_webhook_queue
):
    monkeypatch.setenv("WEBHOOK_SECRET", SECRET)

    payload = make_payload()
    signature = generate_signature(payload, SECRET)

    first = send_webhook(client, payload, signature)
    second = send_webhook(client, payload, signature)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["duplicate"] is True

    events = test_db.query(WebhookEvent).all()

    assert len(events) == 1

    # Pending duplicates may enqueue another delivery.
    # The worker's atomic claim prevents simultaneous
    # processing of the same event.
    assert mock_webhook_queue.call_count == 2


def test_processed_duplicate_is_not_requeued(
    client, test_db, monkeypatch, mock_webhook_queue
):
    monkeypatch.setenv("WEBHOOK_SECRET", SECRET)

    payload = make_payload()
    signature = generate_signature(payload, SECRET)

    first = send_webhook(client, payload, signature)
    assert first.status_code == 200

    event = test_db.get(WebhookEvent, "example:evt_123")

    event.status = "processed"
    test_db.commit()

    second = send_webhook(client, payload, signature)

    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["status"] == "processed"

    mock_webhook_queue.assert_called_once()


def test_reused_event_id_with_different_payload(
    client, monkeypatch
):
    monkeypatch.setenv("WEBHOOK_SECRET", SECRET)

    first_payload = make_payload("evt_123")

    second_payload = json.dumps({
        "id": "evt_123",
        "type": "payment.succeeded",
    }).encode("utf-8")

    first = send_webhook(
        client,
        first_payload,
        generate_signature(first_payload, SECRET),
    )

    second = send_webhook(
        client,
        second_payload,
        generate_signature(second_payload, SECRET),
    )

    assert first.status_code == 200
    assert second.status_code == 409
