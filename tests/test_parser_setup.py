from tree_sitter import Parser
from tree_sitter_languages import get_language


def main():
    language = get_language("c")

    parser = Parser()
    parser.set_language(language)

    source_code = """
    int add(int a, int b) {
        return a + b;
    }
    """

    tree = parser.parse(source_code.encode("utf-8"))

    print(tree.root_node)


if __name__ == "__main__":
    main()