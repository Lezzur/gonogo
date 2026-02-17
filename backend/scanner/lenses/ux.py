from typing import List
from schemas import ReconData, IntentAnalysis, TechStack, Finding
from llm.client import LLMClient
from llm.prompt_loader import load_prompt


async def evaluate_ux(
    recon_data: ReconData,
    intent: IntentAnalysis,
    tech_stack: TechStack,
    api_key: str,
    llm_provider: str = "gemini"
) -> List[Finding]:
    """Step 5: Evaluate UX flow - navigation, CTAs, forms, mobile experience."""

    client = LLMClient(api_key, llm_provider)

    # Build navigation sequence from pages
    page_sequence = []
    for page in recon_data.pages:
        page_sequence.append({
            "url": page.url,
            "title": page.title,
            "page_type": page.page_type,
            "has_forms": len(page.form_elements) > 0,
            "interactive_count": len(page.interactive_elements)
        })

    # Collect form details
    form_details = []
    for page in recon_data.pages:
        for form in page.form_elements:
            form_details.append({
                "page": page.url,
                "inputs": form.get("inputs", [])
            })

    # Collect screenshots in navigation order with descriptions
    screenshots = []
    screenshot_descriptions = []
    for page in recon_data.pages[:6]:
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
        "ux_lens",
        intent_analysis=intent.model_dump(),
        tech_stack=tech_stack.model_dump(),
        page_sequence=page_sequence,
        page_structure=page_sequence,
        screenshot_descriptions=screenshot_descriptions,
        form_details=form_details[:10],
        key_user_journeys=intent.key_user_journeys
    )

    result = await client.generate(prompt, images=screenshots[:8], model_tier="pro")

    findings = []
    for f in result.get("findings", []):
        try:
            findings.append(Finding(**f))
        except Exception:
            continue

    return findings
