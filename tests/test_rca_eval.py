#
# Copyright (C) 2026 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""End-to-end evaluation of the RCA prompt with LLM judge.

Runs a full RCA with Claude on a real DCI job, then uses an LLM judge
to score the report against the RCA methodology criteria.

Run with: uv run pytest -m rca_eval -v
Or:       bash scripts/run-checks.sh --rca-eval
"""

import asyncio
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env", override=True)

JOB_ID = "7fb9d2e5-c5d0-4134-8416-02c79af4617d"
REPORT_PATH = Path(f"/tmp/dci/rca-{JOB_ID}.md")

JUDGE_PROMPT = """\
You are an expert judge evaluating the quality of a Root Cause Analysis (RCA) \
report for a CI/CD job failure. Score the report on each criterion below \
using 0, 1, or 2.

## Scoring rubric

1. **causal_depth**: How deep is the causal chain?
   - 0: Stops at the first error (symptom only)
   - 1: 2-3 levels of "why"
   - 2: 4+ levels with evidence at each level

2. **evidence_quality**: Are claims backed by specific log evidence?
   - 0: No log citations or file references
   - 1: Some file references but vague
   - 2: Specific log lines or file content cited at each causal level

3. **adversarial_challenge**: Was an alternative hypothesis explored?
   - 0: No alternative hypothesis mentioned
   - 1: Alternative mentioned but not investigated with evidence
   - 2: Alternative from a different failure category, investigated with evidence for/against

4. **confidence_calibration**: Is confidence level stated with justification?
   - 0: No confidence level stated
   - 1: Confidence stated but criteria not explained
   - 2: Confidence stated with evidence-based justification (what evidence supports it, what's missing)

5. **report_structure**: Does the report have the required sections?
   Required: Job Information, Failure Symptom, Causal Chain, Root Cause, \
Contributing Factors, Confidence Level, Recommendations
   - 0: Fewer than 4 of the 7 sections
   - 1: 4-5 sections present
   - 2: 6-7 sections present

6. **must_gather_usage**: Was must_gather / cluster state data used?
   - 0: Not referenced at all
   - 1: Referenced but not integrated as evidence in the causal chain
   - 2: must_gather findings used as supporting or refuting evidence

7. **actionable_recommendations**: Are the recommendations useful?
   - 0: Missing or completely generic ("fix the bug")
   - 1: Some specific recommendations
   - 2: Concrete, actionable recommendations linked to the identified root cause

## Output format

Return ONLY a JSON object with this exact structure, no other text:
```json
{
  "scores": {
    "causal_depth": <0-2>,
    "evidence_quality": <0-2>,
    "adversarial_challenge": <0-2>,
    "confidence_calibration": <0-2>,
    "report_structure": <0-2>,
    "must_gather_usage": <0-2>,
    "actionable_recommendations": <0-2>
  },
  "explanations": {
    "causal_depth": "<one sentence>",
    "evidence_quality": "<one sentence>",
    "adversarial_challenge": "<one sentence>",
    "confidence_calibration": "<one sentence>",
    "report_structure": "<one sentence>",
    "must_gather_usage": "<one sentence>",
    "actionable_recommendations": "<one sentence>"
  },
  "overall_assessment": "<2-3 sentence summary of the report quality>"
}
```

## Report to evaluate

"""


def _has_dci_credentials():
    return bool(os.getenv("DCI_CLIENT_ID") and os.getenv("DCI_API_SECRET"))


def _has_claude_cli():
    return shutil.which("claude") is not None


skip_no_credentials = pytest.mark.skipif(
    not _has_dci_credentials(),
    reason="DCI credentials not available",
)

skip_no_claude = pytest.mark.skipif(
    not _has_claude_cli(),
    reason="claude CLI not available",
)


def _render_rca_prompt():
    from mcp_server.prompts.render import render_prompt

    return asyncio.run(render_prompt("rca", dci_job_id=JOB_ID))


def _run_rca(prompt):
    mcp_config = json.dumps(
        {
            "mcpServers": {
                "dci": {
                    "command": "uv",
                    "args": ["run", "main.py"],
                    "cwd": str(project_root),
                }
            }
        }
    )

    cmd = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        os.getenv("EVAL_MODEL", "sonnet"),
        "--no-session-persistence",
        "--strict-mcp-config",
        "--dangerously-skip-permissions",
        "--max-budget-usd",
        "2.00",
        "--mcp-config",
        mcp_config,
        "--allowed-tools",
        "mcp__dci__search_dci_jobs",
        "mcp__dci__download_dci_file",
        "mcp__dci__get_jira_ticket",
        "Bash",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=str(project_root),
        )
    except subprocess.TimeoutExpired:
        pytest.fail("RCA eval timed out (600s)")

    messages = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            messages.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return messages, result.returncode


def _run_judge(report):
    """Run the LLM judge on the report and return parsed scores."""
    prompt = JUDGE_PROMPT + report
    empty_mcp = json.dumps({"mcpServers": {}})

    cmd = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        os.getenv("JUDGE_MODEL", "haiku"),
        "--no-session-persistence",
        "--strict-mcp-config",
        "--mcp-config",
        empty_mcp,
        "--max-budget-usd",
        "0.10",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(project_root),
        )
    except subprocess.TimeoutExpired:
        pytest.fail("Judge timed out (120s)")

    answer = ""
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            if msg.get("type") == "result":
                answer = msg.get("result", "")
                break
        except json.JSONDecodeError:
            continue

    if not answer and result.stderr:
        pytest.fail(f"Judge failed: {result.stderr[:500]}")

    # Extract JSON from the answer (may be wrapped in markdown code fence)
    json_match = re.search(r"\{[\s\S]*\}", answer)
    if not json_match:
        pytest.fail(f"Judge did not return valid JSON. Response: {answer[:500]}")

    try:
        return json.loads(json_match.group())
    except json.JSONDecodeError:
        pytest.fail(f"Judge returned invalid JSON: {json_match.group()[:500]}")


CRITERIA = [
    "causal_depth",
    "evidence_quality",
    "adversarial_challenge",
    "confidence_calibration",
    "report_structure",
    "must_gather_usage",
    "actionable_recommendations",
]


@pytest.mark.rca_eval
@skip_no_credentials
@skip_no_claude
class TestRcaEval:
    """End-to-end RCA evaluation with LLM judge."""

    @pytest.fixture(scope="class")
    def rca_report(self):
        """Run the RCA once and return the report text."""
        if REPORT_PATH.exists():
            REPORT_PATH.unlink()

        prompt = _render_rca_prompt()
        messages, _ = _run_rca(prompt)

        cost = 0.0
        num_turns = 0
        for msg in messages:
            if msg.get("type") == "result":
                cost = msg.get("total_cost_usd", 0)
                num_turns = msg.get("num_turns", 0)
                break

        print(f"\n  [rca] cost=${cost:.4f}, turns={num_turns}")

        assert REPORT_PATH.exists(), f"Report not found at {REPORT_PATH}"
        report = REPORT_PATH.read_text()
        assert len(report) > 500, "Report is too short"
        return report

    @pytest.fixture(scope="class")
    def judge_scores(self, rca_report):
        """Run the LLM judge on the report and return scores."""
        result = _run_judge(rca_report)

        scores = result.get("scores", {})
        explanations = result.get("explanations", {})
        overall = result.get("overall_assessment", "")

        print(f"\n  [judge] Overall: {overall}")
        for criterion in CRITERIA:
            score = scores.get(criterion, "?")
            explanation = explanations.get(criterion, "")
            print(f"  [judge] {criterion}: {score}/2 — {explanation}")

        avg = sum(scores.get(c, 0) for c in CRITERIA) / len(CRITERIA)
        print(f"  [judge] Average: {avg:.2f}/2.0")

        return scores

    def test_report_exists_and_has_job_id(self, rca_report):
        assert JOB_ID in rca_report

    def test_no_criterion_scores_zero(self, judge_scores):
        """Every criterion must score at least 1 (partial)."""
        for criterion in CRITERIA:
            score = judge_scores.get(criterion, 0)
            assert score >= 1, f"{criterion} scored 0 — failing quality gate"

    def test_average_score_above_threshold(self, judge_scores):
        """Average score across all criteria must be >= 1.0."""
        avg = sum(judge_scores.get(c, 0) for c in CRITERIA) / len(CRITERIA)
        assert avg >= 1.0, f"Average score {avg:.2f} below threshold 1.0"


# test_rca_eval.py ends here
