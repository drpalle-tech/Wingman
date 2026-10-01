from assist.chat import MAX_HISTORY_CHARS, recent_turns
from assist.schemas import ChatTurn
from conftest import FakeLLM, parse_sse

SECRET = "AKIAIOSFODNN7EXAMPLE"


def test_chat_streams_answer_with_history_and_files(make_client):
    llm = FakeLLM(stream_chunks=["Use ", "`with open(...)`."])
    response = make_client(llm).post(
        "/v1/chat",
        json={
            "messages": [
                {"role": "user", "content": "What does load() do?"},
                {"role": "assistant", "content": "It reads JSON files."},
                {"role": "user", "content": f"How do I stop it leaking handles? My key is {SECRET}"},
            ],
            "context": {"files": [{"path": "app/loader.py", "content": "handle = open(path)\n", "role": "target"}]},
        },
    )

    assert response.status_code == 200
    events = parse_sse(response.text)
    assert [name for name, _ in events] == ["start", "delta", "delta", "done"]
    assert events[0][1]["secrets_redacted"] == 1
    assert events[-1][1]["text"] == "Use `with open(...)`."

    task, messages = llm.calls[0]
    assert task == "chat"
    assert [m["role"] for m in messages] == ["system", "user", "assistant", "user"]
    assert "1 | handle = open(path)" in messages[0]["content"]
    assert SECRET not in llm.prompt_text()


def test_chat_works_without_files(make_client):
    llm = FakeLLM(stream_chunks=["A race condition is..."])
    response = make_client(llm).post("/v1/chat", json={"messages": [{"role": "user", "content": "What is a race condition?"}]})
    assert [name for name, _ in parse_sse(response.text)] == ["start", "delta", "done"]
    assert "Files the developer shared" not in llm.calls[0][1][0]["content"]


def test_chat_requires_a_user_question_last(make_client):
    client = make_client(FakeLLM())
    assert client.post("/v1/chat", json={"messages": []}).status_code == 422
    assert client.post("/v1/chat", json={"messages": [{"role": "assistant", "content": "hi"}]}).status_code == 422
    assert client.post("/v1/chat", json={"messages": [{"role": "user", "content": "   "}]}).status_code == 422


def test_recent_turns_drops_oldest_beyond_budget_but_keeps_latest():
    old = ChatTurn(role="user", content="x" * MAX_HISTORY_CHARS)
    answer = ChatTurn(role="assistant", content="short answer")
    latest = ChatTurn(role="user", content="follow-up")
    assert recent_turns([old, answer, latest]) == [answer, latest]
    huge = ChatTurn(role="user", content="y" * (MAX_HISTORY_CHARS + 1))
    assert recent_turns([answer, huge]) == [huge]
