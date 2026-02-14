from pathlib import Path
from datetime import datetime
from typing import Tuple

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


async def generate_reports(
    scan_id: str,
    url: str,
    synthesis: SynthesisResult,
    tech_stack: TechStack,
    api_key: str,
    llm_provider: str = "gemini"
) -> Tuple[Path, Path]:
    """Step 10: Generate dual reports (A: AI handoff, B: Human review)."""

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

    report_b_path = reports_path / "report_b.md"
    with open(report_b_path, "w", encoding="utf-8") as f:
        f.write(report_b_content)

    return report_a_path, report_b_path
