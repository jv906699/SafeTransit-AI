
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.parser import ASTGraphWalker, CodeParser


class TestASTGraphWalker(unittest.TestCase):

    def setUp(self) -> None:
        self.parser = CodeParser()
        self.walker = ASTGraphWalker()

    def test_walk_returns_nodes(self) -> None:
        code = "int add(int a, int b) { return a + b; }"
        tree = self.parser.parse(code, "c")

        nodes = self.walker.walk(tree)

        self.assertGreater(len(nodes), 1)
        self.assertEqual(nodes[0]["type"], "translation_unit")

    def test_finds_function_definition(self) -> None:
        code = "int add(int a, int b) { return a + b; }"
        tree = self.parser.parse(code, "c")

        functions = self.walker.find_nodes(
            tree, {"function_definition"}
        )

        self.assertEqual(len(functions), 1)
        self.assertIn("add", functions[0]["text"])

    def test_finds_return_statement(self) -> None:
        code = "int calculate(void) { return 42; }"
        tree = self.parser.parse(code, "c")

        returns = self.walker.find_nodes(
            tree, {"return_statement"}
        )

        self.assertEqual(len(returns), 1)

    def test_finds_malloc_call(self) -> None:
        code = """
        #include <stdlib.h>
        int main(void) {
            int *buffer = malloc(sizeof(int) * 5);
            free(buffer);
            return 0;
        }
        """
        tree = self.parser.parse(code, "c")

        calls = self.walker.find_nodes(
            tree, {"call_expression"}
        )

        call_texts = [node["text"] for node in calls]

        self.assertTrue(any("malloc" in text for text in call_texts))
        self.assertTrue(any("free" in text for text in call_texts))


if __name__ == "__main__":
    unittest.main(verbosity=2)
