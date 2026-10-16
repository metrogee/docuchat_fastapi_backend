
import time
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from server import app
from database.database import SessionLocal, engine
from database.models import DocumentChunk


def main():
    database_name = engine.url.database
    print("Database:", database_name)

    if database_name != "docuchat_db":
        raise RuntimeError(
            "Smoke test must run against docuchat_db"
        )

    client = TestClient(app)

    # Step 1: Register a temporary development user.
    email = f"celery-test-{uuid4().hex[:10]}@example.com"

    registration = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Celery Test User",
            "email": email,
            "password": "TestPassword123!",
        },
    )

    assert registration.status_code == 201, (
        registration.status_code,
        registration.text,
    )

    token = registration.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {token}",
    }

    print("User registered successfully")

    # Step 2: Create a document with 1,200 words.
    content = " ".join(
        f"word{i}" for i in range(1200)
    )

    response = client.post(
        "/api/v1/documents",
        json={
            "title": "Celery Background Processing Test",
            "content": content,
        },
        headers=headers,
    )

    assert response.status_code == 202, (
        response.status_code,
        response.text,
    )

    payload = response.json()

    document_id = payload["document"]["id"]
    job_id = payload["jobId"]

    print("Document ID:", document_id)
    print("Celery job ID:", job_id)
    print("Initial status:", payload["document"]["status"])

    # Step 3: Poll until processing finishes.
    final_status = None

    for attempt in range(30):
        result = client.get(
            f"/api/v1/documents/{document_id}",
            headers=headers,
        )

        assert result.status_code == 200, result.text

        final_status = result.json()["status"]

        print(
            f"Check {attempt + 1}: {final_status}"
        )

        if final_status in {"ready", "failed"}:
            break

        time.sleep(1)

    # Step 4: Verify the database records.
    with SessionLocal() as db:
        chunks = db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        ).all()

        print("Final status:", final_status)
        print("Chunks created:", len(chunks))
        print(
            "Words per chunk:",
            [len(chunk.content.split()) for chunk in chunks],
        )

        assert final_status == "ready", (
            "Document processing did not finish successfully"
        )

        assert len(chunks) == 3
        assert [
            len(chunk.content.split())
            for chunk in chunks
        ] == [500, 500, 200]

    print("SUCCESS: Background processing works!")


if __name__ == "__main__":
    main()
