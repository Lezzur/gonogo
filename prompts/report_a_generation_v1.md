# Report A Generation Prompt — v1.1
# Model: gemini-3-pro-preview
# Last updated: 2026-02-14

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
- **Values:** [raw_data values if any - hex colors, measurements, etc. ONLY include if present in evidence]
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
7. **INCLUDE RAW VALUES**: If the finding has raw_data (hex colors like #3B82F6, Tailwind classes like bg-blue-500, measurements), include them in the **Values:** field. This makes fixes precise.

## Example Entries

### Functionality Issue Example
```
### FUNC-001: Checkout form fails silently on submit
- **Page:** /checkout
- **Selector:** form#checkout-form button[type=submit]
- **Issue:** Form submission triggers "Cannot read property 'submit' of undefined". Users see no feedback and cannot complete purchases.
- **Console:** TypeError: Cannot read property 'submit' of undefined at handleSubmit (checkout.js:45)
- **Values:** N/A
- **Fix:** In the checkout form component, the form ref is null when handleSubmit runs. Add early return: `if (!formRef.current) return;` at the start of handleSubmit. Alternatively, move form ref initialization to useEffect or ensure component is mounted before attaching handler.
- **File hint:** src/components/CheckoutForm.tsx or src/pages/checkout.js
```

### Design Issue Example (with raw values)
```
### DESIGN-002: Inconsistent button colors
- **Page:** /
- **Selector:** button[type='submit'], a.btn-primary
- **Issue:** Primary buttons use different shades of blue, creating visual inconsistency.
- **Console:** N/A
- **Values:** Sign In button: #3B82F6 (bg-blue-500), Get Started button: #2563EB (bg-blue-600)
- **Fix:** Standardize all primary buttons to use bg-blue-600 (#2563EB). Search for `bg-blue-500` and replace with `bg-blue-600`, OR search for `#3B82F6` and replace with `#2563EB`.
- **File hint:** Search codebase for button components or global styles.
```
