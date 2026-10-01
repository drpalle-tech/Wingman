"""Conversational help about code: multi-turn, optionally grounded in files the developer shared."""

from typing import AsyncIterator, Callable

from llm_client import Usage

from .context import detect_project, render_bundle
from .prompting import system_prompt
from .schemas import ChatTurn, CodeChatRequest, UsageInfo
from .secret_scan import find_secrets, redact, redact_bundle
from .streaming import StreamOutcome, done_event, relay

MAX_HISTORY_CHARS = 60_000


def build_messages(req: CodeChatRequest) -> tuple[list[dict], int]:
    bundle, file_hits = redact_bundle(req.context)
    project = detect_project(bundle.files, bundle.project)
    system = system_prompt("chat", bundle, project)
    if bundle.files:
        system += "\n\n## Files the developer shared\n" + render_bundle(bundle, project, number_targets=True)

    turns, turn_hits = [], 0
    for turn in recent_turns(req.messages):
        matches = find_secrets(turn.content)
        turn_hits += len(matches)
        turns.append({"role": turn.role, "content": redact(turn.content, matches) if matches else turn.content})
    return [{"role": "system", "content": system}, *turns], len(file_hits) + turn_hits


def recent_turns(messages: list[ChatTurn]) -> list[ChatTurn]:
    """Keeps the newest turns that fit the history budget; the latest question is always kept."""
    kept, used = [], 0
    for turn in reversed(messages):
        if kept and used + len(turn.content) > MAX_HISTORY_CHARS:
            break
        kept.append(turn)
        used += len(turn.content)
    return list(reversed(kept))


async def chat_events(req: CodeChatRequest, llm, track: Callable[[Usage], UsageInfo]) -> AsyncIterator[tuple[str, dict]]:
    """Yields (event, data) pairs: start, delta*, then done or error."""
    messages, secrets_redacted = build_messages(req)
    yield "start", {"model": llm.model, "secrets_redacted": secrets_redacted}
    outcome = StreamOutcome()
    async for event in relay(llm, messages, "chat", outcome):
        yield event
    if not outcome.failed:
        yield done_event(outcome, secrets_redacted, llm, track)
