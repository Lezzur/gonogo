from typing import Optional
from schemas import ReconData, IntentAnalysis
from llm.client import LLMClient
from llm.prompt_loader import load_prompt


async def analyze_intent(
    recon_data: ReconData,
    user_brief: Optional[str],
    api_key: str,
    llm_provider: str = "gemini"
) -> IntentAnalysis:
    """Step 1: Analyze project intent from user brief and recon data."""

    client = LLMClient(api_key, llm_provider)

    # Prepare context
    homepage = next((p for p in recon_data.pages if p.page_type == "homepage"), None)
    if not homepage and recon_data.pages:
        homepage = recon_data.pages[0]

    # Extract visible text (first 500 words from DOM if available)
    visible_text = ""
    if homepage and homepage.dom_snapshot:
        import re
        text = re.sub(r'<[^>]+>', ' ', homepage.dom_snapshot)
        text = re.sub(r'\s+', ' ', text).strip()
        words = text.split()[:500]
        visible_text = ' '.join(words)

    # Build prompt
    prompt = load_prompt(
        "intent_analysis",
        user_brief=user_brief or "No brief provided",
        meta_tags=recon_data.meta_tags,
        og_tags=recon_data.og_tags,
        navigation_structure=list(recon_data.page_type_map.keys()),
        visible_text=visible_text[:2000]
    )

    # Include homepage screenshot if available
    images = []
    if homepage and homepage.screenshot_desktop:
        images.append(homepage.screenshot_desktop)

    result = await client.generate(prompt, images=images, model_tier="pro")

    return IntentAnalysis(**result)
