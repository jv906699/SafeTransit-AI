"""Benchmark the SafeTransit-AI migration pipeline on legacy C programs."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from .config import BENCHMARKS_DIR, ensure_project_directories
from .ollama_agent import OllamaRepairAgent, clean_code_output
from .ollama_client import OllamaClient
from .orchestrator import PipelineOrchestrator


class PipelineBenchmarker:
    """Run legacy C cases through the real migration pipeline."""

    def __init__(
        self,
        cases_dir: Path | None = None,
        output_dir: Path | None = None,
        pipeline: PipelineOrchestrator | None = None,
    ) -> None:
        ensure_project_directories()

        self.cases_dir = cases_dir or BENCHMARKS_DIR / "legacy_cases"
        self.output_dir = output_dir or BENCHMARKS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if pipeline is None:
            client = OllamaClient()
            agent = OllamaRepairAgent(
                client=client,
                cleanup_fn=clean_code_output,
            )
            pipeline = PipelineOrchestrator(agent=agent)

        self.pipeline = pipeline

    @staticmethod
    def _attempt_depth(result: dict[str, Any]) -> int:
        """Return the number of recorded pipeline attempts."""
        return int(result.get("attempts_used", 0))

    @staticmethod
    def _count_type_diagnostics(diagnostic_text: str) -> int:
        """Count diagnostic lines that explicitly mention type-related issues."""
        keywords = (
            "type mismatch",
            "incompatible type",
            "incompatible pointer",
            "conflicting types",
            "implicit conversion",
            "conversion to",
            "makes integer from pointer",
            "makes pointer from integer",
            "expected expression of type",
        )
        return sum(
            1
            for line in diagnostic_text.splitlines()
            if any(keyword in line.lower() for keyword in keywords)
        )

    def _run_case(self, case_path: Path) -> dict[str, Any]:
        """Run one case and return measured results."""
        source = case_path.read_text(encoding="utf-8")
        started = time.perf_counter()

        try:
            result = self.pipeline.execute_migration_pipeline(
                source,
                language="c",
            )
            error = ""
        except Exception as exc:  # noqa: BLE001
            # Record this case's failure so the remaining benchmarks can run.
            result = {
                "status": "benchmark_error",
                "verified": False,
                "attempts_used": 0,
                "attempt_history": [],
                "diagnostics": [f"{type(exc).__name__}: {exc}"],
            }
            error = f"{type(exc).__name__}: {exc}"

        elapsed_seconds = time.perf_counter() - started
        history = result.get("attempt_history", [])
        diagnostics = result.get("diagnostics", [])

        if isinstance(diagnostics, list):
            diagnostic_text = " | ".join(str(item) for item in diagnostics)
        else:
            diagnostic_text = str(diagnostics)

        # Collect telemetry from repair attempts. A missing metric stays
        # missing instead of being incorrectly reported as zero.
        repair_metrics = [
            entry["inference_metrics"]
            for entry in history
            if isinstance(entry.get("inference_metrics"), dict)
        ]

        prompt_counts = [
            item["prompt_tokens"]
            for item in repair_metrics
            if isinstance(item.get("prompt_tokens"), (int, float))
        ]
        generated_counts = [
            item["generated_tokens"]
            for item in repair_metrics
            if isinstance(item.get("generated_tokens"), (int, float))
        ]
        inference_durations = [
            item["inference_duration_ns"]
            for item in repair_metrics
            if isinstance(item.get("inference_duration_ns"), (int, float))
        ]
        generation_durations = [
            item["generation_duration_ns"]
            for item in repair_metrics
            if isinstance(item.get("generation_duration_ns"), (int, float))
        ]

        # The top-level diagnostics may be empty after successful verification.
        # Include diagnostics retained in the attempt history for statistics.
        history_diagnostics = [
            str(entry.get("diagnostics", ""))
            for entry in history
            if entry.get("diagnostics")
        ]
        all_diagnostics = "\n".join(
            part for part in [diagnostic_text, *history_diagnostics] if part
        )

        return {
            "case_name": case_path.name,
            "language": "c",
            "status": result.get("status", "unknown"),
            "verified": bool(result.get("verified", False)),
            "attempts_used": self._attempt_depth(result),
            "elapsed_seconds": round(elapsed_seconds, 6),
            "attempt_history_count": len(history),
            "diagnostics": diagnostic_text,
            "diagnostic_count": sum(
                1 for line in all_diagnostics.splitlines() if line.strip()
            ),
            "type_diagnostic_count": self._count_type_diagnostics(
                all_diagnostics
            ),
            "repair_calls_with_metrics": len(repair_metrics),
            "prompt_tokens": sum(prompt_counts) if prompt_counts else None,
            "generated_tokens": (
                sum(generated_counts) if generated_counts else None
            ),
            "inference_duration_ns": (
                sum(inference_durations) if inference_durations else None
            ),
            "generation_duration_ns": (
                sum(generation_durations) if generation_durations else None
            ),
            # Compiler-based verification does not establish either property.
            "behavior_verified": False,
            "memory_safety_verified": False,
            "benchmark_error": error,
        }

    def run(self) -> pd.DataFrame:
        """Benchmark all C files and export reports and visualizations."""
        case_files = sorted(self.cases_dir.glob("*.c"))

        if not case_files:
            raise FileNotFoundError(
                f"No .c benchmark cases found in {self.cases_dir}"
            )

        dataframe = pd.DataFrame(
            [self._run_case(path) for path in case_files]
        )

        dataframe.to_csv(
            self.output_dir / "metrics_report.csv",
            index=False,
        )
        self._write_summary(dataframe)
        self._write_iteration_chart(dataframe)
        self._write_latency_chart(dataframe)

        return dataframe

    def _write_summary(self, dataframe: pd.DataFrame) -> None:
        """Write aggregate benchmark statistics."""
        total = len(dataframe)
        summary = pd.DataFrame(
            [
                {
                    "total_cases": total,
                    "verified_cases": int(dataframe["verified"].sum()),
                    "verification_success_rate": (
                        float(dataframe["verified"].mean()) if total else 0.0
                    ),
                    "mean_elapsed_seconds": dataframe[
                        "elapsed_seconds"
                    ].mean(),
                    "std_elapsed_seconds": dataframe[
                        "elapsed_seconds"
                    ].std(),
                    "mean_attempts": dataframe["attempts_used"].mean(),
                    "std_attempts": dataframe["attempts_used"].std(),
                    "mean_prompt_tokens": dataframe["prompt_tokens"].mean(),
                    "mean_generated_tokens": dataframe[
                        "generated_tokens"
                    ].mean(),
                    "mean_inference_duration_ns": dataframe[
                        "inference_duration_ns"
                    ].mean(),
                    "mean_generation_duration_ns": dataframe[
                        "generation_duration_ns"
                    ].mean(),
                    "total_diagnostic_count": int(
                        dataframe["diagnostic_count"].sum()
                    ),
                    "total_type_diagnostic_count": int(
                        dataframe["type_diagnostic_count"].sum()
                    ),
                    "cases_with_benchmark_errors": int(
                        dataframe["benchmark_error"].fillna("").ne("").sum()
                    ),
                }
            ]
        )

        summary.to_csv(
            self.output_dir / "benchmark_summary.csv",
            index=False,
        )

    def _write_iteration_chart(self, dataframe: pd.DataFrame) -> None:
        """Plot repair-attempt depth for each benchmark case."""
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar(dataframe["case_name"], dataframe["attempts_used"])
        ax.set_title("Repair Iterations per Benchmark Case")
        ax.set_xlabel("Benchmark case")
        ax.set_ylabel("Pipeline attempts")
        ax.tick_params(axis="x", labelrotation=75)
        fig.tight_layout()
        fig.savefig(
            self.output_dir / "iteration_depths.png",
            dpi=150,
        )
        plt.close(fig)

    def _write_latency_chart(self, dataframe: pd.DataFrame) -> None:
        """Plot pipeline latency against generated-token counts."""
        fig, ax = plt.subplots(figsize=(9, 6))
        valid = dataframe.dropna(
            subset=["generated_tokens", "elapsed_seconds"]
        )

        if valid.empty:
            ax.text(
                0.5,
                0.5,
                "Token metrics unavailable; no repair telemetry was recorded.",
                horizontalalignment="center",
                verticalalignment="center",
                transform=ax.transAxes,
            )
            ax.set_axis_off()
        else:
            ax.scatter(
                valid["generated_tokens"],
                valid["elapsed_seconds"],
            )
            ax.set_xlabel("Generated tokens across repair calls")
            ax.set_ylabel("Total pipeline time (seconds)")
            ax.set_title("Pipeline Latency vs. Generated Tokens")
            ax.grid(True, alpha=0.3)

        fig.tight_layout()
        fig.savefig(
            self.output_dir / "latency_curves.png",
            dpi=150,
        )
        plt.close(fig)


if __name__ == "__main__":
    benchmarker = PipelineBenchmarker()
    results = benchmarker.run()

    print(
        results[
            [
                "case_name",
                "status",
                "verified",
                "attempts_used",
                "prompt_tokens",
                "generated_tokens",
                "elapsed_seconds",
            ]
        ].to_string(index=False)
    )
    print(f"\nProcessed {len(results)} benchmark cases.")
    print(f"Reports saved in: {BENCHMARKS_DIR}")
