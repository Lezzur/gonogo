from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional, Dict, Any

from schemas import SynthesisResult, TechStack
from config import REPORTS_DIR
from llm.client import LLMClient
from llm.prompt_loader import load_prompt


def get_verdict_emoji(verdict: str) -> str:
    """Get emoji for verdict."""
    if verdict == "GO":
        return "🟢"
    elif verdict == "NO-GO":
        return "🔴"
    else:
        return "🟡"


def _generate_delta_section_a(
    delta_data: Dict[str, Any],
    cycle_number: int,
    previous_score: float,
    current_score: float
) -> str:
    """Generate delta section for Report A (AI-consumable format)."""
    resolved_ids = ", ".join(f["id"] for f in delta_data["resolved"]) or "none"
    new_ids = ", ".join(f["id"] for f in delta_data["new"]) or "none"

    score_delta = current_score - previous_score
    delta_sign = "+" if score_delta >= 0 else ""

    return f"""## DELTA FROM PREVIOUS SCAN (Cycle {cycle_number})
- Findings resolved: {delta_data["resolved_count"]} ({resolved_ids})
- New findings: {delta_data["new_count"]} ({new_ids})
- Unchanged: {delta_data["unchanged_count"]}
- Score: {previous_score} → {current_score} ({delta_sign}{score_delta:.1f})

---

"""


def _generate_delta_section_b(
    delta_data: Dict[str, Any],
    cycle_number: int,
    previous_score: float,
    current_score: float
) -> str:
    """Generate delta section for Report B (human-readable format)."""
    lines = [f"### Changes Since Last Scan (Cycle {cycle_number})\n"]

    # Resolved findings with strikethrough
    lines.append(f"**Resolved ({delta_data['resolved_count']})**")
    if delta_data["resolved"]:
        for f in delta_data["resolved"]:
            lines.append(f"- ~~{f.get('title', f['id'])}~~")
    else:
        lines.append("- _None_")
    lines.append("")

    # New findings with warning flags
    lines.append(f"**New Issues ({delta_data['new_count']})**")
    if delta_data["new"]:
        for f in delta_data["new"]:
            lines.append(f"- ⚠️ {f.get('title', f['id'])}")
    else:
        lines.append("- _None_")
    lines.append("")

    # Still open
    lines.append(f"**Still Open ({delta_data['unchanged_count']})**")
    lines.append("")

    # Score delta
    score_delta = current_score - previous_score
    delta_sign = "+" if score_delta >= 0 else ""
    lines.append(f"**Score:** {previous_score} → {current_score} ({delta_sign}{score_delta:.1f})")
    lines.append("\n---\n")

    return "\n".join(lines)


async def generate_reports(
    scan_id: str,
    url: str,
    synthesis: SynthesisResult,
    tech_stack: TechStack,
    api_key: str,
    llm_provider: str = "gemini",
    delta_data: Optional[Dict[str, Any]] = None,
    cycle_number: Optional[int] = None,
    previous_score: Optional[float] = None
) -> Tuple[Path, Path]:
    """Step 10: Generate dual reports (A: AI handoff, B: Human review).

    Optional delta params for rescan reports:
        delta_data: Output from generate_delta_report() containing resolved/new/unchanged
        cycle_number: Current cycle number (2, 3, etc.)
        previous_score: Score from the previous scan for delta display
    """

    client = LLMClient(api_key, llm_provider)
    reports_path = REPORTS_DIR / scan_id
    reports_path.mkdir(parents=True, exist_ok=True)

    # Organize findings by severity
    critical = [f for f in synthesis.deduplicated_findings if f.severity == "critical"]
    high = [f for f in synthesis.deduplicated_findings if f.severity == "high"]
    medium = [f for f in synthesis.deduplicated_findings if f.severity == "medium"]
    low = [f for f in synthesis.deduplicated_findings if f.severity == "low"]

    print(f"📝 Report generation: {len(critical)} critical, {len(high)} high, {len(medium)} medium, {len(low)} low")

    # Generate Report A (AI Handoff)
    report_a_prompt = load_prompt(
        "report_a_generation",
        url=url,
        verdict=synthesis.verdict,
        overall_score=synthesis.overall_score,
        overall_grade=synthesis.overall_grade,
        tech_stack=tech_stack.model_dump(),
        scan_date=datetime.utcnow().isoformat(),
        critical_findings=[f.model_dump() for f in critical],
        high_findings=[f.model_dump() for f in high],
        medium_findings=[f.model_dump() for f in medium],
        low_findings=[f.model_dump() for f in low]
    )

    report_a_content = await client.generate(report_a_prompt, model_tier="pro", expect_json=False)

    # Insert delta section after header if delta data provided
    if delta_data is not None and cycle_number is not None and previous_score is not None:
        delta_section_a = _generate_delta_section_a(
            delta_data, cycle_number, previous_score, synthesis.overall_score
        )
        report_a_content = _insert_delta_after_header(report_a_content, delta_section_a)

    report_a_path = reports_path / "report_a.md"
    with open(report_a_path, "w", encoding="utf-8") as f:
        f.write(report_a_content)

    # Generate Report B (Human Review)
    report_b_prompt = load_prompt(
        "report_b_generation",
        url=url,
        verdict=synthesis.verdict,
        verdict_emoji=get_verdict_emoji(synthesis.verdict),
        overall_score=synthesis.overall_score,
        overall_grade=synthesis.overall_grade,
        verdict_reasoning=synthesis.verdict_reasoning,
        lens_scores={k: v.model_dump() for k, v in synthesis.lens_scores.items()},
        top_3_actions=synthesis.top_3_actions,
        systemic_patterns=synthesis.systemic_patterns,
        critical_findings=[f.model_dump() for f in critical],
        high_findings=[f.model_dump() for f in high],
        medium_findings=[f.model_dump() for f in medium],
        low_findings=[f.model_dump() for f in low]
    )

    report_b_content = await client.generate(report_b_prompt, model_tier="pro", expect_json=False)

    # Insert delta section after header if delta data provided
    if delta_data is not None and cycle_number is not None and previous_score is not None:
        delta_section_b = _generate_delta_section_b(
            delta_data, cycle_number, previous_score, synthesis.overall_score
        )
        report_b_content = _insert_delta_after_header(report_b_content, delta_section_b)

    report_b_path = reports_path / "report_b.md"
    with open(report_b_path, "w", encoding="utf-8") as f:
        f.write(report_b_content)

    return report_a_path, report_b_path


def _insert_delta_after_header(content: str, delta_section: str) -> str:
    """Insert delta section after the first '---' separator (end of header)."""
    parts = content.split("---", 1)
    if len(parts) < 2:
        # No separator found, prepend delta section
        return delta_section + content
    return parts[0] + "---\n\n" + delta_section + parts[1].lstrip("\n")
