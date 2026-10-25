
from src.verifier import VerificationDiagnostic, VerificationRunner


def test_valid_python_passes_combined_analysis():
    runner = VerificationRunner(timeout_seconds=15)

    result = runner.analyze_python(
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n"
    )

    assert result.syntax_valid is True
    assert result.tools_run == ["python_ast", "mypy", "bandit"]
    assert result.diagnostics == []


def test_invalid_python_stops_before_external_tools():
    runner = VerificationRunner()

    result = runner.analyze_python("def broken(:\n    pass\n")

    assert result.syntax_valid is False
    assert result.tools_run == ["python_ast"]
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].tool == "python_ast"


def test_mypy_detects_a_type_error():
    runner = VerificationRunner(timeout_seconds=15)

    result = runner.check_python_types(
        "def add(a: int, b: int) -> int:\n"
        '    return "not an integer"\n'
    )

    assert any(
        diagnostic.tool == "mypy"
        and diagnostic.severity == "error"
        for diagnostic in result
    )


def test_bandit_detects_hardcoded_password():
    runner = VerificationRunner(timeout_seconds=15)

    result = runner.check_python_security(
        'password = "hardcoded-secret"\n'
    )

    assert any(
        diagnostic.tool == "bandit"
        and diagnostic.code == "B105"
        for diagnostic in result
    )


def test_valid_analysis_reports_complete():
    runner = VerificationRunner(timeout_seconds=15)

    result = runner.analyze_python(
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n"
    )

    assert result.syntax_valid is True
    assert result.analysis_complete is True
    assert result.tools_run == ["python_ast", "mypy", "bandit"]


def test_syntax_error_stops_analysis():
    runner = VerificationRunner()

    result = runner.analyze_python("def broken(:\n    pass\n")

    assert result.syntax_valid is False
    assert result.analysis_complete is True
    assert result.tools_run == ["python_ast"]
    assert result.diagnostics[0].tool == "python_ast"


def test_tool_execution_failure_marks_analysis_incomplete(monkeypatch):
    from src.verifier import AnalyzerResult

    runner = VerificationRunner()

    monkeypatch.setattr(
        runner,
        "_analyze_python_types",
        lambda source: AnalyzerResult(
            tool="mypy",
            diagnostics=[
                VerificationDiagnostic(
                    tool="mypy",
                    severity="error",
                    message="Could not execute mypy: FileNotFoundError",
                )
            ],
            completed=False,
        ),
    )

    monkeypatch.setattr(
        runner,
        "_analyze_python_security",
        lambda source: AnalyzerResult(
            tool="bandit",
            diagnostics=[],
            completed=True,
        ),
    )

    result = runner.analyze_python(
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n"
    )

    assert result.syntax_valid is True
    assert result.analysis_complete is False
    assert result.failed_tools == ["mypy"]
    assert result.tools_run == ["python_ast", "mypy", "bandit"]


def test_analyzer_result_records_completion_with_findings():
    from src.verifier import AnalyzerResult, VerificationDiagnostic

    diagnostic = VerificationDiagnostic(
        tool="mypy",
        severity="error",
        message="Incompatible return value type",
        line=3,
    )

    result = AnalyzerResult(
        tool="mypy",
        diagnostics=[diagnostic],
        completed=True,
    )

    assert result.tool == "mypy"
    assert result.completed is True
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].severity == "error"


def test_mypy_diagnostic_parsing_extracts_structured_fields(monkeypatch):
    from src.verifier import AnalyzerResult, CommandResult

    runner = VerificationRunner()

    mypy_output = (
        "sandbox_scratchpad.py:4:9: error: Incompatible return value type "
        "(got \"str\", expected \"int\") [return-value]\n"
    )

    monkeypatch.setattr(
        runner,
        "run_command",
        lambda command: CommandResult(
            command=command,
            return_code=1,
            stdout=mypy_output,
            stderr="",
            timed_out=False,
        ),
    )

    result = runner._analyze_python_types(
        "def calculate() -> int:\n    return \"wrong\"\n"
    )

    assert isinstance(result, AnalyzerResult)
    assert result.completed is True
    assert len(result.diagnostics) == 1

    diagnostic = result.diagnostics[0]
    assert diagnostic.tool == "mypy"
    assert diagnostic.severity == "error"
    assert diagnostic.line == 4
    assert diagnostic.column == 9
    assert diagnostic.code == "return-value"
    assert "Incompatible return value type" in diagnostic.message


def test_mypy_parser_maps_notes_to_info(monkeypatch):
    from src.verifier import CommandResult

    runner = VerificationRunner()
    mypy_output = (
        "sandbox_scratchpad.py:2:5: note: See documentation for details\n"
        "Success: no issues found in 1 source file\n"
    )

    monkeypatch.setattr(
        runner,
        "run_command",
        lambda command: CommandResult(
            command=command,
            return_code=0,
            stdout=mypy_output,
            stderr="",
            timed_out=False,
        ),
    )

    result = runner._analyze_python_types("x: int = 1\n")

    assert result.completed is True
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].severity == "info"
    assert result.diagnostics[0].line == 2
    assert result.diagnostics[0].column == 5
    assert result.diagnostics[0].message == "See documentation for details"


def test_mypy_parser_extracts_warning_and_ignores_other_output(monkeypatch):
    from src.verifier import CommandResult

    runner = VerificationRunner()
    mypy_output = (
        "sandbox_scratchpad.py:3:7: warning: Example warning [unused-ignore]\n"
        "This is an ordinary output line\n"
    )

    monkeypatch.setattr(
        runner,
        "run_command",
        lambda command: CommandResult(
            command=command,
            return_code=0,
            stdout=mypy_output,
            stderr="",
            timed_out=False,
        ),
    )

    result = runner._analyze_python_types("x: int = 1\n")

    assert result.completed is True
    assert len(result.diagnostics) == 1

    diagnostic = result.diagnostics[0]
    assert diagnostic.severity == "warning"
    assert diagnostic.line == 3
    assert diagnostic.column == 7
    assert diagnostic.code == "unused-ignore"
    assert diagnostic.message == "Example warning"


def test_bandit_execution_failure_has_classification(monkeypatch):
    from src.verifier import CommandResult

    runner = VerificationRunner()

    monkeypatch.setattr(
        runner,
        "run_command",
        lambda command: CommandResult(
            command=command,
            return_code=None,
            stdout="",
            stderr="",
            timed_out=False,
            execution_error="FileNotFoundError",
        ),
    )

    result = runner._analyze_python_security("x = 1\n")

    assert result.completed is False
    assert result.diagnostics[0].classification == "tool_execution_error"


def test_bandit_timeout_has_classification(monkeypatch):
    from src.verifier import CommandResult

    runner = VerificationRunner()

    monkeypatch.setattr(
        runner,
        "run_command",
        lambda command: CommandResult(
            command=command,
            return_code=None,
            stdout="",
            stderr="",
            timed_out=True,
        ),
    )

    result = runner._analyze_python_security("x = 1\n")

    assert result.completed is False
    assert result.diagnostics[0].classification == "timeout"


def test_bandit_invalid_json_has_classification(monkeypatch):
    from src.verifier import CommandResult

    runner = VerificationRunner()

    monkeypatch.setattr(
        runner,
        "run_command",
        lambda command: CommandResult(
            command=command,
            return_code=0,
            stdout="not valid json",
            stderr="",
            timed_out=False,
        ),
    )

    result = runner._analyze_python_security("x = 1\n")

    assert result.completed is False
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].classification == "invalid_tool_output"


def test_bandit_invalid_report_structure_has_classification(monkeypatch):
    import json

    from src.verifier import CommandResult

    runner = VerificationRunner()
    invalid_report = json.dumps({"results": "unexpected"})

    monkeypatch.setattr(
        runner,
        "run_command",
        lambda command: CommandResult(
            command=command,
            return_code=0,
            stdout=invalid_report,
            stderr="",
            timed_out=False,
        ),
    )

    result = runner._analyze_python_security("x = 1\n")

    assert result.completed is False
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].classification == "invalid_tool_output"


def test_mypy_nonzero_exit_with_unrecognized_output_is_incomplete(
    monkeypatch,
):
    from src.verifier import CommandResult

    runner = VerificationRunner()
    mypy_output = (
        "sandbox_scratchpad.py:2:5: error: Incompatible types [assignment]\n"
        "Unexpected internal analyzer failure\n"
    )

    monkeypatch.setattr(
        runner,
        "run_command",
        lambda command: CommandResult(
            command=command,
            return_code=2,
            stdout=mypy_output,
            stderr="",
            timed_out=False,
        ),
    )

    result = runner._analyze_python_types("x: int = 1\n")

    assert result.completed is False
    assert any(
        diagnostic.classification == "type_error"
        for diagnostic in result.diagnostics
    )
    assert any(
        diagnostic.classification == "tool_execution_error"
        for diagnostic in result.diagnostics
    )


def test_python_analysis_cleans_up_sandbox_artifacts():
    runner = VerificationRunner(timeout_seconds=15)

    result = runner.analyze_python(
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n"
    )

    assert result.syntax_valid is True
    assert not (
        runner.sandbox_dir / "sandbox_scratchpad.py"
    ).exists()
    assert not (
        runner.sandbox_dir / "sandbox_scratchpad.c"
    ).exists()
    assert not (
        runner.sandbox_dir / "sandbox_scratchpad.exe"
    ).exists()
