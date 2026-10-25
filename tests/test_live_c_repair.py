"""Live integration test for Ollama-backed C code repair."""

from pprint import pprint

from src.config import MAX_REPAIR_ATTEMPTS
from src.ollama_agent import OllamaRepairAgent, clean_code_output
from src.ollama_client import OllamaClient
from src.orchestrator import PipelineOrchestrator
from src.verifier import VerificationRunner

INVALID_C = """
#include <stdio.h>

int main(void) {
    int value = ;
    printf("%d\\n", value);
    return 0;
}
"""


def test_live_ollama_repairs_invalid_c():
    """Verify real Ollama repair produces C code accepted by GCC."""
    client = OllamaClient(timeout=180)
    agent = OllamaRepairAgent(
        client=client,
        cleanup_fn=clean_code_output,
    )
    verifier = VerificationRunner()
    pipeline = PipelineOrchestrator(
        agent=agent,
        verifier=verifier,
        max_attempts=MAX_REPAIR_ATTEMPTS,
    )

    result = pipeline.execute_migration_pipeline(
        INVALID_C,
        language="c",
    )

    print("\n=== LIVE C REPAIR RESULT ===")
    pprint(result)

    assert isinstance(result, dict)
    assert result["status"] == "verified"
    assert result["verified"] is True
    assert result["language"] == "c"
    assert result["attempts_used"] >= 2
    assert result["attempts_used"] <= MAX_REPAIR_ATTEMPTS
    assert result["attempt_history"][0]["status"] == "verification_failed"
    assert result["attempt_history"][-1]["status"] == "verified"
    assert result["verification"]["passed"] is True
    assert result["verification"]["complete"] is True
    assert "gcc" in result["verification"]["tools_run"]
    assert result["diagnostics"] == []
