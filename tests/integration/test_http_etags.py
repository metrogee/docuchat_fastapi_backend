
from fastapi import FastAPI
from fastapi.testclient import TestClient

from utils.http_cache import conditional_json_response


def test_etag_returns_304_for_matching_content():
    app = FastAPI()

    @app.get("/resource")
    def get_resource(request: __import__("fastapi").Request):
        return conditional_json_response(
            request,
            {"id": "123", "title": "DocuChat"},
        )

    with TestClient(app) as client:
        first = client.get("/resource")

        assert first.status_code == 200
        assert "etag" in first.headers
        assert first.headers["cache-control"] == (
            "private, no-cache"
        )

        second = client.get(
            "/resource",
            headers={
                "If-None-Match": first.headers["etag"]
            },
        )

        assert second.status_code == 304
        assert second.content == b""


def test_etag_changes_when_resource_changes():
    app = FastAPI()
    state = {"title": "Original"}

    @app.get("/resource")
    def get_resource(request: __import__("fastapi").Request):
        return conditional_json_response(
            request,
            state,
        )

    with TestClient(app) as client:
        first = client.get("/resource")
        old_etag = first.headers["etag"]

        state["title"] = "Updated"

        second = client.get(
            "/resource",
            headers={"If-None-Match": old_etag},
        )

        assert second.status_code == 200
        assert second.headers["etag"] != old_etag
        assert second.json()["title"] == "Updated"


def test_auth_responses_disable_browser_caching():
    from server import app

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={},
        )

        assert response.headers["cache-control"] == (
            "no-store"
        )
