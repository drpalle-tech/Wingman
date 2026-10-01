"""App-wide error handling: consistent JSON errors without leaking internals."""

import logging

import openai
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class UpstreamError(Exception):
    """The model responded, but not with something usable."""


def describe_llm_error(exc: openai.APIError) -> tuple[int, str]:
    if isinstance(exc, openai.RateLimitError):
        return 429, "The model's rate limit was reached. Wait a moment and retry."
    if isinstance(exc, openai.APIConnectionError):
        return 502, "Could not reach the model endpoint. Check AZURE_ENDPOINT and your network."
    if isinstance(exc, openai.APIStatusError):
        return 502, f"Model provider error ({exc.status_code}): {exc.message}"[:600]
    return 502, "Model provider error."


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(openai.APIError)
    async def llm_error(request: Request, exc: openai.APIError) -> JSONResponse:
        status, message = describe_llm_error(exc)
        logger.error("LLM error on %s: %s", request.url.path, message)
        return JSONResponse(status_code=status, content={"detail": message})

    @app.exception_handler(UpstreamError)
    async def upstream_error(request: Request, exc: UpstreamError) -> JSONResponse:
        logger.error("Unusable model output on %s: %s", request.url.path, exc)
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
