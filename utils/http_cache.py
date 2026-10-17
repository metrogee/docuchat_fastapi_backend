
import hashlib
import json

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response


def conditional_json_response(
    request: Request,
    data,
    status_code: int = 200,
    cache_control: str = "private, no-cache",
):
    """
    Return JSON with an ETag.

    When If-None-Match matches, return 304 without a body.
    Authentication and authorization must happen before
    calling this function.
    """

    encoded = jsonable_encoder(data)

    content = json.dumps(
        encoded,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    etag = '"' + hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest() + '"'

    headers = {
        "ETag": etag,
        "Cache-Control": cache_control,
        "Vary": "Authorization",
    }

    if status_code == 200:
        client_etags = request.headers.get(
            "if-none-match", ""
        )

        candidates = [
            value.strip()
            for value in client_etags.split(",")
        ]

        if etag in candidates or "*" in candidates:
            return Response(
                status_code=304,
                headers=headers,
            )

    return JSONResponse(
        content=encoded,
        status_code=status_code,
        headers=headers,
    )
