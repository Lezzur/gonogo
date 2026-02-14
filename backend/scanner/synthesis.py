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
    llm_provider: str = "gemini",
    auth_status: str = "no_auth_required"
) -> SynthesisResult:
    """Step 9: Synthesize findings, deduplicate, score, and determine verdict."""

    client = LLMClient(api_key, llm_provider)

    # Format auth status for prompt
    auth_status_text = {
        "no_auth_required": "No authentication was required for this scan.",
        "auth_successful": "Authentication was SUCCESSFUL - agent was able to access authenticated pages. Any auth-related console errors were handled/recovered.",
        "auth_attempted_unclear": "Authentication was attempted but status unclear."
    }.get(auth_status, auth_status)

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
        severity_counts=severity_counts,
        auth_status=auth_status_text
    )

    result = await client.generate(prompt, model_tier="pro")

    print(f"🔍 Synthesis LLM returned {len(result.get('deduplicated_findings', []))} deduplicated findings")

    # Debug: Log severity distribution from synthesis
    synth_severities = {}
    for f in result.get('deduplicated_findings', []):
        sev = f.get('severity', 'unknown') if isinstance(f, dict) else 'non-dict'
        synth_severities[sev] = synth_severities.get(sev, 0) + 1
    print(f"   Severities from synthesis: {synth_severities}")

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
    raw_findings = result.get("deduplicated_findings", [])
    print(f"   Raw deduplicated_findings count: {len(raw_findings)}, type: {type(raw_findings)}")

    # If synthesis didn't return findings, use original findings
    if not raw_findings:
        print(f"   ⚠️  No deduplicated_findings in synthesis, using original {len(findings)} findings")
        raw_findings = [f.model_dump() for f in findings]

    for i, f in enumerate(raw_findings):
        try:
            if isinstance(f, dict):
                # Normalize severity to lowercase
                if "severity" in f:
                    f["severity"] = f["severity"].lower().strip()
                    # Map any variations to standard values
                    severity_map = {
                        "crit": "critical",
                        "hi": "high",
                        "med": "medium",
                        "lo": "low",
                    }
                    f["severity"] = severity_map.get(f["severity"], f["severity"])
                deduplicated.append(Finding(**f))
            elif hasattr(f, 'model_dump'):
                # It's already a Finding object
                deduplicated.append(f)
            else:
                print(f"   ⚠️  Finding {i} is unexpected type: {type(f)}")
        except Exception as e:
            print(f"   ⚠️  Failed to parse finding {i} in synthesis: {e}")
            if isinstance(f, dict):
                print(f"      Keys: {f.keys()}")
            continue

    # Debug: Log parsed findings severities
    parsed_severities = {}
    for f in deduplicated:
        sev = f.severity if hasattr(f, 'severity') else 'no-attr'
        parsed_severities[sev] = parsed_severities.get(sev, 0) + 1
    print(f"   Parsed findings severities: {parsed_severities}")
    print(f"   Total deduplicated findings: {len(deduplicated)}")

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
