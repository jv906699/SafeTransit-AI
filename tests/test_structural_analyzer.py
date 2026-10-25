
import unittest

from src.parser import StructuralAnalyzer


class TestStructuralAnalyzer(unittest.TestCase):

    def setUp(self) -> None:
        self.analyzer = StructuralAnalyzer()

    def test_detects_c_string_literal(self) -> None:
        result = self.analyzer.analyze(
            'char *message = "hello";',
            "c",
        )

        self.assertEqual(result["string_literal_count"], 1)
        self.assertIn('"hello"', result["string_literals"])

    def test_detects_python_identifiers_and_string(self) -> None:
        result = self.analyzer.analyze(
            'def greet(name):\n'
            '    message = "hello"\n'
            '    return message',
            "python",
        )

        self.assertGreaterEqual(result["identifier_count"], 3)
        self.assertIn("greet", result["identifiers"])
        self.assertIn("name", result["identifiers"])
        self.assertEqual(result["string_literal_count"], 1)

    def test_reports_block_source_positions(self) -> None:
        result = self.analyzer.analyze(
            "int main(void) { return 0; }",
            "c",
        )

        self.assertGreaterEqual(result["block_count"], 1)
        self.assertIn("start_point", result["blocks"][0])
        self.assertIn("end_point", result["blocks"][0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
