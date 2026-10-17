
from unittest.mock import patch

from queues.webhook_tasks import process_webhook_event


def test_document_imported_handler():
    payload = {
        "id": "evt_123",
        "type": "document.imported",
    }

    with patch(
        "queues.webhook_tasks.logger"
    ) as mock_logger:
        process_webhook_event(
            "document.imported",
            payload,
        )

        mock_logger.info.assert_called_once()


def test_unknown_webhook_type():
    payload = {
        "id": "evt_unknown",
        "type": "unknown.event",
    }

    with patch(
        "queues.webhook_tasks.logger"
    ) as mock_logger:
        process_webhook_event(
            "unknown.event",
            payload,
        )

        mock_logger.info.assert_called_once()
