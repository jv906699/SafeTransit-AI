
"""Live integration test for unsafe-array repair using Ollama."""

import subprocess
import tempfile
from pathlib import Path
from pprint import pprint

from src.config import MAX_REPAIR_ATTEMPTS
from src.ollama_agent import OllamaRepairAgent, clean_code_output
from src.ollama_client import OllamaClient
from src.orchestrator import PipelineOrchestrator
from src.verifier import VerificationRunner

BENCHMARK_CASE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "benchmarks"
    / "legacy_cases"
    / "case_01_unsafe_array.c"
)

EXPECTED_OUTPUT = "Last value: 40\n"


def test_live_ollama_repairs_unsafe_array():
    """Check a live repair, then compile and run its returned candidate."""
    original_code = BENCHMARK_CASE.read_text(encoding="utf-8")

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
        original_code,
        language="c",
    )

    print("\n=== LIVE UNSAFE-ARRAY REPAIR RESULT ===")
    pprint(result)

    assert result["status"] == "verified", result
    assert result["verified"] is True
    assert result["language"] == "c"
    assert 1 <= result["attempts_used"] <= MAX_REPAIR_ATTEMPTS
    assert result["verification"]["passed"] is True
    assert result["verification"]["complete"] is True
    assert "gcc" in result["verification"]["tools_run"]

    repaired_code = result["code"]
    assert repaired_code.strip(), "Repair returned empty source code."

    # Verify actual execution behavior independently of the pipeline.
    with tempfile.TemporaryDirectory(
        prefix="safetransit_live_array_"
    ) as temp_dir:
        source = Path(temp_dir) / "repaired.c"
        executable = Path(temp_dir) / "repaired.exe"
        source.write_text(repaired_code, encoding="utf-8")

        compile_result = subprocess.run(
            [
                "gcc",
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Werror",
                str(source),
                "-o",
                str(executable),
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        assert compile_result.returncode == 0, compile_result.stderr

        run_result = subprocess.run(
            [str(executable)],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        assert run_result.returncode == 0, run_result.stderr
        assert run_result.stdout == EXPECTED_OUTPUT
