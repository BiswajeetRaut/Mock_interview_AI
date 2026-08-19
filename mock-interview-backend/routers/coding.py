from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from middleware.rate_limit import CODING_RUN_CAPACITY, CODING_RUN_REFILL_PER_MIN, rate_limit_by_ip

# ── P2-101: kill-switch ──────────────────────────────────────────────────
# /coding/run executes candidate-submitted code with no sandbox. Disabled by
# default until it's rebuilt on an isolated runner (see Phase 2 backlog,
# P2-101 / Epic 6 sandboxed executor). Set CODING_RUNNER_ENABLED=true to
# re-enable for local development only.
CODING_RUNNER_ENABLED = os.getenv("CODING_RUNNER_ENABLED", "false").strip().lower() in (
    "1", "true", "yes",
)


def _require_coding_runner_enabled() -> None:
    if not CODING_RUNNER_ENABLED:
        raise HTTPException(
            status_code=503,
            detail=(
                "Code execution is temporarily disabled while we roll out a "
                "sandboxed runner. Your interview continues normally — only "
                "the coding practice panel is affected."
            ),
        )


# P2-106: /coding/run has no auth dependency (adding one is out of scope
# here — P2-101 already turns the whole endpoint off by default), so it only
# gets the per-IP dimension of the rate limiter, not per-UID.
_coding_run_rate_limit = rate_limit_by_ip("coding_run", CODING_RUN_CAPACITY, CODING_RUN_REFILL_PER_MIN)

router = APIRouter(dependencies=[
    Depends(_require_coding_runner_enabled),
    Depends(_coding_run_rate_limit),
])


class CodingRunRequest(BaseModel):
    code: str
    language: Literal["python", "javascript"] = "python"
    test_cases: List[Dict[str, Any]] = Field(default_factory=list)


def _normalize_output(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return str(value).strip()


def _run_python(code: str, test_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    harness = f"""
import json
{code}

CASES = {json.dumps(test_cases)}
results = []
for idx, case in enumerate(CASES):
    try:
        if "solve" not in globals():
            raise Exception("Please define a solve(input_data) function.")
        actual = solve(case.get("input"))
        expected = case.get("expected_output")
        passed = str(actual).strip() == str(expected).strip()
        results.append({{"index": idx, "passed": passed, "actual": actual, "expected": expected}})
    except Exception as exc:
        results.append({{"index": idx, "passed": False, "actual": f"Runtime error: {{exc}}", "expected": case.get("expected_output")}})
print(json.dumps(results))
""".strip()

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "run.py"
        file_path.write_text(harness, encoding="utf-8")
        proc = subprocess.run(
            ["python", str(file_path)],
            capture_output=True,
            text=True,
            timeout=8,
        )
    if proc.returncode != 0:
        raise HTTPException(status_code=400, detail=proc.stderr.strip() or "Python execution failed")
    return json.loads(proc.stdout.strip() or "[]")


def _run_js(code: str, test_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    harness = f"""
{code}
const CASES = {json.dumps(test_cases)};
const results = [];
for (let idx = 0; idx < CASES.length; idx += 1) {{
  const testCase = CASES[idx];
  try {{
    if (typeof solve !== "function") throw new Error("Please define solve(inputData) function.");
    const actual = solve(testCase.input);
    const expected = testCase.expected_output;
    const passed = String(actual).trim() === String(expected).trim();
    results.push({{ index: idx, passed, actual, expected }});
  }} catch (error) {{
    results.push({{ index: idx, passed: false, actual: `Runtime error: ${{error.message}}`, expected: testCase.expected_output }});
  }}
}}
console.log(JSON.stringify(results));
""".strip()

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "run.js"
        file_path.write_text(harness, encoding="utf-8")
        proc = subprocess.run(
            ["node", str(file_path)],
            capture_output=True,
            text=True,
            timeout=8,
        )
    if proc.returncode != 0:
        raise HTTPException(status_code=400, detail=proc.stderr.strip() or "JavaScript execution failed")
    return json.loads(proc.stdout.strip() or "[]")


@router.post("/run")
def run_code(payload: CodingRunRequest):
    if not payload.test_cases:
        raise HTTPException(status_code=400, detail="No test cases provided.")

    if payload.language == "python":
        results = _run_python(payload.code, payload.test_cases)
    else:
        results = _run_js(payload.code, payload.test_cases)

    normalized_results = [
        {
            **item,
            "actual": _normalize_output(item.get("actual")),
            "expected": _normalize_output(item.get("expected")),
        }
        for item in results
    ]
    passed_count = len([item for item in normalized_results if item.get("passed")])
    return {
        "total": len(normalized_results),
        "passed": passed_count,
        "all_passed": passed_count == len(normalized_results),
        "results": normalized_results,
    }
