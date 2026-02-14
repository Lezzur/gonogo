from typing import List
from schemas import ReconData, IntentAnalysis, TechStack, Finding
from llm.client import LLMClient
from llm.prompt_loader import load_prompt


async def evaluate_performance(
    recon_data: ReconData,
    intent: IntentAnalysis,
    tech_stack: TechStack,
    api_key: str,
    llm_provider: str = "gemini"
) -> List[Finding]:
    """Step 6: Evaluate performance - Core Web Vitals, page weight, etc."""

    client = LLMClient(api_key, llm_provider)

    # Extract Lighthouse metrics
    lighthouse = recon_data.lighthouse_report
    audits = lighthouse.get("audits", {})
    categories = lighthouse.get("categories", {})

    performance_score = categories.get("performance", {}).get("score", 0) * 100

    core_web_vitals = {
        "lcp": audits.get("largest-contentful-paint", {}).get("numericValue"),
        "fid": audits.get("max-potential-fid", {}).get("numericValue"),
        "cls": audits.get("cumulative-layout-shift", {}).get("numericValue"),
        "fcp": audits.get("first-contentful-paint", {}).get("numericValue"),
        "tti": audits.get("interactive", {}).get("numericValue"),
        "tbt": audits.get("total-blocking-time", {}).get("numericValue")
    }

    # Extract specific audit results
    render_blocking = audits.get("render-blocking-resources", {})
    unused_js = audits.get("unused-javascript", {})
    unused_css = audits.get("unused-css-rules", {})
    image_optimization = audits.get("uses-optimized-images", {})
    modern_formats = audits.get("modern-image-formats", {})

    # Calculate total page weight from network requests
    total_size = 0
    for page in recon_data.pages:
        for req in page.network_requests:
            total_size += req.get("size", 0)

    prompt = load_prompt(
        "performance_lens",
        intent_analysis=intent.model_dump(),
        tech_stack=tech_stack.model_dump(),
        performance_score=performance_score,
        core_web_vitals=core_web_vitals,
        render_blocking=render_blocking.get("details", {}).get("items", [])[:10],
        unused_js=unused_js.get("details", {}).get("items", [])[:10],
        unused_css=unused_css.get("details", {}).get("items", [])[:10],
        image_issues={
            "unoptimized": image_optimization.get("details", {}).get("items", [])[:10],
            "legacy_formats": modern_formats.get("details", {}).get("items", [])[:10]
        },
        total_page_weight_bytes=total_size
    )

    # No screenshots needed for performance
    result = await client.generate(prompt, model_tier="flash")

    findings = []
    for f in result.get("findings", []):
        try:
            findings.append(Finding(**f))
        except Exception:
            continue

    return findings
