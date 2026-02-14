# Report A Generation Prompt — v1
# Model: gemini-2.5-pro
# Last updated: 2024-01-01

## System

Generate Report A — the AI-consumable handoff document. This report will be pasted directly into a coding AI (Claude, Cursor, etc.) to implement fixes. Every finding must be actionable WITHOUT asking for clarification.

## Context

URL: {{url}}
Verdict: {{verdict}}
Score: {{overall_score}}/100 ({{overall_grade}})
Tech Stack: {{tech_stack}}
Scan Date: {{scan_date}}

## Findings

Critical:
{{critical_findings}}

High:
{{high_findings}}

Medium:
{{medium_findings}}

Low:
{{low_findings}}

## Output Instructions

Generate a complete markdown document. Do NOT wrap in code blocks. Output the raw markdown directly.

Use this exact structure:

```
# GoNoGo Report A — AI Handoff
# URL: [url]
# Verdict: [verdict]
# Score: [score]/100 ([grade])
# Tech Stack: [tech stack summary]
# Scanned: [date]

---

## CRITICAL — Fix Before Launch

### [ID]: [title]
- **Page:** [page_url]
- **Selector:** [dom_selector]
- **Issue:** [description]
- **Console:** [console_errors if any]
- **Fix:** [ai_actionable recommendation - THIS IS THE KEY PART]
- **File hint:** [likely file path based on tech stack]

[Repeat for each critical finding]

---

## HIGH PRIORITY

[Same structure for each finding]

---

## MEDIUM PRIORITY

[Same structure for each finding]

---

## LOW PRIORITY

[Same structure for each finding]
```

## Design Principles

1. **Zero ambiguity**: Every instruction should be precise enough that a coding AI can act immediately
2. **Include selectors**: CSS selectors from the evidence data ONLY
3. **Include fix code**: Actual code snippets when relevant
4. **No conversational tone**: Pure signal, maximum density
5. **DO NOT INVENT FILE PATHS**: Only include file hints if they were in the original finding evidence. If no file path was provided, write "File hint: Search codebase for [selector/component name]" instead of guessing paths like "src/components/X.tsx"
6. **DO NOT ADD FINDINGS**: Only format the findings provided. Do not create new issues.

## Example Entry

```
### FUNC-001: Checkout form fails silently on submit
- **Page:** /checkout
- **Selector:** form#checkout-form button[type=submit]
- **Issue:** Form submission triggers "Cannot read property 'submit' of undefined". Users see no feedback and cannot complete purchases.
- **Console:** TypeError: Cannot read property 'submit' of undefined at handleSubmit (checkout.js:45)
- **Fix:** In the checkout form component, the form ref is null when handleSubmit runs. Add early return: `if (!formRef.current) return;` at the start of handleSubmit. Alternatively, move form ref initialization to useEffect or ensure component is mounted before attaching handler.
- **File hint:** src/components/CheckoutForm.tsx or src/pages/checkout.js
```
