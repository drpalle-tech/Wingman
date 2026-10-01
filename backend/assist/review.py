"""Code review: build the prompt, call the model, then validate and ground its findings."""

import json
import logging
import re
from typing import Any, Callable, Optional

from errors import UpstreamError
from llm_client import Completion, Usage

from .context import detect_project, render_bundle
from .prompting import system_prompt
from .schemas import ContextBundle, Finding, ProjectInfo, ReviewRequest, ReviewResponse, UsageInfo
from .secret_scan import SecretHit, redact_bundle

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {"critical": 0, "major": 1, "minor": 2, "info": 3}
SEVERITY_ALIASES = {
    "blocker": "critical", "high": "major", "error": "major", "medium": "minor",
    "warning": "minor", "low": "info", "suggestion": "info", "nit": "info",
}
CATEGORIES = {
    "correctness", "security", "leak", "performance", "concurrency",
    "error-handling", "design", "maintainability", "testing",
}
CATEGORY_ALIASES = {
    "leaks": "leak", "memory": "leak", "resource": "leak", "resource-leak": "leak", "memory-leak": "leak",
    "bug": "correctness", "logic": "correctness", "errors": "error-handling", "error handling": "error-handling",
    "async": "concurrency", "threading": "concurrency", "style": "maintainability", "readability": "maintainability",
}

REPAIR_PROMPT = (
    "Convert the following text into valid JSON. Return only a JSON object with keys "
    '"summary" (string) and "findings" (array of objects with severity, category, path, line, quote, '
    "title, explanation, suggestion, suggested_code). Keep the content; fix only the structure."
)
LINE_PREFIX = re.compile(r"^\s*\d+\s*\|\s?")


async def run_review(req: ReviewRequest, llm, track: Callable[[Usage], UsageInfo]) -> ReviewResponse:
    spent = Usage()

    async def call(messages: list[dict]) -> Completion:
        nonlocal spent
        completion = await llm.complete(messages, "review")
        spent = spent + completion.usage
        return completion

    try:
        summary, findings = await _review(req, call)
    except Exception:
        if spent.total_tokens:
            track(spent)
        raise
    return ReviewResponse(summary=summary, findings=findings, model=llm.model, usage=track(spent))


async def _review(req: ReviewRequest, call) -> tuple[str, list[Finding]]:
    bundle, secret_hits = redact_bundle(req.context)
    project = detect_project(bundle.files, bundle.project)
    completion = await call(
        [
            {"role": "system", "content": system_prompt("review", bundle, project)},
            {"role": "user", "content": _user_message(req, bundle, project)},
        ]
    )
    if completion.finish_reason == "content_filter":
        raise UpstreamError("The model's content filter blocked this review.")
    if not completion.text.strip():
        raise UpstreamError("The model ran out of output tokens before answering. Review a smaller selection.")

    data = parse_json_object(completion.text)
    if data is None:
        logger.warning("Review output was not valid JSON; asking the model to repair it")
        repaired = await call([{"role": "user", "content": f"{REPAIR_PROMPT}\n\n{completion.text}"}])
        data = parse_json_object(repaired.text)
    if data is None:
        raise UpstreamError("The model did not return a valid review. Try again or review a smaller selection.")

    findings = [_secret_finding(hit) for hit in secret_hits]
    findings += ground_findings(data.get("findings"), bundle)
    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.path, f.start_line or 10**9))
    for number, finding in enumerate(findings, 1):
        finding.id = f"F{number}"
    summary = _text(data.get("summary")) or "No summary returned."
    return summary, findings


def _user_message(req: ReviewRequest, bundle: ContextBundle, project: ProjectInfo) -> str:
    focus = ", ".join(req.focus) if req.focus else "all categories"
    lines = [f"Review the target files. Focus: {focus}."]
    if bundle.selection:
        s = bundle.selection
        lines.append(
            f"Concentrate on {s.path} lines {s.start_line}-{s.end_line}. "
            "Report issues elsewhere only if they are critical or directly related."
        )
    if req.instructions and req.instructions.strip():
        lines.append(f"Developer notes: {req.instructions.strip()}")
    lines += ["", render_bundle(bundle, project, number_targets=True)]
    return "\n".join(lines)


def parse_json_object(text: str) -> Optional[dict]:
    text = text.strip()
    candidates = [text]
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fenced:
        candidates.append(fenced.group(1))
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return None


def ground_findings(raw: Any, bundle: ContextBundle) -> list[Finding]:
    if not isinstance(raw, list):
        return []
    targets = bundle.targets()
    findings = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = _text(item.get("title"))
        explanation = _text(item.get("explanation") or item.get("message") or item.get("description"))
        if not (title or explanation):
            continue
        quote = "\n".join(LINE_PREFIX.sub("", line) for line in _text(item.get("quote")).splitlines()).strip()
        if "[REDACTED:" in quote:
            continue  # already reported by the secret scanner

        path = _text(item.get("path"))
        file = bundle.file_by_path(path) if path else None
        if file is None and len(targets) == 1:
            file = targets[0]
        if file is None:
            logger.info("Dropping a finding that points at a file not in the bundle")
            continue

        hint = _coerce_line(item.get("line"))
        location = locate(file.content, quote, hint) if quote else None
        anchored = location is not None
        if location is None and hint is not None and hint <= len(file.content.splitlines()):
            location = (hint, hint)

        findings.append(
            Finding(
                id="",
                severity=_severity(item.get("severity")),
                category=_category(item.get("category")),
                path=file.path,
                start_line=location[0] if location else None,
                end_line=location[1] if location else None,
                anchored=anchored,
                quote=quote,
                title=title or explanation.split(". ")[0][:100],
                message=explanation or title,
                suggestion=_text(item.get("suggestion")),
                suggested_code=_optional_text(item.get("suggested_code")),
            )
        )
    return findings


def locate(content: str, quote: str, hint: Optional[int]) -> Optional[tuple[int, int]]:
    """Finds the quoted code in the file; returns 1-based (start, end) lines closest to the hint."""
    wanted = [_norm(line) for line in quote.splitlines()]
    wanted = [line for line in wanted if line]
    if not wanted:
        return None
    code = [(number, _norm(line)) for number, line in enumerate(content.splitlines(), 1)]
    code = [(number, line) for number, line in code if line]

    matches = []
    for k in range(len(code) - len(wanted) + 1):
        window = code[k : k + len(wanted)]
        if all(_same(q, line) for q, (_, line) in zip(wanted, window)):
            matches.append((window[0][0], window[-1][0]))
    if not matches:
        matches = [(number, number) for number, line in code if _same(wanted[0], line)]
    if not matches:
        return None
    if hint is None:
        return matches[0]
    return min(matches, key=lambda m: abs(m[0] - hint))


def _norm(line: str) -> str:
    return " ".join(line.split())


def _same(quoted: str, actual: str) -> bool:
    return quoted == actual or (len(quoted) >= 8 and quoted in actual)


def _secret_finding(hit: SecretHit) -> Finding:
    return Finding(
        id="",
        severity="critical",
        category="secret-leak",
        path=hit.path,
        start_line=hit.line,
        end_line=hit.line,
        anchored=True,
        quote=hit.masked_line,
        title=f"Hard-coded secret: {hit.title}",
        message="A secret is stored in source code. Anyone with access to the code, its history, build output or logs can use it.",
        suggestion=(
            "Rotate it now, remove it from the code, and load it at runtime from an environment variable or a "
            "secret store (for example Azure Key Vault or .NET user-secrets). Removing it from the latest commit "
            "is not enough; it stays in git history."
        ),
        source="secret-scan",
    )


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _optional_text(value: Any) -> Optional[str]:
    text = _text(value)
    return None if text.lower() in ("", "null", "none") else text


def _coerce_line(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    match = re.search(r"\d+", str(value)) if value is not None else None
    return int(match.group()) if match and int(match.group()) > 0 else None


def _severity(value: Any) -> str:
    severity = _text(value).lower()
    severity = SEVERITY_ALIASES.get(severity, severity)
    return severity if severity in SEVERITY_ORDER else "minor"


def _category(value: Any) -> str:
    category = _text(value).lower().replace("_", "-")
    category = CATEGORY_ALIASES.get(category, category)
    return category if category in CATEGORIES else "maintainability"
