
import json

from starlette.requests import Request

from utils.http_cache import conditional_json_response


def make_request(headers=None):
    raw_headers = [
        (key.lower().encode(), value.encode())
        for key, value in (headers or {}).items()
    ]

    return Request({
        "type": "http",
        "method": "GET",
        "path": "/api/v1/conversations",
        "headers": raw_headers,
        "query_string": b"",
    })


def test_first_request_returns_200_with_etag():
    response = conditional_json_response(
        make_request(),
        {"data": [{"id": "123"}]},
    )

    assert response.status_code == 200
    assert response.headers["etag"]
    assert response.headers["cache-control"] == (
        "private, no-cache"
    )


def test_matching_etag_returns_304():
    data = {"data": [{"id": "123"}]}

    first = conditional_json_response(
        make_request(),
        data,
    )

    second = conditional_json_response(
        make_request({
            "if-none-match": first.headers["etag"]
        }),
        data,
    )

    assert second.status_code == 304
    assert second.body == b""


def test_changed_response_returns_200():
    first = conditional_json_response(
        make_request(),
        {"value": 1},
    )

    second = conditional_json_response(
        make_request({
            "if-none-match": first.headers["etag"]
        }),
        {"value": 2},
    )

    assert second.status_code == 200
    assert (
        first.headers["etag"]
        != second.headers["etag"]
    )


def test_etag_is_stable_for_same_data():
    first = conditional_json_response(
        make_request(),
        {"a": 1, "b": 2},
    )

    second = conditional_json_response(
        make_request(),
        {"b": 2, "a": 1},
    )

    assert (
        first.headers["etag"]
        == second.headers["etag"]
    )


def test_response_body_is_valid_json():
    response = conditional_json_response(
        make_request(),
        {"message": "success"},
    )

    assert json.loads(response.body) == {
        "message": "success"
    }
