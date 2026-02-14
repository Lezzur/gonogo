import re
from typing import List
from schemas import ReconData, IntentAnalysis, TechStack, Finding
from llm.client import LLMClient
from llm.prompt_loader import load_prompt


async def evaluate_code_content(
    recon_data: ReconData,
    intent: IntentAnalysis,
    tech_stack: TechStack,
    api_key: str,
    llm_provider: str = "gemini"
) -> List[Finding]:
    """Step 8: Evaluate code quality and content - SEO, semantics, placeholders."""

    client = LLMClient(api_key, llm_provider)

    # Analyze meta tags for SEO
    meta_tags = recon_data.meta_tags
    og_tags = recon_data.og_tags

    seo_analysis = {
        "has_title": bool(meta_tags.get("title") or recon_data.pages[0].title if recon_data.pages else False),
        "has_description": bool(meta_tags.get("description")),
        "has_og_title": bool(og_tags.get("og:title")),
        "has_og_description": bool(og_tags.get("og:description")),
        "has_og_image": bool(og_tags.get("og:image")),
        "has_canonical": "canonical" in str(meta_tags).lower(),
        "has_robots": bool(meta_tags.get("robots"))
    }

    # Check for placeholder content
    placeholder_patterns = [
        r"lorem ipsum",
        r"placeholder",
        r"\bTODO\b",
        r"\bFIXME\b",
        r"\basdf\b",
        r"\btest\s*(text|content|data)\b",
        r"coming soon",
        r"under construction"
    ]

    placeholder_content = []
    for page in recon_data.pages:
        if page.dom_snapshot:
            text = re.sub(r'<[^>]+>', ' ', page.dom_snapshot).lower()
            for pattern in placeholder_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    placeholder_content.append({
                        "page": page.url,
                        "pattern": pattern,
                        "count": len(matches)
                    })

    # Check console for leftover logs
    console_logs_left = []
    for page in recon_data.pages:
        for log in page.console_logs:
            if log.get("level") == "log":
                console_logs_left.append({
                    "page": page.url,
                    "message": log.get("message", "")[:100]
                })

    # Analyze semantic HTML
    semantic_analysis = {
        "pages_analyzed": len(recon_data.pages)
    }

    # Check heading structure
    for page in recon_data.pages[:3]:
        if page.dom_snapshot:
            h1_count = len(re.findall(r'<h1[^>]*>', page.dom_snapshot, re.IGNORECASE))
            semantic_analysis[page.url] = {
                "h1_count": h1_count,
                "has_main": "<main" in page.dom_snapshot.lower(),
                "has_nav": "<nav" in page.dom_snapshot.lower(),
                "has_footer": "<footer" in page.dom_snapshot.lower()
            }

    # Get Lighthouse SEO/best-practices scores
    lighthouse = recon_data.lighthouse_report
    categories = lighthouse.get("categories", {})
    seo_score = categories.get("seo", {}).get("score", 0) * 100
    best_practices_score = categories.get("best-practices", {}).get("score", 0) * 100

    prompt = load_prompt(
        "code_content_lens",
        intent_analysis=intent.model_dump(),
        tech_stack=tech_stack.model_dump(),
        seo_analysis=seo_analysis,
        seo_score=seo_score,
        best_practices_score=best_practices_score,
        placeholder_content=placeholder_content[:20],
        console_logs_left=console_logs_left[:20],
        semantic_analysis=semantic_analysis,
        meta_tags=meta_tags,
        og_tags=og_tags
    )

    # Include homepage screenshot for content review
    images = []
    if recon_data.pages and recon_data.pages[0].screenshot_desktop:
        images.append(recon_data.pages[0].screenshot_desktop)

    result = await client.generate(prompt, images=images[:1], model_tier="flash")

    findings = []
    for f in result.get("findings", []):
        try:
            findings.append(Finding(**f))
        except Exception:
            continue

    return findings
