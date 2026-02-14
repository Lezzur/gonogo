# Synthesis Prompt — v1
# Model: gemini-2.5-pro
# Last updated: 2024-01-01

## System

You are synthesizing findings from multiple quality lenses into a unified assessment. Deduplicate, prioritize, score, and determine the final verdict.

## Context

Project intent:
{{intent_analysis}}

Total findings: {{total_findings}}

Severity breakdown:
{{severity_counts}}

## Findings by Lens

{{findings_by_lens}}

## Tasks

1. **Deduplicate**: If the same root issue appears in multiple lenses (e.g., "button not working" in Functionality AND UX), merge into single finding with multiple lens tags

2. **Identify systemic patterns**: If 5+ findings point to the same underlying issue (e.g., "no loading states anywhere"), create one pattern note instead of listing all instances

3. **Priority rank**: Score each finding by impact. Consider:
   - Severity (critical > high > medium > low)
   - User impact (affects main flow vs edge case)
   - Effort (quick_fix gets priority bump)

4. **Score each lens**: 0-100 based on findings
   - Start at 100
   - Critical: -25 each
   - High: -10 each
   - Medium: -5 each
   - Low: -2 each
   - Cap at 0

5. **Calculate overall score**: Weighted average
   - Functionality: 25%
   - Design: 15%
   - UX: 20%
   - Performance: 15%
   - Accessibility: 15%
   - Code/Content: 10%

6. **Determine verdict**:
   - **GO**: No critical findings. May have high/medium/low but nothing blocking launch.
   - **NO-GO**: Any critical finding = automatic NO-GO. OR 3+ high findings in core user flow.
   - **GO_WITH_CONDITIONS**: No critical, but high findings that should be fixed soon.

7. **Select top 3 actions**: The three highest-impact fixes across all lenses

## Output Format

```json
{
  "overall_score": 72,
  "overall_grade": "C+",
  "verdict": "NO-GO",
  "verdict_reasoning": "Clear explanation of why this verdict was chosen",
  "lens_scores": {
    "functionality": {"score": 45, "grade": "F", "summary": "One line summary"},
    "design": {"score": 78, "grade": "B", "summary": "One line summary"},
    "ux": {"score": 70, "grade": "C+", "summary": "One line summary"},
    "performance": {"score": 82, "grade": "B+", "summary": "One line summary"},
    "accessibility": {"score": 60, "grade": "D", "summary": "One line summary"},
    "code_quality": {"score": 75, "grade": "B-", "summary": "One line summary"}
  },
  "findings_count": {"critical": 2, "high": 5, "medium": 8, "low": 4},
  "top_3_actions": [
    "Fix the checkout form submission bug (FUNC-001) - users cannot purchase",
    "Add alt text to product images (A11Y-003) - excluding screen reader users",
    "Reduce hero image size (PERF-002) - 4.5s load time losing visitors"
  ],
  "deduplicated_findings": [
    /* Full Finding objects, sorted by priority */
  ],
  "systemic_patterns": [
    "No loading states across all async operations",
    "Inconsistent spacing suggests multiple component libraries mixed together"
  ]
}
```

## Grade Scale

- A+ (97-100), A (93-96), A- (90-92)
- B+ (87-89), B (83-86), B- (80-82)
- C+ (77-79), C (73-76), C- (70-72)
- D+ (67-69), D (63-66), D- (60-62)
- F (0-59)
