import pytest

from cost_tracker import CostTracker
from llm_client import LLMClient


@pytest.fixture
def llm_env(monkeypatch):
    monkeypatch.setenv("AZURE_ENDPOINT", "https://example.openai.azure.com/")
    monkeypatch.setenv("AZURE_API_KEY", "test")
    for name in ("LLM_MODEL", "LLM_REASONING", "LLM_REASONING_EFFORT"):
        monkeypatch.delenv(name, raising=False)

    def _make(deployment: str) -> LLMClient:
        monkeypatch.setenv("DEPLOYMENT_NAME", deployment)
        return LLMClient()

    return _make


def test_reasoning_models_use_completion_token_budget_without_temperature(llm_env):
    kwargs = llm_env("gpt-5-mini")._request_kwargs("review")
    assert kwargs["max_completion_tokens"] == 16000
    assert kwargs["reasoning_effort"] == "medium"
    assert kwargs["response_format"] == {"type": "json_object"}
    assert "temperature" not in kwargs and "max_tokens" not in kwargs


def test_non_reasoning_models_use_max_tokens_and_temperature(llm_env):
    kwargs = llm_env("Llama-3.3-70B-Instruct")._request_kwargs("generate")
    assert kwargs["max_tokens"] == 4096
    assert kwargs["temperature"] == 0.2
    assert "max_completion_tokens" not in kwargs and "response_format" not in kwargs


def test_reasoning_effort_override(llm_env, monkeypatch):
    monkeypatch.setenv("LLM_REASONING_EFFORT", "high")
    assert llm_env("gpt-5-mini")._request_kwargs("chat")["reasoning_effort"] == "high"


def test_cost_tracker_prices_known_models(tmp_path):
    record = CostTracker("gpt-5-mini", tmp_path / "usage.db").track_request(10_000, 2_000, task="review")
    assert record["total_cost"] == pytest.approx(0.0025 + 0.004)


def test_usage_totals_survive_restarts_and_separate_sessions(tmp_path):
    db = tmp_path / "data" / "usage.db"
    first = CostTracker("gpt-5-mini", db)
    first.track_request(10_000, 2_000, task="review")
    first.track_request(1_000, 1_000, task="chat")

    restarted = CostTracker("Llama-3.3-70B-Instruct", db)
    restarted.track_request(1_000, 0, task="chat")
    usage = restarted.get_current_usage()

    assert usage["total_requests"] == 3
    assert usage["total_tokens"] == 15_000
    assert usage["total_cost_usd"] == pytest.approx(0.0065 + 0.00225 + 0.00315, abs=1e-4)
    assert usage["tracking_since"] is not None
    assert usage["session"]["requests"] == 1
    assert usage["session"]["total_tokens"] == 1_000
    assert [m["model"] for m in usage["by_model"]] == ["gpt-5-mini", "Llama-3.3-70B-Instruct"]


def test_request_history_is_oldest_first_and_limited(tmp_path):
    tracker = CostTracker("gpt-5-mini", tmp_path / "usage.db")
    for tokens in (1, 2, 3):
        tracker.track_request(tokens, 0, task="chat")
    assert [r["input_tokens"] for r in tracker.get_request_history(2)] == [2, 3]
    assert tracker.get_request_history(0) == []
    assert tracker.reset_tracking()["total_requests"] == 0


def test_cost_tracker_unknown_model_costs_zero(tmp_path):
    assert CostTracker("mystery-model", tmp_path / "usage.db").track_request(1000, 1000, task="chat")["total_cost"] == 0.0
