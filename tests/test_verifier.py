
import sys

import pytest

from src.verifier import VerificationRunner


def test_write_source_creates_scratchpad():
    runner = VerificationRunner()

    path = runner.write_source('print("hello")')

    assert path.exists()
    assert path.name == "sandbox_scratchpad.py"
    assert path.read_text(encoding="utf-8") == 'print("hello")'


def test_write_source_rejects_empty_code():
    runner = VerificationRunner()

    with pytest.raises(ValueError, match="cannot be empty"):
        runner.write_source("   ")


def test_run_command_captures_stdout():
    runner = VerificationRunner()

    result = runner.run_command(
        [sys.executable, "-c", 'print("verification successful")']
    )

    assert result.return_code == 0
    assert "verification successful" in result.stdout
    assert result.timed_out is False


def test_run_command_captures_errors():
    runner = VerificationRunner()

    result = runner.run_command(
        [
            sys.executable,
            "-c",
            'raise ValueError("intentional test error")',
        ]
    )

    assert result.return_code != 0
    assert "ValueError" in result.stderr
    assert result.timed_out is False


def test_run_command_enforces_timeout():
    runner = VerificationRunner(timeout_seconds=1)

    result = runner.run_command(
        [sys.executable, "-c", "import time; time.sleep(5)"]
    )

    assert result.timed_out is True
    assert result.return_code is None


def test_run_command_rejects_empty_command():
    runner = VerificationRunner()

    with pytest.raises(ValueError, match="Command cannot be empty"):
        runner.run_command([])


def test_run_command_captures_missing_executable():
    runner = VerificationRunner()

    result = runner.run_command(
        ["safetransit_command_that_does_not_exist"]
    )

    assert result.return_code is None
    assert result.timed_out is False
    assert result.execution_error is not None
    assert result.execution_error.startswith("FileNotFoundError")


def test_run_command_preserves_execution_error_details():
    runner = VerificationRunner()

    result = runner.run_command(
        ["safetransit_command_that_does_not_exist"]
    )

    assert result.execution_error is not None
    assert "system cannot find the file" in result.execution_error.lower()


def test_command_result_succeeded_when_exit_code_is_zero():
    from src.verifier import CommandResult

    result = CommandResult(
        command=["python", "--version"],
        return_code=0,
        stdout="Python 3.11.9",
        stderr="",
        timed_out=False,
    )

    assert result.succeeded is True


def test_command_result_not_succeeded_when_timed_out():
    from src.verifier import CommandResult

    result = CommandResult(
        command=["python", "slow_script.py"],
        return_code=None,
        stdout="",
        stderr="",
        timed_out=True,
    )

    assert result.succeeded is False

def test_write_source_rejects_source_over_size_limit():
    from src.config import MAX_SOURCE_SIZE_BYTES

    runner = VerificationRunner()
    source_code = "a" * (MAX_SOURCE_SIZE_BYTES + 1)

    with pytest.raises(ValueError, match="maximum size"):
        runner.write_source(source_code)


def test_write_source_rejects_source_over_line_limit():
    from src.config import MAX_SOURCE_LINES

    runner = VerificationRunner()
    source_code = "\n".join(
        "pass" for _ in range(MAX_SOURCE_LINES + 1)
    )

    with pytest.raises(ValueError, match="maximum"):
        runner.write_source(source_code)


def test_write_c_source_creates_c_file():
    runner = VerificationRunner()

    path = runner.write_c_source(
        "int main(void) { return 0; }\n"
    )

    assert path.exists()
    assert path.name == "sandbox_scratchpad.c"
    assert path.read_text(encoding="utf-8") == (
        "int main(void) { return 0; }\n"
    )


def test_check_c_compilation_accepts_valid_c():
    runner = VerificationRunner()

    source_code = """
#include <stdio.h>

int main(void) {
    printf("Hello, SafeTransit!\\n");
    return 0;
}
"""

    result = runner.check_c_compilation(source_code)

    assert result.tool == "gcc"
    assert result.completed is True
    assert result.diagnostics == []


def test_check_c_compilation_reports_invalid_c():
    runner = VerificationRunner()

    source_code = """
int main(void) {
    int value = ;
    return 0;
}
"""

    result = runner.check_c_compilation(source_code)

    assert result.tool == "gcc"
    assert result.completed is True
    assert result.diagnostics
    assert any(
        diagnostic.classification == "compile_error"
        for diagnostic in result.diagnostics
    )
    assert any(
        diagnostic.line is not None
        for diagnostic in result.diagnostics
    )


def test_check_c_compilation_detects_unsafe_array_loop():
    runner = VerificationRunner()

    source_code = """
#include <stdio.h>

int main(void) {
    int values[5];
    int i;

    for (i = 0; i <= 5; i++) {
        values[i] = i * 10;
    }

    printf("Last value: %d\\n", values[4]);
    return 0;
}
"""

    result = runner.check_c_compilation(source_code)

    assert result.completed is True
    assert result.diagnostics, (
        "The verifier incorrectly accepted an array loop that writes "
        "past the end of values[5]."
    )
    assert any(
        diagnostic.classification == "memory_safety"
        for diagnostic in result.diagnostics
    )


def test_check_c_compilation_detects_out_of_bounds_array_read():
    runner = VerificationRunner()

    source_code = """
#include <stdio.h>

int main(void) {
    int values[5] = {10, 20, 30, 40, 50};

    for (int i = 0; i <= 5; i++) {
        printf("%d\\n", values[i]);
    }

    return 0;
}
"""

    result = runner.check_c_compilation(source_code)

    assert result.completed is True
    assert any(
        diagnostic.classification == "memory_safety"
        for diagnostic in result.diagnostics
    )


def test_check_c_compilation_accepts_valid_array_loop():
    runner = VerificationRunner()

    source_code = """
#include <stdio.h>

int main(void) { 
    int values[5] = {10, 20, 30, 40, 50};

    for (int i = 0; i < 5; i++) {
        printf("%d\\n", values[i]);
    }

    return 0;
}
"""

    result = runner.check_c_compilation(source_code)

    assert result.completed is True
    assert not result.diagnostics


def test_c_compilation_cleans_up_sandbox_artifacts():
    runner = VerificationRunner()

    source_code = """
int main(void) {
    return 0;
}
"""

    result = runner.check_c_compilation(source_code)

    assert result.completed is True
    assert not (
        runner.sandbox_dir / "sandbox_scratchpad.c"
    ).exists()
    assert not (
        runner.sandbox_dir / "sandbox_scratchpad.exe"
    ).exists()
    assert not (
        runner.sandbox_dir / "sandbox_scratchpad.py"
    ).exists()
