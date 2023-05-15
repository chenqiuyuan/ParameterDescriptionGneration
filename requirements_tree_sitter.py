import os
from tree_sitter import Language, Parser

__TREE_SITTER_LIBS_DIR__ = "tree_sitter_libs"

YOUR_LANGUAGE = 'java'
so_file = os.path.join(__TREE_SITTER_LIBS_DIR__, f'{YOUR_LANGUAGE}.so')
lib_dir = os.path.join(__TREE_SITTER_LIBS_DIR__, "tree-sitter-java")

def build_so():
    print(f"Build {YOUR_LANGUAGE}.so, and save it at {so_file}")
    Language.build_library(
        # your language parser file, we recommend build *.so file for each language
        so_file,
        # Include one or more languages
        [lib_dir],
    )

def test_parse(code):
    JAVA_LANGUAGE = Language(so_file, 'java')

    parser = Parser()
    parser.set_language(JAVA_LANGUAGE)

    tree = parser.parse(code)
    return tree

if __name__ == "__main__":
    """
    python -m requirements_tree_sitter
    """
    build_so()