from typing import List
from schemas import ReconData, IntentAnalysis, TechStack, Finding
from llm.client import LLMClient
from llm.prompt_loader import load_prompt


async def evaluate_accessibility(
    recon_data: ReconData,
    intent: IntentAnalysis,
    tech_stack: TechStack,
    api_key: str,
    llm_provider: str = "gemini"
) -> List[Finding]:
    """Step 7: Evaluate accessibility - WCAG compliance, axe-core violations."""

    client = LLMClient(api_key, llm_provider)

    # Extract axe-core violations
    axe_report = recon_data.axe_report
    violations = axe_report.get("violations", [])

    # Process violations into structured format
    axe_violations = []
    for v in violations:
        axe_violations.append({
            "id": v.get("id"),
            "impact": v.get("impact"),
            "description": v.get("description"),
            "help": v.get("help"),
            "helpUrl": v.get("helpUrl"),
            "nodes_count": len(v.get("nodes", [])),
            "nodes": [
                {
                    "html": n.get("html", "")[:200],
                    "target": n.get("target", [])[:3]
                }
                for n in v.get("nodes", [])[:5]
            ]
        })

    # Extract Lighthouse accessibility audit
    lighthouse = recon_data.lighthouse_report
    a11y_category = lighthouse.get("categories", {}).get("accessibility", {})
    a11y_score = a11y_category.get("score", 0) * 100

    # Get specific accessibility audits
    audits = lighthouse.get("audits", {})
    failed_audits = []
    for audit_id, audit in audits.items():
        if audit.get("scoreDisplayMode") == "binary" and audit.get("score") == 0:
            if "accessibility" in audit.get("description", "").lower():
                failed_audits.append({
                    "id": audit_id,
                    "title": audit.get("title"),
                    "description": audit.get("description")
                })

    # Collect image alt text data
    images_without_alt = []
    for page in recon_data.pages:
        for img in page.images:
            if not img.get("alt"):
                images_without_alt.append({
                    "page": page.url,
                    "src": img.get("src")
                })

    prompt = load_prompt(
        "accessibility_lens",
        intent_analysis=intent.model_dump(),
        tech_stack=tech_stack.model_dump(),
        accessibility_score=a11y_score,
        axe_violations=axe_violations[:30],
        failed_lighthouse_audits=failed_audits[:20],
        images_without_alt=images_without_alt[:20]
    )

    # No screenshots needed for accessibility
    result = await client.generate(prompt, model_tier="flash")

    findings = []
    for f in result.get("findings", []):
        try:
            findings.append(Finding(**f))
        except Exception:
            continue

    return findings
