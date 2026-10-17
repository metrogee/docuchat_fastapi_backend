
import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)


class ExternalAPIError(Exception):
    def __init__(
        self,
        message,
        status_code=None,
        retry_after=None,
    ):
        self.status_code = status_code
        self.retry_after = retry_after
        super().__init__(message)


class OpenAIClient:
    BASE_URL = "https://api.openai.com/v1"

    def __init__(self, api_key=None, timeout=30.0, transport=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.timeout = timeout

        self.client = httpx.Client(
            base_url=self.BASE_URL,
            timeout=httpx.Timeout(timeout),
            transport=transport,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "DocuChat/1.0",
            },
            event_hooks={
                "request": [self.log_request],
                "response": [self.log_response],
            },
        )

    @staticmethod
    def log_request(request):
        request.extensions["start_time"] = time.monotonic()
        logger.info(
            "External request: %s %s",
            request.method,
            request.url.path,
        )

    @staticmethod
    def log_response(response):
        start = response.request.extensions.get("start_time")
        duration = (
            round((time.monotonic() - start) * 1000, 2)
            if start is not None else 0
        )

        logger.info(
            "External response: %s %s (%sms)",
            response.status_code,
            response.request.url.path,
            duration,
        )

        if response.status_code >= 400:
            logger.error(
                "External API returned HTTP %s",
                response.status_code,
            )

        remaining = response.headers.get(
            "x-ratelimit-remaining-requests"
        )

        if remaining is not None:
            try:
                if int(remaining) < 50:
                    logger.warning(
                        "OpenAI rate limit low: %s requests remaining",
                        remaining,
                    )
            except ValueError:
                logger.warning("Invalid rate-limit header received")

    def post(self, endpoint, data):
        try:
            response = self.client.post(endpoint, json=data)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            retry_after = exc.response.headers.get("retry-after")

            logger.error("OpenAI HTTP error: %s", status)

            raise ExternalAPIError(
                f"OpenAI returned HTTP {status}",
                status_code=status,
                retry_after=retry_after,
            ) from exc

        except httpx.TimeoutException as exc:
            logger.error("OpenAI request timed out")
            raise ExternalAPIError(
                "OpenAI request timed out"
            ) from exc

        except httpx.RequestError as exc:
            logger.error(
                "OpenAI connection failed: %s",
                type(exc).__name__,
            )
            raise ExternalAPIError(
                "OpenAI connection failed"
            ) from exc

        except ValueError as exc:
            logger.error("Invalid JSON response from OpenAI")
            raise ExternalAPIError(
                "OpenAI returned an invalid JSON response"
            ) from exc

    def close(self):
        self.client.close()
