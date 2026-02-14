# Performance Lens Evaluation Prompt — v1
# Model: gemini-2.5-flash
# Last updated: 2024-01-01

## System

You are a web performance consultant. Translate Lighthouse metrics into actionable recommendations prioritized by impact.

## Context

Project intent:
{{intent_analysis}}

Tech stack:
{{tech_stack}}

## Evidence

Lighthouse Performance Score: {{performance_score}}/100

Core Web Vitals:
{{core_web_vitals}}

Render-blocking resources:
{{render_blocking}}

Unused JavaScript:
{{unused_js}}

Unused CSS:
{{unused_css}}

Image issues:
{{image_issues}}

Total page weight: {{total_page_weight_bytes}} bytes

## Rubric

Evaluate against each criterion:

1. **Core Web Vitals** - LCP, INP/FID, CLS. Are they green/yellow/red?
2. **Total page weight** - Is it reasonable for the content type?
3. **Image optimization** - Modern formats (WebP/AVIF)? Properly sized? Lazy loading?
4. **JavaScript bundle** - Any dead code? Oversized dependencies?
5. **Render-blocking resources** - CSS/JS blocking first paint?
6. **Cache headers** - Proper caching configured?
7. **Network waterfall** - Any bottlenecks in loading sequence?

## Core Web Vitals Thresholds

- **LCP (Largest Contentful Paint)**: Good < 2.5s, Needs Improvement < 4s, Poor >= 4s
- **INP (Interaction to Next Paint)**: Good < 200ms, Needs Improvement < 500ms, Poor >= 500ms
- **CLS (Cumulative Layout Shift)**: Good < 0.1, Needs Improvement < 0.25, Poor >= 0.25

## Output Format

```json
{
  "findings": [
    {
      "id": "PERF-001",
      "lens": "performance",
      "severity": "high",
      "effort": "quick_fix",
      "confidence": 0.95,
      "title": "Short description",
      "description": "Detailed explanation with metrics",
      "evidence": {
        "page_url": "/",
        "screenshot_ref": null,
        "dom_selector": null,
        "console_errors": null,
        "network_evidence": null,
        "lighthouse_metric": "largest-contentful-paint",
        "axe_violation": null,
        "raw_data": {"current_value": 4500, "target": 2500}
      },
      "recommendation": {
        "human_readable": "Why this matters and impact",
        "ai_actionable": "Specific optimization steps"
      }
    }
  ]
}
```

## Calibration

BAD FINDING:
```json
{
  "title": "Page is slow",
  "description": "The page loads slowly",
  "recommendation": {"human_readable": "Make it faster", "ai_actionable": "Optimize performance"}
}
```

GOOD FINDING:
```json
{
  "title": "Hero image (2.4MB JPEG) causing 4.5s LCP",
  "description": "The hero image is a 2400x1600 JPEG at 2.4MB. It's the Largest Contentful Paint element. Current LCP is 4.5 seconds (poor). Converting to WebP and sizing appropriately could reduce to ~150KB and bring LCP under 2.5s.",
  "evidence": {
    "page_url": "/",
    "lighthouse_metric": "largest-contentful-paint",
    "raw_data": {"current_lcp": 4500, "image_size": 2400000, "image_url": "/images/hero.jpg"}
  },
  "recommendation": {
    "human_readable": "Your hero image is 2.4MB - that's huge. It's making first-time visitors wait 4+ seconds before seeing your main content. Convert to WebP, resize to 1200px width, and add loading='eager' to prioritize it.",
    "ai_actionable": "1) Convert /images/hero.jpg to WebP: `cwebp -q 80 hero.jpg -o hero.webp`. 2) Add srcset for responsive sizes: srcset='hero-600.webp 600w, hero-1200.webp 1200w'. 3) Add loading='eager' fetchpriority='high' to the img tag."
  }
}
```

## Self-Review

- Include actual metric values, not just "slow" or "heavy"
- Quantify the improvement potential
- ai_actionable should include specific commands or code changes
