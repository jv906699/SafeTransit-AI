import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
import json
import time
from datetime import datetime, timezone

from src.config import BENCHMARKS_DIR
from src.ollama_agent import clean_code_output
from src.ollama_client import OllamaClient
from src.parser import CodeParser


PROMPTS = [
    {
        "name": "minimal_program",
        "prompt": (
            "Write a complete C11 program that returns 0. "
            "Output source code only."
        ),
    },
    {
        "name": "print_program",
        "prompt": (
            "Write a complete C11 program that prints "
            "'SafeTransit prompt test passed' followed by a newline. "
            "Output source code only."
        ),
    },
    {
        "name": "function_program",
        "prompt": (
            "Write a complete C11 program with a typed function "
            "int add(int a, int b) and a main function that returns 0. "
            "Output source code only."
        ),
    },
]


def main() -> None:
    client = OllamaClient()
    parser = CodeParser()
    results = []

    for case in PROMPTS:
        start = time.perf_counter()
        response = client.generate(
            prompt=case["prompt"],
            system=(
                "You are a careful C11 programmer. Return complete, "
                "valid C source code only. Do not include Markdown "
                "fences or explanations."
            ),
            temperature=0.1,
            top_p=0.9,
            num_predict=512,
        )
        elapsed = time.perf_counter() - start

        cleaned = clean_code_output(response.response)
        tree = parser.parse(cleaned, "c")
        syntax_valid = not parser.has_syntax_errors(tree)

        result = {
            "name": case["name"],
            "wall_clock_seconds": round(elapsed, 4),
            "prompt_eval_count": response.prompt_eval_count,
            "eval_count": response.eval_count,
            "raw_has_markdown_fence": response.response.strip().startswith("```"),
            "cleaned_syntax_valid": syntax_valid,
            "raw_response": response.response,
            "cleaned_response": cleaned,
        }
        results.append(result)

        print(
            f"{case['name']}: syntax_valid={syntax_valid}, "
            f"raw_fence={result['raw_has_markdown_fence']}, "
            f"wall_clock={elapsed:.2f}s"
        )

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model": client.model,
        "temperature": 0.1,
        "top_p": 0.9,
        "num_predict": 512,
        "cases": results,
    }

    BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = BENCHMARKS_DIR / "prompt_matrix.json"
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Saved prompt matrix to: {output_path}")


if __name__ == "__main__":
    main()
