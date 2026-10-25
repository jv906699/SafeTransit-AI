
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.parser import ASTGraphWalker, CodeParser, CStructuralAnalyzer


class TestFrontendIntegration(unittest.TestCase):

    def test_legacy_c_analysis_pipeline(self) -> None:
        source = """
        #include <stdlib.h>

        int process(int size) {
            int *buffer = malloc(sizeof(int) * size);
            if (buffer == NULL) {
                return -1;
            }
            buffer[0] = size;
            free(buffer);
            return 0;
        }
        """

        parser = CodeParser()
        tree = parser.parse(source, "c")

        self.assertFalse(parser.has_syntax_errors(tree))

        nodes = ASTGraphWalker().walk(tree)
        self.assertTrue(
            any(node["type"] == "function_definition" for node in nodes)
        )

        result = CStructuralAnalyzer().analyze(source)

        self.assertEqual(result["function_count"], 1)
        self.assertGreaterEqual(result["pointer_declaration_count"], 1)
        self.assertGreaterEqual(result["array_access_count"], 1)
        self.assertTrue(
            any("malloc" in call
                for call in result["memory_management_calls"])
        )
        self.assertTrue(
            any("free" in call
                for call in result["memory_management_calls"])
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
