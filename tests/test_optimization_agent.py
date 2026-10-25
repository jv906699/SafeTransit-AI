
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.ollama_agent import OllamaRepairAgent, clean_code_output
from src.orchestrator import PipelineOrchestrator


def make_agent(response_text="def find_user(ids, target):\n    return target in set(ids)\n"):
    client = Mock()
    client.generate.return_value = SimpleNamespace(
        response=response_text,
        model="qwen2.5-coder:7b-instruct",
        total_duration_ns=1_000_000_000,
        prompt_eval_count=100,
        eval_count=40,
        eval_duration_ns=800_000_000,
    )
    return OllamaRepairAgent(client=client, cleanup_fn=clean_code_output), client


def test_optimize_method_exists_without_breaking_repair():
    agent, _ = make_agent()
    assert callable(agent.repair)
    assert callable(agent.optimize)


def test_optimize_uses_language_aware_prompt_and_returns_metrics():
    candidate = "def find_user(ids, target):\n    return target in set(ids)"
    agent, client = make_agent(candidate)

    result = agent.optimize(
        source_code=(
            "def find_user(ids, target):\n"
            "    for item in ids:\n"
            "        if item == target:\n"
            "            return True\n"
            "    return False"
        ),
        language="python",
    )

    assert result.cleaned_code == candidate
    assert result.model == "qwen2.5-coder:7b-instruct"
    assert result.total_duration_ns == 1_000_000_000
    assert result.prompt_eval_count == 100
    assert result.eval_count == 40

    call = client.generate.call_args
    assert "PYTHON" in call.kwargs["system"]
    assert "performance" in call.kwargs["system"].lower()
    assert call.kwargs["temperature"] == 0.1


@pytest.mark.parametrize(
    ("source_code", "language"),
    [("", "python"), ("   ", "c")],
)
def test_optimize_rejects_empty_source(source_code, language):
    agent, client = make_agent()

    with pytest.raises(ValueError, match="Source code cannot be empty"):
        agent.optimize(source_code, language)

    client.generate.assert_not_called()


def test_optimize_rejects_unsupported_language():
    agent, client = make_agent()

    with pytest.raises(ValueError, match="Unsupported language"):
        agent.optimize("some code", "javascript")

    client.generate.assert_not_called()


def test_optimize_rejects_empty_model_output():
    agent, client = make_agent("```")

    with pytest.raises(ValueError, match="empty optimization output"):
        agent.optimize("print('hello')", "python")

    client.generate.assert_called_once()


def make_orchestrator(candidate_code):
    agent, _ = make_agent(candidate_code)
    orchestrator = PipelineOrchestrator(agent=agent)
    orchestrator._verify = Mock(
        side_effect=[
            {"passed": True, "complete": True, "language": "python",
             "diagnostics": [], "tools_run": ["tree_sitter"]},
            {"passed": True, "complete": True, "language": "python",
             "diagnostics": [], "tools_run": ["tree_sitter"]},
        ]
    )
    return orchestrator


def test_optimization_pipeline_returns_verified_candidate():
    candidate = "def find_user(ids, target):\n    return target in set(ids)"
    orchestrator = make_orchestrator(candidate)

    result = orchestrator.execute_optimization_pipeline(
        "def find_user(ids, target):\n    return False",
        language="python",
    )

    assert result["status"] == "verified"
    assert result["verified"] is True
    assert result["code"] == candidate
    assert result["optimization_candidate_verified"] is True
    assert result["optimization_applied"] is True
    assert result["attempt_history"][0]["inference_metrics"]["generated_tokens"] == 40


def test_failed_candidate_keeps_original_source():
    original = "def find_user(ids, target):\n    return False"
    candidate = "def find_user(ids, target):\n    return target in set(ids)"
    orchestrator = make_orchestrator(candidate)
    orchestrator._verify = Mock(
        side_effect=[
            {"passed": True, "complete": True, "language": "python",
             "diagnostics": [], "tools_run": ["tree_sitter"]},
            {"passed": False, "complete": True, "language": "python",
             "diagnostics": ["Candidate failed a check"], "tools_run": ["tree_sitter"]},
        ]
    )

    result = orchestrator.execute_optimization_pipeline(original, "python")

    assert result["verified"] is False
    assert result["code"] == original
    assert result["optimization_applied"] is False
    assert result["optimization_candidate"] == candidate


def test_original_verification_failure_stops_optimization():
    agent, _ = make_agent()
    orchestrator = PipelineOrchestrator(agent=agent)
    orchestrator._verify = Mock(
        return_value={
            "passed": False,
            "complete": True,
            "language": "python",
            "diagnostics": ["Original source failed"],
            "tools_run": ["tree_sitter"],
        }
    )
    agent.optimize = Mock()

    result = orchestrator.execute_optimization_pipeline(
        "def broken(:",
        language="python",
    )

    assert result["status"] == "original_verification_failed"
    assert result["optimization_applied"] is False
    agent.optimize.assert_not_called()
