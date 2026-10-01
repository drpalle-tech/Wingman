import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from assist.router import router
from cost_tracker import CostTracker
from errors import register_error_handlers
from llm_client import Completion, StreamEnd, Usage


class FakeLLM:
    model = "fake-model"

    def __init__(self, replies=None, stream_chunks=None, stream_error=None):
        self.replies = list(replies or [])
        self.stream_chunks = list(stream_chunks or [])
        self.stream_error = stream_error
        self.calls = []

    async def complete(self, messages, task):
        self.calls.append((task, messages))
        return Completion(text=self.replies.pop(0), usage=Usage(1000, 200), finish_reason="stop")

    async def stream(self, messages, task):
        self.calls.append((task, messages))
        for chunk in self.stream_chunks:
            yield chunk
        if self.stream_error:
            raise self.stream_error
        yield StreamEnd(usage=Usage(500, 100), finish_reason="stop")

    def prompt_text(self) -> str:
        return "\n".join(m["content"] for _, messages in self.calls for m in messages)


@pytest.fixture
def make_client(tmp_path):
    def _make(llm: FakeLLM) -> TestClient:
        app = FastAPI()
        register_error_handlers(app)
        app.state.llm = llm
        app.state.cost_tracker = CostTracker(llm.model, tmp_path / "usage.db")
        app.include_router(router)
        return TestClient(app)

    return _make


def parse_sse(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        events.append((fields["event"], json.loads(fields["data"])))
    return events
