
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.parser import CodeParser


class TestCodeParser(unittest.TestCase):

    def setUp(self) -> None:
        self.parser = CodeParser()

    def test_valid_c_code(self) -> None:
        code = "int add(int a, int b) { return a + b; }"
        tree = self.parser.parse(code, "c")

        self.assertEqual(tree.root_node.type, "translation_unit")
        self.assertFalse(self.parser.has_syntax_errors(tree))

    def test_valid_python_code(self) -> None:
        code = "def add(a, b):\n    return a + b\n"
        tree = self.parser.parse(code, "python")

        self.assertEqual(tree.root_node.type, "module")
        self.assertFalse(self.parser.has_syntax_errors(tree))

    def test_invalid_language(self) -> None:
        with self.assertRaises(ValueError):
            self.parser.parse("some code", "java")

    def test_empty_source(self) -> None:
        with self.assertRaises(ValueError):
            self.parser.parse("", "c")

    def test_malformed_c_code(self) -> None:
        code = "int add( { return 1; }"
        tree = self.parser.parse(code, "c")

        self.assertTrue(self.parser.has_syntax_errors(tree))


if __name__ == "__main__":
    unittest.main(verbosity=2)
