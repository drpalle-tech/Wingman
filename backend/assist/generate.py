"""Code generation: build the prompt, then stream the model's answer and the files it wrote."""

from typing import AsyncIterator, Callable

from llm_client import Usage

from .context import detect_project, render_bundle, selected_text
from .prompting import system_prompt
from .schemas import GenerateRequest, UsageInfo
from .secret_scan import redact_bundle
from .streaming import StreamOutcome, done_event, relay

MODE_INSTRUCTIONS = {
    "new": "Write new code for the request below. Put new files at paths that fit the project layout.",
    "complete": (
        "Complete the unfinished code in the target files: implement stubs, TODOs and missing branches so each "
        "file works as clearly intended. Leave code that already works unchanged."
    ),
    "refactor": (
        "Refactor the target files as requested below without changing externally observable behavior unless "
        "the request asks for it. Explain notable changes in Notes."
    ),
}


def build_messages(req: GenerateRequest) -> tuple[list[dict], int]:
    bundle, secret_hits = redact_bundle(req.context)
    project = detect_project(bundle.files, bundle.project)
    lines = [MODE_INSTRUCTIONS[req.mode]]
    if req.request.strip():
        lines += ["", "Request:", req.request.strip()]
    selection = selected_text(bundle)
    if selection is not None and bundle.selection is not None:
        s = bundle.selection
        lines += [
            "",
            f"Limit changes to {s.path} lines {s.start_line}-{s.end_line} unless the change requires touching "
            "other code. The selected code is:",
            "```",
            selection,
            "```",
        ]
    if bundle.files:
        lines += ["", render_bundle(bundle, project, number_targets=False)]
    messages = [
        {"role": "system", "content": system_prompt("generate", bundle, project)},
        {"role": "user", "content": "\n".join(lines)},
    ]
    return messages, len(secret_hits)


async def generate_events(
    req: GenerateRequest, llm, track: Callable[[Usage], UsageInfo]
) -> AsyncIterator[tuple[str, dict]]:
    """Yields (event, data) pairs: start, delta*, then done or error."""
    messages, secrets_redacted = build_messages(req)
    yield "start", {"model": llm.model, "secrets_redacted": secrets_redacted}
    outcome = StreamOutcome()
    async for event in relay(llm, messages, "generate", outcome):
        yield event
    if not outcome.failed:
        yield done_event(outcome, secrets_redacted, llm, track)
