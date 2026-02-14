from typing import List
from schemas import ReconData, IntentAnalysis, TechStack, Finding
from llm.client import LLMClient
from llm.prompt_loader import load_prompt


async def evaluate_design(
    recon_data: ReconData,
    intent: IntentAnalysis,
    tech_stack: TechStack,
    api_key: str,
    llm_provider: str = "gemini"
) -> List[Finding]:
    """Step 4: Evaluate design quality - colors, typography, spacing, etc."""

    client = LLMClient(api_key, llm_provider)

    # Collect all screenshots (design evaluation is vision-heavy)
    screenshots = []
    screenshot_descriptions = []

    for page in recon_data.pages:
        if page.screenshot_desktop:
            screenshots.append(page.screenshot_desktop)
            screenshot_descriptions.append({
                "file": page.screenshot_desktop,
                "url": page.url,
                "type": "desktop",
                "page_type": page.page_type
            })
        if page.screenshot_mobile:
            screenshots.append(page.screenshot_mobile)
            screenshot_descriptions.append({
                "file": page.screenshot_mobile,
                "url": page.url,
                "type": "mobile",
                "page_type": page.page_type
            })

    prompt = load_prompt(
        "design_lens",
        intent_analysis=intent.model_dump(),
        tech_stack=tech_stack.model_dump(),
        screenshot_descriptions=screenshot_descriptions,
        framework_signatures=recon_data.framework_signatures
    )

    # Limit screenshots to avoid token limits
    result = await client.generate(prompt, images=screenshots[:10], model_tier="pro")

    findings = []
    for f in result.get("findings", []):
        try:
            findings.append(Finding(**f))
        except Exception:
            continue

    return findings
