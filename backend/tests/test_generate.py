import httpx
import openai

from assist.streaming import extract_files
from conftest import FakeLLM, parse_sse

ANSWER = """- Add a cart service

```python path=src/cart.py
def total(items):
    return sum(items)
```

```bash
pytest
```

```ts path="web/src/api.ts"
export const x = 1
```

Notes: run pytest.
"""


def test_extract_files_reads_path_annotated_fences_only():
    files = extract_files(ANSWER)
    assert [(f.path, f.language) for f in files] == [("src/cart.py", "python"), ("web/src/api.ts", "ts")]
    assert files[0].content == "def total(items):\n    return sum(items)\n"


def test_extract_files_keeps_last_version_of_a_path():
    text = "```python path=a.py\nv1\n```\n\n```python path=a.py\nv2\n```\n"
    assert [f.content for f in extract_files(text)] == ["v2\n"]


def test_generate_streams_deltas_then_done(make_client):
    chunks = [ANSWER[:40], ANSWER[40:]]
    llm = FakeLLM(stream_chunks=chunks)
    response = make_client(llm).post(
        "/v1/generate",
        json={
            "mode": "refactor",
            "request": "Make it typed",
            "context": {"files": [{"path": "src/cart.py", "content": 'KEY = "AKIAIOSFODNN7EXAMPLE"\n'}]},
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(response.text)
    assert [name for name, _ in events] == ["start", "delta", "delta", "done"]
    assert events[0][1] == {"model": "fake-model", "secrets_redacted": 1}
    done = events[-1][1]
    assert done["text"] == ANSWER
    assert [f["path"] for f in done["files"]] == ["src/cart.py", "web/src/api.ts"]
    assert done["truncated"] is False
    assert done["usage"]["total_tokens"] == 600
    assert "AKIAIOSFODNN7EXAMPLE" not in llm.prompt_text()
    assert "Make it typed" in llm.prompt_text()


def test_generate_reports_model_errors_as_event(make_client):
    error = openai.APIConnectionError(request=httpx.Request("POST", "https://example.invalid"))
    llm = FakeLLM(stream_chunks=["partial"], stream_error=error)
    response = make_client(llm).post("/v1/generate", json={"mode": "new", "request": "Write a hello world"})
    events = parse_sse(response.text)
    assert [name for name, _ in events] == ["start", "delta", "error"]
    assert "Could not reach the model endpoint" in events[-1][1]["message"]


def test_generate_validates_mode_inputs(make_client):
    client = make_client(FakeLLM())
    assert client.post("/v1/generate", json={"mode": "refactor", "request": ""}).status_code == 422
    assert client.post("/v1/generate", json={"mode": "complete", "request": "finish it"}).status_code == 422
    assert client.post("/v1/generate", json={"mode": "new", "request": "  "}).status_code == 422
