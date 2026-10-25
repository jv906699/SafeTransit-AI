
"""End-to-end tests for the SafeTransit-AI repair pipeline."""

import shutil
import subprocess
from unittest.mock import Mock, patch

import pytest
import requests

from src.ollama_agent import OllamaRepairAgent, clean_code_output
from src.ollama_client import OllamaClient
from src.parser import CodeParser


@pytest.fixture(scope="module")
def repair_result():
    """Repair a deliberately broken C program using local Ollama."""
    if shutil.which("gcc") is None:
        pytest.skip("GCC is not available on PATH.")

    client = OllamaClient(timeout=180)

    # Skip cleanly if the local Ollama server is unavailable.
    try:
        response = client.generate(
            prompt="Reply with exactly: READY",
            temperature=0.0,
            top_p=0.9,
        )
    except requests.RequestException as exc:
        pytest.skip(f"Local Ollama server is unavailable: {exc}")

    assert response.response.strip(), "Ollama returned an empty response."

    agent = OllamaRepairAgent(
        client=client,
        cleanup_fn=clean_code_output,
    )

    broken_code = (
        "#include <stdio.h>\n"
        "int main(void) {\n"
        '    printf("SafeTransit repair passed\\\\n");\n'
        "    return 0\n"
        "}\n"
    )

    result = agent.repair(
        broken_code,
        "The return statement is missing a semicolon. "
        "Return the complete corrected C source code only.",
    )

    assert result.cleaned_code.strip(), "The repair output is empty."
    return result.cleaned_code


def test_repaired_code_has_no_syntax_errors(repair_result):
    """The repaired source must parse without Tree-sitter errors."""
    parser = CodeParser()
    tree = parser.parse(repair_result, "c")

    assert not parser.has_syntax_errors(tree), (
        f"Repaired source still has syntax errors:\n{repair_result}"
    )


def test_repaired_code_compiles_and_runs(repair_result, tmp_path):
    """The repaired source must compile strictly and run successfully."""
    source_file = tmp_path / "repaired.c"
    executable = tmp_path / "repaired.exe"

    source_file.write_text(repair_result, encoding="utf-8")

    compile_result = subprocess.run(
        [
            "gcc",
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            str(source_file),
            "-o",
            str(executable),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert compile_result.returncode == 0, (
        f"GCC compilation failed:\n{compile_result.stderr}\n"
        f"Generated source:\n{repair_result}"
    )

    run_result = subprocess.run(
        [str(executable)],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert run_result.returncode == 0, (
        f"Program execution failed:\n{run_result.stderr}"
    )
    assert "SafeTransit repair passed" in run_result.stdout

def test_code_cleanup_handles_fenced_and_plain_output():
    """Markdown fences are removed without altering plain source."""
    fenced = "```c\nint main(void) { return 0; }\n```"
    plain = "int main(void) { return 0; }"

    assert clean_code_output(fenced) == (
        "int main(void) { return 0; }"
    )
    assert clean_code_output(plain) == plain

def test_ollama_client_sends_generation_limit():
    """The configured generation limit must reach Ollama's API."""
    from src.ollama_client import OllamaClient

    fake_response = Mock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {
        "model": "qwen2.5-coder:7b-instruct",
        "response": "int main(void) { return 0; }",
        "total_duration": 1000,
        "prompt_eval_count": 5,
        "eval_count": 10,
    }

    with patch("src.ollama_client.requests.post", return_value=fake_response) as post:
        client = OllamaClient()
        client.generate(
            prompt="Return a C program.",
            temperature=0.1,
            top_p=0.9,
            num_predict=512,
        )

    payload = post.call_args.kwargs["json"]
    assert payload["options"]["num_predict"] == 512
    assert payload["options"]["temperature"] == 0.1
    assert payload["options"]["top_p"] == 0.9


def test_code_cleanup_removes_fences_from_c_response():
    """A typical fenced C response becomes parseable source."""
    from src.ollama_agent import clean_code_output
    from src.parser import CodeParser

    raw_output = (
        "```c\n"
        "#include <stdio.h>\n"
        "int main(void) {\n"
        '    printf("Hello\\\\n");\n'
        "    return 0;\n"
        "}\n"
        "```"
    )

    cleaned = clean_code_output(raw_output)
    parser = CodeParser()
    tree = parser.parse(cleaned, "c")

    assert not cleaned.startswith("```")
    assert not cleaned.endswith("```")
    assert not parser.has_syntax_errors(tree)
