import json

from assist.review import ground_findings, locate, parse_json_object
from assist.schemas import ContextBundle, ContextFile
from conftest import FakeLLM

SOURCE = """import json


def load(paths, cache={}):
    for path in paths:
        handle = open(path)

        cache[path] = json.load(handle)
    return cache
"""


def review_json(*findings, summary="Two problems.") -> str:
    return json.dumps({"summary": summary, "findings": list(findings)})


def finding(**overrides) -> dict:
    base = {
        "severity": "major",
        "category": "leak",
        "path": "app/loader.py",
        "line": 6,
        "quote": "handle = open(path)",
        "title": "File handle never closed",
        "explanation": "Each call leaks a file descriptor.",
        "suggestion": "Use a with block.",
        "suggested_code": None,
    }
    return {**base, **overrides}


def test_locate_exact_and_whitespace_insensitive():
    assert locate(SOURCE, "handle = open(path)", None) == (6, 6)
    assert locate(SOURCE, "   handle   =  open(path)", None) == (6, 6)


def test_locate_multiline_quote_skips_blank_lines_in_file():
    assert locate(SOURCE, "handle = open(path)\ncache[path] = json.load(handle)", None) == (6, 8)


def test_locate_partial_line_and_nearest_to_hint():
    text = "total = 0\nprint('start')\nx = compute()\nprint('start')\n"
    assert locate(text, "print('start')", 4) == (4, 4)
    assert locate(text, "print('start')", 1) == (2, 2)
    assert locate(SOURCE, "open(path)", None) == (6, 6)


def test_locate_returns_none_when_quote_is_not_in_file():
    assert locate(SOURCE, "os.remove(path)", 3) is None


def test_parse_json_object_handles_fences_and_prose():
    assert parse_json_object('{"a": 1}') == {"a": 1}
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_object('Here you go:\n{"a": 1}\nThanks') == {"a": 1}
    assert parse_json_object("not json") is None
    assert parse_json_object("[1, 2]") is None


def test_ground_findings_normalizes_and_grounds():
    bundle = ContextBundle(files=[ContextFile(path="app/loader.py", content=SOURCE)])
    raw = [
        finding(line=40, quote="  6 | handle = open(path)"),
        finding(severity="HIGH", category="bug", quote="def load(paths, cache={}):", line="4"),
        finding(quote="not in the file", line=9, severity="whatever", category="nonsense"),
        finding(path="other/file.py"),
        finding(quote='KEY = "[REDACTED:api-key]"'),
        {"severity": "minor"},
    ]
    results = ground_findings(raw, bundle)
    assert [(f.start_line, f.anchored) for f in results] == [(6, True), (4, True), (9, False), (6, True)]
    assert results[0].quote == "handle = open(path)"
    assert (results[1].severity, results[1].category) == ("major", "correctness")
    assert (results[2].severity, results[2].category) == ("minor", "maintainability")
    assert results[3].path == "app/loader.py"  # single target: unknown path falls back to it


def test_ground_findings_drops_unknown_path_with_several_targets():
    bundle = ContextBundle(
        files=[ContextFile(path="a.py", content=SOURCE), ContextFile(path="b.py", content=SOURCE)]
    )
    assert ground_findings([finding(path="c.py")], bundle) == []


def test_review_endpoint_grounds_findings_and_hides_secrets(make_client):
    secret = "AKIAIOSFODNN7EXAMPLE"
    content = SOURCE + f'\nAWS_KEY = "{secret}"\n'
    llm = FakeLLM(replies=[review_json(finding(), finding(severity="minor", category="correctness", line=4, quote="def load(paths, cache={}):", title="Mutable default"))])
    client = make_client(llm)

    response = client.post(
        "/v1/review",
        json={"context": {"files": [{"path": "app/loader.py", "content": content}]}, "focus": ["leaks"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert [(f["id"], f["source"], f["severity"], f["start_line"]) for f in body["findings"]] == [
        ("F1", "secret-scan", "critical", 11),
        ("F2", "model", "major", 6),
        ("F3", "model", "minor", 4),
    ]
    assert body["summary"] == "Two problems."
    assert body["usage"] == {"input_tokens": 1000, "output_tokens": 200, "total_tokens": 1200, "cost_usd": 0.0}
    assert secret not in llm.prompt_text()
    assert " 6 | " in llm.prompt_text()
    assert "Focus: leaks" in llm.prompt_text()


def test_review_repairs_invalid_json_once(make_client):
    llm = FakeLLM(replies=["Sure! findings: severity major...", review_json(finding())])
    response = make_client(llm).post(
        "/v1/review", json={"context": {"files": [{"path": "app/loader.py", "content": SOURCE}]}}
    )
    assert response.status_code == 200
    assert len(llm.calls) == 2
    assert response.json()["usage"]["input_tokens"] == 2000


def test_review_fails_cleanly_when_output_stays_invalid(make_client):
    llm = FakeLLM(replies=["nope", "still nope"])
    response = make_client(llm).post(
        "/v1/review", json={"context": {"files": [{"path": "app/loader.py", "content": SOURCE}]}}
    )
    assert response.status_code == 502
    assert "valid review" in response.json()["detail"]


def test_review_requires_a_target_file(make_client):
    response = make_client(FakeLLM()).post(
        "/v1/review", json={"context": {"files": [{"path": "package.json", "content": "{}", "role": "config"}]}}
    )
    assert response.status_code == 422


def test_review_rejects_oversized_context(make_client, monkeypatch):
    monkeypatch.setenv("MAX_CONTEXT_CHARS", "10")
    response = make_client(FakeLLM()).post(
        "/v1/review", json={"context": {"files": [{"path": "a.py", "content": "x" * 11}]}}
    )
    assert response.status_code == 413
