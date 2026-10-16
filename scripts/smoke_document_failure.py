
import json
import time
from uuid import uuid4

from fastapi.testclient import TestClient
from redis import Redis

from server import app
from database.database import engine
from queues.celery_app import REDIS_URL
from queues.failure_handling import DEAD_LETTER_QUEUE


def main():
    if engine.url.database != "docuchat_db":
        raise RuntimeError(
            "This smoke test must use docuchat_db"
        )

    client = TestClient(app)
    redis_client = Redis.from_url(
        REDIS_URL,
        decode_responses=True,
    )

    try:
        initial_dlq_count = redis_client.llen(
            DEAD_LETTER_QUEUE
        )

        # Create a temporary development user.
        registration = client.post(
            "/api/v1/auth/register",
            json={
                "name": "Celery Failure Test",
                "email": (
                    f"failure-{uuid4().hex}@example.com"
                ),
                "password": "TestPassword123!",
            },
        )

        assert registration.status_code == 201, (
            registration.text
        )

        token = registration.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}"
        }

        # Whitespace passes through the upload endpoint
        # but produces zero processable text chunks.
        response = client.post(
            "/api/v1/documents",
            json={
                "title": "Intentional Celery Failure Test",
                "content": "   \n\t   ",
            },
            headers=headers,
        )

        assert response.status_code == 202, (
            "Document was not accepted: "
            + response.text
        )

        data = response.json()
        document_id = data["document"]["id"]

        print("Document ID:", document_id)
        print("Initial status:", data["document"]["status"])
        print("Initial DLQ count:", initial_dlq_count)

        # Allow the worker to retry before checking.
        final_status = None

        for attempt in range(45):
            status_response = client.get(
                (
                    f"/api/v1/documents/"
                    f"{document_id}/processing-status"
                ),
                headers=headers,
            )

            assert status_response.status_code == 200, (
                status_response.text
            )

            status_data = status_response.json()
            final_status = status_data["status"]

            print(
                f"Check {attempt + 1}: {final_status}"
            )

            if final_status == "failed":
                break

            time.sleep(1)

        assert final_status == "failed", (
            "Document did not reach failed status"
        )

        # Verify this specific document reached the DLQ.
        failure_record = None

        for _ in range(10):
            records = redis_client.lrange(
                DEAD_LETTER_QUEUE, 0, -1
            )

            for raw_record in records:
                record = json.loads(raw_record)

                if record.get("documentId") == document_id:
                    failure_record = record
                    break

            if failure_record is not None:
                break

            time.sleep(1)

        assert failure_record is not None, (
            "Document was not recorded in the DLQ"
        )

        assert failure_record["attempts"] == 3, (
            failure_record
        )

        print("Final status:", final_status)
        print(
            "Processing attempts:",
            failure_record["attempts"],
        )
        print(
            "Failure reason:",
            failure_record["error"],
        )
        print(
            "DLQ count:",
            redis_client.llen(DEAD_LETTER_QUEUE),
        )

        print(
            "SUCCESS: Retries and permanent failure "
            "handling verified!"
        )

    finally:
        redis_client.close()


if __name__ == "__main__":
    main()
