"""Deterministic secret detection and redaction, run before any code reaches the model."""

import math
import re
from collections import Counter
from dataclasses import dataclass

from .schemas import ContextBundle


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    pattern: re.Pattern
    group: int = 0
    min_entropy: float = 0.0


# Order is priority: when matches overlap, the earlier rule wins.
RULES = [
    Rule(
        "private-key",
        "Private key",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----"),
    ),
    Rule("azure-storage-key", "Azure Storage account key", re.compile(r"AccountKey=([A-Za-z0-9+/]{40,}={0,2})"), 1),
    Rule("aws-access-key", "AWS access key ID", re.compile(r"\b((?:AKIA|ASIA)[0-9A-Z]{16})\b"), 1),
    Rule("github-token", "GitHub token", re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,})\b"), 1),
    Rule("slack-token", "Slack token", re.compile(r"\b(xox[abposr]-[A-Za-z0-9-]{10,})\b"), 1),
    Rule("google-api-key", "Google API key", re.compile(r"\b(AIza[0-9A-Za-z_\-]{35})\b"), 1),
    Rule("api-key", "API key", re.compile(r"\b(sk-(?:ant-|proj-)?[A-Za-z0-9_\-]{20,})\b"), 1),
    Rule(
        "jwt",
        "JSON Web Token",
        re.compile(r"\b(eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})\b"),
        1,
    ),
    Rule(
        "connection-string-password",
        "Password in a connection string",
        re.compile(r"""(?i)[;"'][ \t]*(?:password|pwd)[ \t]*=[ \t]*([^;'"\s]{4,})"""),
        1,
    ),
    Rule(
        "hardcoded-credential",
        "Hard-coded credential",
        re.compile(
            r"""(?i)\b[\w.-]*?(?:api[_-]?key|secret|token|passw(?:or)?d|access[_-]?key)["']?[ \t]*[:=][ \t]*["']([^"'\s]{8,})["']"""
        ),
        1,
        min_entropy=3.0,
    ),
]

PLACEHOLDER = re.compile(
    r"""(?ix)^(
        <[^>]*> | \$\{[^}]*\} | \{\{?[^}]*\}?\} | %[^%]+% | \$\([^)]*\) |
        \*+ | x+ | \.+ | -+ |
        changeme | change[_-]me | password | secret | redacted | example | dummy | test | todo | none | null |
        your[_-].* | .*placeholder.* | \[REDACTED.*
    )$"""
)


@dataclass(frozen=True)
class SecretMatch:
    rule: Rule
    start: int
    end: int

    def value(self, text: str) -> str:
        return text[self.start : self.end]


@dataclass(frozen=True)
class SecretHit:
    rule_id: str
    title: str
    path: str
    line: int
    masked_line: str


def _entropy(value: str) -> float:
    counts = Counter(value)
    return -sum(n / len(value) * math.log2(n / len(value)) for n in counts.values())


def find_secrets(text: str) -> list[SecretMatch]:
    candidates = []
    for priority, rule in enumerate(RULES):
        for m in rule.pattern.finditer(text):
            start, end = m.span(rule.group)
            value = text[start:end]
            if rule.id != "private-key" and PLACEHOLDER.match(value):
                continue
            if rule.min_entropy and _entropy(value) < rule.min_entropy:
                continue
            candidates.append((priority, SecretMatch(rule, start, end)))

    accepted: list[SecretMatch] = []
    for _, match in sorted(candidates, key=lambda c: (c[0], c[1].start)):
        if all(match.end <= a.start or match.start >= a.end for a in accepted):
            accepted.append(match)
    return sorted(accepted, key=lambda m: m.start)


def redact(text: str, matches: list[SecretMatch]) -> str:
    """Replaces each secret with a placeholder, keeping line numbers unchanged."""
    out, cursor = [], 0
    for m in matches:
        out.append(text[cursor : m.start])
        out.append(f"[REDACTED:{m.rule.id}]" + "\n" * m.value(text).count("\n"))
        cursor = m.end
    out.append(text[cursor:])
    return "".join(out)


def _masked_line(text: str, match: SecretMatch) -> str:
    line_start = text.rfind("\n", 0, match.start) + 1
    line_end = text.find("\n", match.start)
    line = text[line_start : line_end if line_end != -1 else len(text)].rstrip("\r")
    value = match.value(text).split("\n", 1)[0]
    masked = value[:4] + "*" * 8 if match.rule.id != "private-key" else value
    return line.replace(value, masked, 1).strip()


def redact_bundle(bundle: ContextBundle) -> tuple[ContextBundle, list[SecretHit]]:
    files, hits = [], []
    for f in bundle.files:
        matches = find_secrets(f.content)
        if not matches:
            files.append(f)
            continue
        for m in matches:
            hits.append(
                SecretHit(
                    rule_id=m.rule.id,
                    title=m.rule.title,
                    path=f.path,
                    line=f.content.count("\n", 0, m.start) + 1,
                    masked_line=_masked_line(f.content, m),
                )
            )
        files.append(f.model_copy(update={"content": redact(f.content, matches)}))
    return bundle.model_copy(update={"files": files}), hits
