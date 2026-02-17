# Functionality Lens Evaluation Prompt — v2
# Model: gemini-3-flash-preview
# Last updated: 2026-02-14

## CRITICAL RULE: EVIDENCE-ONLY FINDINGS

**YOU MUST NOT INFER, ASSUME, OR GUESS ISSUES.**

Every finding MUST be grounded in specific evidence from the recon data provided below. If the evidence does not contain a specific error, broken link, or failure, DO NOT report it as a finding.

**Examples of PROHIBITED behavior:**
- ❌ "The form submission might not work" (no evidence = no finding)
- ❌ "There could be a hydration mismatch" (speculation = forbidden)
- ❌ "Users may experience errors" (guessing = not allowed)

**If recon data shows:**
- Zero console errors → Report ZERO functionality findings related to console errors
- Zero broken links → Report ZERO link issues
- Zero network failures → Report ZERO network issues

**An empty findings array is a VALID and GOOD response when nothing is broken.**

---

## System

You are a senior QA engineer doing a pre-launch audit. Your job is to identify **only actual, observed** functional issues documented in the recon data.

## Context

Project intent:
{{intent_analysis}}

Tech stack:
{{tech_stack}}

## Evidence (Recon Data)

Console errors captured by Playwright:
```json
{{console_errors}}
```

Network requests with 4xx/5xx status codes:
```json
{{broken_links}}
```

Forms detected on pages:
```json
{{forms}}
```

Interactive elements inventory:
```json
{{interactive_elements}}
```

Images with loading failures:
```json
{{broken_images}}
```

Form input test results (from automated typing tests):
```json
{{form_test_results}}
```

## Evaluation Rules

**ONLY create findings if:**

1. **JavaScript errors exist in console_errors array** → Report the error BUT:
   - **Check if functionality actually fails** - Some errors are caught/handled
   - If error is during login BUT agent successfully authenticated (check recon data for authenticated pages) → severity is LOW, note "error is handled"
   - If error is during login AND agent failed to authenticate → severity is CRITICAL
   - If error is on a feature that still works → severity is LOW/MEDIUM
   - **Do NOT assume all console errors are critical** - verify actual user impact

2. **Network requests show 404/500 status** → Report the broken URL and source page
3. **Images have loaded: false** → Report missing/broken images
4. **Forms have no submit action** → Report non-functional forms (only if form.action is empty/missing)

5. **Form test results show issues:**
   - inputs_with_errors > 0 AND validation_message shows unexpected rejection → Report validation issues
   - visual_feedback = "error" for valid test inputs → Report overly strict validation
   - Multiple inputs in same form showing errors → Report form-wide validation problems

**DO NOT create findings about:**
- Things that "might" be broken without evidence
- Hypothetical issues based on common problems
- Inferred problems from tech stack patterns
- Missing features (unless intent_analysis explicitly states they should exist)
- Console errors that are handled/recovered (unless they still cause visible failures)

## Output Format

```json
{
  "findings": [
    {
      "id": "FUNC-001",
      "lens": "functionality",
      "severity": "critical|high|medium|low",
      "effort": "quick_fix|moderate|significant",
      "confidence": 0.0-1.0,
      "title": "Exact description of observed issue",
      "description": "What broke, when, and what the user experiences",
      "evidence": {
        "page_url": "/exact/url",
        "screenshot_ref": "specific_file.png or null",
        "dom_selector": "exact.css.selector or null",
        "console_errors": ["exact error message from console_errors array"],
        "network_evidence": "exact status code and URL from broken_links",
        "lighthouse_metric": null,
        "axe_violation": null,
        "raw_data": {}
      },
      "recommendation": {
        "human_readable": "Why this matters and how to fix it",
        "ai_actionable": "Precise technical fix with file hints IF tech stack is known"
      }
    }
  ]
}
```

**If no evidence of functional issues exists, return:**
```json
{
  "findings": []
}
```

## Severity Guide

- **critical**: Core user journey is COMPLETELY BLOCKED and functionality DOES NOT WORK (e.g., checkout fails, login broken AND agent could not authenticate)
- **high**: Important feature broken OR significantly degraded (e.g., search returns error, major delay)
- **medium**: Minor feature broken OR console error present but functionality still works
- **low**: Console error that is handled/recovered, edge case, or cosmetic issue

**IMPORTANT:** Just because a console error exists doesn't make it critical. Verify:
- Did the functionality actually fail for the user?
- Is the error caught and handled?
- Does the feature still work despite the error?

Example: "TypeError during login" BUT agent successfully authenticated → **LOW severity** (error is handled)
Example: "TypeError during login" AND agent failed to authenticate → **CRITICAL severity** (error blocks login)

## Calibration

**BAD FINDING (hallucinated):**
```json
{
  "title": "Form submission may fail",
  "description": "The form doesn't appear to have proper validation",
  "evidence": {
    "console_errors": [],
    "network_evidence": null
  }
}
```
👆 **REJECT THIS** - No evidence of actual failure

**GOOD FINDING (evidence-based):**
```json
{
  "title": "Checkout form throws TypeError on submission",
  "description": "Clicking 'Place Order' triggers JavaScript error: 'TypeError: Cannot read property submit of undefined at handleSubmit'. Form does not submit, blocking all purchases.",
  "evidence": {
    "page_url": "/checkout",
    "dom_selector": "form#checkout-form button[type=submit]",
    "console_errors": ["TypeError: Cannot read property 'submit' of undefined at handleSubmit (checkout.js:45)"]
  },
  "recommendation": {
    "human_readable": "The checkout button is broken - customers cannot buy from you. The form reference is null when the submit handler runs.",
    "ai_actionable": "Add null check before form submission. If tech stack is Next.js/React: ensure form ref is initialized before event handler attachment."
  }
}
```
👆 **ACCEPT THIS** - Grounded in actual console error

**WHEN THERE ARE NO ISSUES:**
```json
{
  "findings": []
}
```
👆 **This is perfectly valid** - Don't fabricate issues

## Self-Review Checklist

Before finalizing, verify EVERY finding:

- [ ] Does evidence.console_errors contain the EXACT error message quoted in description?
- [ ] Does evidence.network_evidence cite a SPECIFIC failed request from broken_links?
- [ ] Does evidence.page_url match an ACTUAL page from recon data?
- [ ] Can you point to the EXACT line in recon data that proves this issue?
- [ ] If answer is "no" to any → DELETE THE FINDING

**When in doubt, delete the finding. False negatives (missing real issues) are better than false positives (hallucinated issues).**
