from typing import List
from schemas import ReconData, IntentAnalysis, TechStack, Finding
from llm.client import LLMClient
from llm.prompt_loader import load_prompt


async def evaluate_functionality(
    recon_data: ReconData,
    intent: IntentAnalysis,
    tech_stack: TechStack,
    api_key: str,
    llm_provider: str = "gemini"
) -> List[Finding]:
    """Step 3: Evaluate functionality - JS errors, broken links, forms, etc."""

    client = LLMClient(api_key, llm_provider)

    # Gather evidence
    console_errors = []
    for page in recon_data.pages:
        for log in page.console_logs:
            if log.get("level") == "error":
                console_errors.append({
                    "page": page.url,
                    "message": log.get("message", "")
                })

    broken_links = [
        link.model_dump() for link in recon_data.links_audit
        if link.status_code >= 400 or link.status_code == 0
    ]

    forms = []
    for page in recon_data.pages:
        for form in page.form_elements:
            forms.append({
                "page": page.url,
                "form": form
            })

    interactive_elements = []
    for page in recon_data.pages:
        interactive_elements.extend([
            {"page": page.url, **el}
            for el in page.interactive_elements[:20]
        ])

    broken_images = []
    for page in recon_data.pages:
        for img in page.images:
            if not img.get("loaded"):
                broken_images.append({
                    "page": page.url,
                    "src": img.get("src"),
                    "alt": img.get("alt")
                })

    prompt = load_prompt(
        "functionality_lens",
        intent_analysis=intent.model_dump(),
        tech_stack=tech_stack.model_dump(),
        console_errors=console_errors[:50],
        broken_links=broken_links[:50],
        forms=forms[:20],
        interactive_elements=interactive_elements[:50],
        broken_images=broken_images[:20]
    )

    result = await client.generate(prompt, model_tier="flash")

    print(f"🔍 Functionality lens LLM returned: {len(result.get('findings', []))} findings")

    findings = []
    for f in result.get("findings", []):
        try:
            findings.append(Finding(**f))
        except Exception as e:
            print(f"⚠️  Failed to parse finding: {e}")
            continue

    print(f"✅ Functionality lens parsed {len(findings)} valid findings")
    return findings
