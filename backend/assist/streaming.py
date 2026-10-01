"""Relays a streamed model answer as server-sent-event payloads, and parses files out of it."""

import logging
import re
from dataclasses import dataclass, field
from typing import AsyncIterator, Callable

import openai

from errors import describe_llm_error
from llm_client import StreamEnd, Task, Usage

from .languages import language_for
from .schemas import GeneratedFile, StreamDone, UsageInfo

logger = logging.getLogger(__name__)

FENCE = re.compile(
    r"^```([\w+#.-]*)[ \t]+path=[\"']?([^\s\"'`]+)[\"']?[^\n]*\n(.*?)^```[ \t]*$",
    re.M | re.S,
)


@dataclass
class StreamOutcome:
    text: str = ""
    end: StreamEnd = field(default_factory=lambda: StreamEnd(usage=Usage(), finish_reason=None))
    failed: bool = False


async def relay(llm, messages: list[dict], task: Task, outcome: StreamOutcome) -> AsyncIterator[tuple[str, dict]]:
    """Yields `delta` events, or one `error` event, and records the result in `outcome`."""
    parts: list[str] = []
    try:
        async for item in llm.stream(messages, task):
            if isinstance(item, StreamEnd):
                outcome.end = item
            else:
                parts.append(item)
                yield "delta", {"text": item}
    except openai.APIError as exc:
        _, message = describe_llm_error(exc)
        logger.error("Streaming %s failed: %s", task, message)
        outcome.failed = True
        yield "error", {"message": message}
    except Exception:
        logger.exception("Streaming %s failed", task)
        outcome.failed = True
        yield "error", {"message": "Internal server error"}
    finally:
        outcome.text = "".join(parts)


def done_event(outcome: StreamOutcome, secrets_redacted: int, llm, track: Callable[[Usage], UsageInfo]) -> tuple[str, dict]:
    done = StreamDone(
        text=outcome.text,
        files=extract_files(outcome.text),
        truncated=outcome.end.finish_reason == "length",
        secrets_redacted=secrets_redacted,
        model=llm.model,
        usage=track(outcome.end.usage),
    )
    return "done", done.model_dump()


def extract_files(text: str) -> list[GeneratedFile]:
    files: dict[str, GeneratedFile] = {}
    for match in FENCE.finditer(text):
        language, path, body = match.group(1), match.group(2), match.group(3)
        files[path] = GeneratedFile(path=path, language=(language or language_for(path)).lower(), content=body)
    return list(files.values())
