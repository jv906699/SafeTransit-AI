
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.parser import CStructuralAnalyzer


class TestCStructuralAnalyzer(unittest.TestCase):

    def setUp(self) -> None:
        self.analyzer = CStructuralAnalyzer()

    def test_detects_function_definition(self) -> None:
        result = self.analyzer.analyze(
            "int add(int a, int b) { return a + b; }"
        )

        self.assertEqual(result["function_count"], 1)
        self.assertIn("add", result["functions"][0])

    def test_detects_memory_management_calls(self) -> None:
        code = """
        #include <stdlib.h>
        int main(void) {
            int *buffer = malloc(sizeof(int) * 5);
            free(buffer);
            return 0;
        }
        """

        result = self.analyzer.analyze(code)
        calls = result["memory_management_calls"]

        self.assertTrue(any("malloc" in call for call in calls))
        self.assertTrue(any("free" in call for call in calls))


    def test_detects_memory_calls_with_whitespace(self) -> None:
        code = """
        #include <stdlib.h>
        int main(void) {
            int *buffer = malloc (sizeof(int) * 5);
            free (buffer);
            return 0;
        }
        """

        result = self.analyzer.analyze(code)
        calls = result["memory_management_calls"]

        self.assertTrue(any("malloc" in call for call in calls))
        self.assertTrue(any("free" in call for call in calls))

    def test_ignores_memory_function_names_in_comments_and_strings(
        self,
    ) -> None:
        code = r'''
        int main(void) {
            // malloc(10) is mentioned in this comment.
            const char *message = "free(ptr)";
            return 0;
        }
        '''

        result = self.analyzer.analyze(code)

        self.assertEqual(
            result["memory_management_calls"],
            [],
        )


    def test_detects_pointer_declaration(self) -> None:
        result = self.analyzer.analyze(
            "int main(void) { int *value; return 0; }"
        )

        self.assertGreaterEqual(
            result["pointer_declaration_count"], 1
        )

    def test_detects_array_access(self) -> None:
        result = self.analyzer.analyze(
            "int main(void) { int values[5]; return values[2]; }"
        )

        self.assertGreaterEqual(result["array_access_count"], 1)

    def test_detects_changed_function_body(self) -> None:
        original = """
        int square(int x) {
            return x * x;
        }
        """

        modified = """
        int square(int x) {
            return x + x;
        }
        """

        original_result = self.analyzer.analyze(original)
        modified_result = self.analyzer.analyze(modified)

        self.assertEqual(
            original_result["function_count"],
            modified_result["function_count"],
        )
        self.assertNotEqual(
            original_result["functions"],
            modified_result["functions"],
        )

    def test_valid_code_has_no_syntax_errors(self) -> None:
        result = self.analyzer.analyze(
            "int square(int x) { return x * x; }"
        )

        self.assertFalse(result["syntax_errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
