
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from src.ollama_agent import RepairResponse
from src.orchestrator import PipelineOrchestrator

CORRECTED_C = r'''#include <stdio.h>

int main(void) {
    int values[5];
    int i;

    for (i = 0; i < 5; i++) {
        values[i] = i * 10;
    }

    printf("Last value: %d\n", values[4]);
    return 0;
}
'''


class TestBenchmarkBehavior(unittest.TestCase):
    def test_case_01_corrected_program_output(self):
        with tempfile.TemporaryDirectory(
            prefix="safetransit_case01_"
        ) as temp_dir:
            source = Path(temp_dir) / "case01.c"
            executable = Path(temp_dir) / "case01.exe"
            source.write_text(CORRECTED_C, encoding="utf-8")

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

            self.assertEqual(
                compile_result.returncode,
                0,
                msg=compile_result.stderr,
            )

            run_result = subprocess.run(
                [str(executable)],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            self.assertEqual(run_result.returncode, 0)
            self.assertEqual(
                run_result.stdout,
                "Last value: 40\n",
            )


    def test_orchestrator_repair_candidate_preserves_expected_output(self):
        original_source = r'''#include <stdio.h>

int main(void) {
    int values[5];
    int i;

    for (i = 0; i <= 5; i++) {
        values[i] = i * 10;
    }

    printf("Last value: %d\n", values[4]);
    return 0;
}
'''

        agent = Mock()
        verifier = Mock()
        verifier.write_source.return_value = None

        # Simulate the compiler accepting the candidate.
        verifier.check_c_compilation.side_effect = [
    Mock(
        tool="gcc",
        diagnostics=["Simulated initial verification failure"],
        completed=True,
    ),
    Mock(
        tool="gcc",
        diagnostics=[],
        completed=True,
    ),
]
        agent.repair.return_value = RepairResponse(
            raw_output=CORRECTED_C,
            cleaned_code=CORRECTED_C,
        )

        pipeline = PipelineOrchestrator(
            agent=agent,
            verifier=verifier,
        )

        result = pipeline.execute_migration_pipeline(
            original_source,
            language="c",
        )

        self.assertTrue(result["verified"])
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["code"], CORRECTED_C)
        self.assertEqual(result["attempts_used"], 2)
        agent.repair.assert_called_once()

        with tempfile.TemporaryDirectory(
            prefix="safetransit_repair_"
        ) as temp_dir:
            source = Path(temp_dir) / "repaired.c"
            executable = Path(temp_dir) / "repaired.exe"
            source.write_text(result["code"], encoding="utf-8")

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

            self.assertEqual(
                compile_result.returncode,
                0,
                msg=compile_result.stderr,
            )

            run_result = subprocess.run(
                [str(executable)],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            self.assertEqual(run_result.returncode, 0)
            self.assertEqual(run_result.stdout, "Last value: 40\n")

if __name__ == "__main__":
    unittest.main(verbosity=2)
