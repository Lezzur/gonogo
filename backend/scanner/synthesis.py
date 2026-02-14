from typing import List
from schemas import Finding, IntentAnalysis, SynthesisResult, LensScore
from llm.client import LLMClient
from llm.prompt_loader import load_prompt


def calculate_grade(score: int) -> str:
    """Convert numeric score to letter grade."""
    if score >= 97:
        return "A+"
    elif score >= 93:
        return "A"
    elif score >= 90:
        return "A-"
    elif score >= 87:
        return "B+"
    elif score >= 83:
        return "B"
    elif score >= 80:
        return "B-"
    elif score >= 77:
        return "C+"
    elif score >= 73:
        return "C"
    elif score >= 70:
        return "C-"
    elif score >= 67:
        return "D+"
    elif score >= 63:
        return "D"
    elif score >= 60:
        return "D-"
    else:
        return "F"


async def synthesize_findings(
    findings: List[Finding],
    intent_analysis: IntentAnalysis,
    api_key: str,
    llm_provider: str = "gemini"
) -> SynthesisResult:
    """Step 9: Synthesize findings, deduplicate, score, and determine verdict."""

    client = LLMClient(api_key, llm_provider)

    # Group findings by lens
    findings_by_lens = {}
    for f in findings:
        if f.lens not in findings_by_lens:
            findings_by_lens[f.lens] = []
        findings_by_lens[f.lens].append(f.model_dump())

    # Count by severity
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1

    prompt = load_prompt(
        "synthesis",
        intent_analysis=intent_analysis.model_dump(),
        findings_by_lens=findings_by_lens,
        total_findings=len(findings),
        severity_counts=severity_counts
    )

    result = await client.generate(prompt, model_tier="pro")

    print(f"🔍 Synthesis LLM returned {len(result.get('deduplicated_findings', []))} deduplicated findings")

    # Parse lens scores
    lens_scores = {}
    for lens_name, score_data in result.get("lens_scores", {}).items():
        lens_scores[lens_name] = LensScore(
            score=score_data.get("score", 50),
            grade=score_data.get("grade", calculate_grade(score_data.get("score", 50))),
            summary=score_data.get("summary", "")
        )

    # Parse deduplicated findings
    deduplicated = []
    for f in result.get("deduplicated_findings", findings):
        try:
            if isinstance(f, dict):
                deduplicated.append(Finding(**f))
            else:
                deduplicated.append(f)
        except Exception:
            continue

    return SynthesisResult(
        overall_score=result.get("overall_score", 50),
        overall_grade=result.get("overall_grade", calculate_grade(result.get("overall_score", 50))),
        verdict=result.get("verdict", "GO_WITH_CONDITIONS"),
        verdict_reasoning=result.get("verdict_reasoning", ""),
        lens_scores=lens_scores,
        findings_count=result.get("findings_count", severity_counts),
        top_3_actions=result.get("top_3_actions", [])[:3],
        deduplicated_findings=deduplicated,
        systemic_patterns=result.get("systemic_patterns", [])
    )
