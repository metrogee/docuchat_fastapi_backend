
import pytest
import httpx

from http_clients.openai_client import (
    OpenAIClient,
    ExternalAPIError,
)


def test_successful_request():
    def handler(request):
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json={"data": [{"embedding": [0.1, 0.2]}]},
        )

    client = OpenAIClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    try:
        result = client.post(
            "/embeddings",
            {"input": "hello", "model": "test-model"},
        )
        assert result["data"][0]["embedding"] == [0.1, 0.2]
    finally:
        client.close()


def test_bad_endpoint_returns_structured_error():
    def handler(request):
        return httpx.Response(
            404,
            json={"error": "Not found"},
        )

    client = OpenAIClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    try:
        with pytest.raises(ExternalAPIError) as exc:
            client.post("/invalid-endpoint", {})

        assert exc.value.status_code == 404
    finally:
        client.close()


def test_network_failure():
    def handler(request):
        raise httpx.ConnectError(
            "Connection failed",
            request=request,
        )

    client = OpenAIClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    try:
        with pytest.raises(
            ExternalAPIError,
            match="connection failed",
        ):
            client.post("/embeddings", {})
    finally:
        client.close()
