"""HTTP endpoints for the code assistant. Versioned because installed clients can't be force-upgraded."""

import json
import logging
import os
from typing import AsyncIterator, Callable

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from llm_client import Usage

from .chat import chat_events
from .generate import generate_events
from .review import run_review
from .schemas import CodeChatRequest, GenerateRequest, ReviewRequest, ReviewResponse, StreamDone, UsageInfo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["assist"])

STREAM_RESPONSES = {
    200: {
        "model": StreamDone,
        "content": {"text/event-stream": {}},
        "description": (
            "Server-sent events: `start` {model, secrets_redacted}, then `delta` {text} chunks, "
            "then `done` (StreamDone) or `error` {message}."
        ),
    }
}


def _check_size(chars: int) -> None:
    limit = int(os.getenv("MAX_CONTEXT_CHARS", "400000"))
    if chars > limit:
        raise HTTPException(413, f"Request is {chars:,} characters; the limit is {limit:,}. Send fewer or smaller files.")


def _tracker(request: Request, task: str) -> Callable[[Usage], UsageInfo]:
    cost_tracker = request.app.state.cost_tracker

    def track(usage: Usage) -> UsageInfo:
        record = cost_tracker.track_request(usage.input_tokens, usage.output_tokens, task)
        return UsageInfo(
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            cost_usd=record["total_cost"],
        )

    return track


def _sse(events: AsyncIterator[tuple[str, dict]]) -> StreamingResponse:
    async def body():
        async for event, data in events:
            yield f"event: {event}\ndata: {json.dumps(data)}\n\n"

    return StreamingResponse(
        body(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/review", response_model=ReviewResponse)
async def review(body: ReviewRequest, request: Request) -> ReviewResponse:
    _check_size(body.context.total_chars())
    logger.info("Review: %d files, %d chars", len(body.context.files), body.context.total_chars())
    return await run_review(body, request.app.state.llm, _tracker(request, "review"))


@router.post("/generate", response_class=StreamingResponse, responses=STREAM_RESPONSES)
async def generate(body: GenerateRequest, request: Request) -> StreamingResponse:
    _check_size(body.context.total_chars())
    logger.info("Generate (%s): %d files, %d chars", body.mode, len(body.context.files), body.context.total_chars())
    return _sse(generate_events(body, request.app.state.llm, _tracker(request, "generate")))


@router.post("/chat", response_class=StreamingResponse, responses=STREAM_RESPONSES)
async def chat(body: CodeChatRequest, request: Request) -> StreamingResponse:
    _check_size(body.total_chars())
    logger.info("Chat: %d turns, %d files, %d chars", len(body.messages), len(body.context.files), body.total_chars())
    return _sse(chat_events(body, request.app.state.llm, _tracker(request, "chat")))
