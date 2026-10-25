import unittest
from unittest.mock import Mock

from src.ollama_agent import RepairResponse
from src.orchestrator import PipelineOrchestrator

VALID_C = """
#include <stdio.h>

int main(void) {
    printf("Hello\\n");
    return 0;
}
"""

INVALID_C = """
int main(void) {
    int value = ;
    return 0;
}
"""


class TestPipelineOrchestrator(unittest.TestCase):

    def setUp(self):
        self.agent = Mock()
        self.verifier = Mock()

        self.verifier.write_source.return_value = None
        self.verifier.check_c_compilation.return_value = Mock(
            tool="gcc",
            diagnostics=[],
            completed=True,
        )

        self.pipeline = PipelineOrchestrator(
            agent=self.agent,
            verifier=self.verifier,
        )

    def test_valid_c_can_be_verified_after_compilation(self):
        result = self.pipeline.execute_migration_pipeline(VALID_C)

        self.assertTrue(result["verified"])
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["attempts_used"], 1)
        self.agent.repair.assert_not_called()
        self.verifier.check_c_compilation.assert_called_once()

    def test_invalid_c_triggers_repair_attempt(self):
        self.agent.repair.return_value = RepairResponse(
            raw_output=VALID_C,
            cleaned_code=VALID_C,
        )

        result = self.pipeline.execute_migration_pipeline(INVALID_C)

        self.assertTrue(result["verified"])
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["attempts_used"], 2)
        self.agent.repair.assert_called_once()

    def test_previous_failure_is_included_in_repair_context(self):
        self.agent.repair.return_value = RepairResponse(
            raw_output=VALID_C,
            cleaned_code=VALID_C,
        )

        result = self.pipeline.execute_migration_pipeline(INVALID_C)

        self.assertTrue(result["verified"])
        self.agent.repair.assert_called_once()

        repaired_source, repair_context = (
            self.agent.repair.call_args.args
        )

        self.assertEqual(repaired_source, INVALID_C)
        self.assertIn("PREVIOUS REPAIR CONVERSATION HISTORY", repair_context)
        self.assertIn("Source code:", repair_context)
        self.assertIn("int value = ;", repair_context)
        self.assertIn("Tree-sitter detected syntax errors", repair_context)
        self.assertIn("Outcome: verification_failed", repair_context)


    def test_history_accumulates_across_multiple_failed_attempts(self):
        first_repair = """
int main(void) {
    int value = ;
    return 0;
}
"""
        second_repair = VALID_C

        self.agent.repair.side_effect = [
            RepairResponse(
                raw_output=first_repair,
                cleaned_code=first_repair,
            ),
            RepairResponse(
                raw_output=second_repair,
                cleaned_code=second_repair,
            ),
        ]

        result = self.pipeline.execute_migration_pipeline(INVALID_C)

        self.assertTrue(result["verified"])
        self.assertEqual(result["attempts_used"], 3)
        self.assertEqual(self.agent.repair.call_count, 2)

        second_call_context = self.agent.repair.call_args_list[1].args[1]

        self.assertIn("PREVIOUS REPAIR CONVERSATION HISTORY", second_call_context)
        self.assertIn("int value = ;", second_call_context)
        self.assertIn("Attempt 2:", second_call_context)
        self.assertIn("Outcome: verification_failed", second_call_context)


    def test_inference_failure_is_reported(self):
        self.agent.repair.side_effect = RuntimeError(
            "Ollama unavailable"
        )

        result = self.pipeline.execute_migration_pipeline(INVALID_C)

        self.assertEqual(result["status"], "inference_failed")
        self.assertFalse(result["verified"])
        self.assertIn(
            "Ollama unavailable",
            result["diagnostics"][0],
        )

    def test_attempt_limit_is_capped_at_configured_maximum(self):
        pipeline = PipelineOrchestrator(
            agent=self.agent,
            verifier=self.verifier,
            max_attempts=100,
        )

        self.assertEqual(pipeline.max_attempts, 4)

    def test_pipeline_stops_after_four_failed_repairs(self):
        self.agent.repair.return_value = RepairResponse(
            raw_output=INVALID_C,
            cleaned_code=INVALID_C,
        )

        result = self.pipeline.execute_migration_pipeline(INVALID_C)

        self.assertEqual(result["status"], "max_attempts_reached")
        self.assertFalse(result["verified"])
        self.assertEqual(result["attempts_used"], 4)
        self.assertEqual(self.agent.repair.call_count, 3)

    def test_incomplete_verification_stops_pipeline(self):
        self.verifier.check_c_compilation.return_value = Mock(
            tool="gcc",
            diagnostics=[],
            completed=False,
        )

        result = self.pipeline.execute_migration_pipeline(VALID_C)

        self.assertEqual(result["status"], "verification_incomplete")
        self.assertFalse(result["verified"])
        self.assertEqual(result["attempts_used"], 1)
        self.agent.repair.assert_not_called()


    def test_python_security_finding_does_not_pass_verification(self):
        from src.verifier import (
            StaticAnalysisResult,
            VerificationDiagnostic,
        )

        self.verifier.analyze_python.return_value = StaticAnalysisResult(
            syntax_valid=True,
            diagnostics=[
                VerificationDiagnostic(
                    tool="bandit",
                    severity="low",
                    message="Possible hardcoded password",
                    code="B105",
                    classification="security_finding",
                )
            ],
            tools_run=["python_ast", "mypy", "bandit"],
            analysis_complete=True,
            failed_tools=[],
        )

        self.agent.repair.return_value = RepairResponse(
            raw_output='password = "hardcoded-secret"\n',
            cleaned_code='password = "hardcoded-secret"\n',
        )

        result = self.pipeline.execute_migration_pipeline(
            'password = "hardcoded-secret"\n',
            language="python",
        )

        self.assertFalse(result["verified"])
        self.assertNotEqual(result["status"], "verified")


    def test_empty_source_is_rejected(self):
        with self.assertRaises(ValueError):
            self.pipeline.execute_migration_pipeline("   ")


if __name__ == "__main__":
    unittest.main()
