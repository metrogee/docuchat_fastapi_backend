
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from middleware.error_handler import (
    app_error_handler,
    unexpected_error_handler,
)
from utils.errors import AppError


app = FastAPI()

app.add_exception_handler(
    AppError,
    app_error_handler,
)

app.add_exception_handler(
    Exception,
    unexpected_error_handler,
)


@app.get("/expected-error")
def raise_expected_error():
    raise AppError(
        message="password=SuperSecret123",
        status_code=400,
        code="TEST_ERROR",
        details={
            "access_token": "abc.def.ghi",
        },
    )


@app.get("/unexpected-error")
def raise_unexpected_error():
    raise RuntimeError(
        "Database failed: "
        "postgresql://admin:secretpass@localhost:5432/docuchat"
    )


client = TestClient(
    app,
    raise_server_exceptions=False,
)


def test_expected_error_redacts_secrets(caplog):
    with caplog.at_level(logging.WARNING):
        response = client.get("/expected-error")

    assert response.status_code == 400

    body = response.json()

    assert "SuperSecret123" not in str(body)

    assert (
        body["error"]["details"]["access_token"]
        == "[REDACTED]"
    )

    assert "SuperSecret123" not in caplog.text


def test_unexpected_error_returns_generic_message(caplog):
    with caplog.at_level(logging.ERROR):
        response = client.get("/unexpected-error")

    assert response.status_code == 500

    body = response.json()

    assert body["error"]["code"] == "INTERNAL_ERROR"

    assert body["error"]["message"] == (
        "An unexpected error occurred"
    )

    assert "secretpass" not in response.text
    assert "secretpass" not in caplog.text
    assert "postgresql://" not in caplog.text
