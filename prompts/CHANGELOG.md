# Prompt Changelog

## v2.3 — Severity Calibration in Synthesis (2026-02-14)

**Problem:** Console errors were being marked CRITICAL even when functionality worked.
Example: "TypeError: Failed to fetch" during login was CRITICAL despite successful authentication.

**Root cause:** Synthesis prompt (v1) didn't consider whether errors were actually blocking.
Rule was simply "any critical finding = NO-GO" without verifying actual impact.

**Changes:**

1. Created `synthesis_v2.md` with severity re-evaluation logic:
   - Downgrade to LOW if console error exists BUT functionality works
   - Only CRITICAL if user CANNOT complete primary task
   - Pass auth_status to synthesis so it knows if login succeeded

2. Updated orchestrator to track auth status:
   - "auth_successful" if agent accessed authenticated pages
   - "auth_attempted_unclear" if unclear
   - "no_auth_required" if no credentials provided

3. Updated synthesize_findings() to accept auth_status parameter

**Expected behavior:**
- Auth error + successful login → LOW severity (error handled)
- Auth error + failed login → CRITICAL severity (actually blocked)
- Verdict NO-GO only for ACTUALLY blocking issues

---

## v2.2 — Complete Anti-Hallucination Overhaul (2026-02-14)

**Problem:** Report still contained 5/7 hallucinated findings despite v2 prompts. Investigation revealed:
1. Only 3 of 6 evaluation lenses were updated to v2
2. Performance, accessibility, and code_content lenses were still v1 (hallucinating)
3. Report generation prompt was telling LLM to "guess file paths based on tech stack"

**Evidence of hallucination:**
- "Hero image causing slow LCP" → NO hero image exists on site
- "/about page has invalid nesting" → /about returns 404
- "/blog images missing sizes" → /blog returns 404
- "Newsletter form at /#contact" → No contact section exists

**Changes in v2.2:**

Created v2 prompts for remaining lenses:
- `performance_lens_v2.md` - Only report metrics from actual Lighthouse data
- `accessibility_lens_v2.md` - Only report violations from actual axe-core data
- `code_content_lens_v2.md` - Only report issues visible in recon data (meta tags, console logs)

Updated report generation:
- `report_a_generation_v1.md` - Added rule: DO NOT INVENT FILE PATHS

**Key constraints added:**
- Performance: "If no hero image in image_issues, DO NOT report hero image issues"
- Accessibility: "If axe-core has zero violations, return empty findings array"
- Code/Content: "If /about not in pages_scanned, DO NOT report /about issues"
- Reports: "Only include file hints if they were in original evidence"

**All 6 evaluation lenses now have v2 prompts with evidence-only constraints.**

---

## v2.1 — Severity Calibration Update (2026-02-14)

**Problem:** v2 functionality lens was reporting ALL console errors as critical, even when functionality still worked. Example: "TypeError: Failed to fetch" during login was marked CRITICAL even though user could successfully log in (error was handled/recovered).

**Changes in v2.1:**

Updated `functionality_lens_v2.md`:
- Added nuance to console error evaluation - presence of error ≠ automatic critical severity
- Severity now based on **actual functionality impact**, not just error existence
- Added rule: Check if feature works despite error before assigning severity
- Updated severity guide with examples distinguishing handled vs blocking errors

**Example:**
- ❌ v2.0: "TypeError during login" + error in console → CRITICAL (incorrect)
- ✅ v2.1: "TypeError during login" BUT agent authenticated successfully → LOW (error handled)

---

## v2 — Anti-Hallucination Update (2026-02-14)

**Problem:** v1 prompts allowed the LLM too much creative freedom. Agent was generating plausible-sounding but fabricated findings - inventing console errors, guessing file paths, and reporting common framework issues without evidence.

**Example hallucinations from v1:**
- "Form submission canceled because the form is not connected" (console error never captured)
- "File hint: src/components/Hero.tsx" (file structure never accessed)
- "Ratio detected: 3.1:1" (measurement never performed)

**Root cause:** Prompts used aspirational rubrics ("Does the form work?") without enforcing that findings MUST be grounded in actual recon data.

**Changes in v2:**

1. **Added CRITICAL RULE section** - Explicit prohibition of inference/assumption/guessing
2. **Evidence-only mandates** - "No evidence = no finding" principle enforced
3. **Negative examples** - Showed what happens when there's no evidence (empty findings array)
4. **Stricter self-review** - Checklist requires pointing to exact evidence in recon data
5. **Empty array validation** - Made it clear that `{"findings": []}` is a GOOD outcome

**Updated prompts:**
- `functionality_lens_v2.md` - Only report observed console errors, network failures, broken images
- `design_lens_v2.md` - Only report what's visible in screenshots
- `ux_lens_v2.md` - Only report observable layout/navigation issues from screenshots

**Migration plan:** Update scanner to use v2 prompts. v1 remains for regression testing.

---

## v1 — Initial Release

All prompts created for GoNoGo V1:

- `intent_analysis_v1.md` - Project intent understanding
- `tech_stack_detection_v1.md` - Framework/library detection
- `functionality_lens_v1.md` - Functional QA evaluation
- `design_lens_v1.md` - Visual design evaluation
- `ux_lens_v1.md` - User experience evaluation
- `performance_lens_v1.md` - Performance metrics evaluation
- `accessibility_lens_v1.md` - WCAG compliance evaluation
- `code_content_lens_v1.md` - Code quality and content evaluation
- `synthesis_v1.md` - Finding synthesis and scoring
- `report_a_generation_v1.md` - AI handoff report
- `report_b_generation_v1.md` - Human review report

### Design Principles

1. **Structured output**: All prompts request JSON (except reports)
2. **Rubric-driven**: Specific criteria, not vague asks
3. **Evidence-required**: Every finding must reference evidence
4. **Dual recommendations**: Both human_readable and ai_actionable
5. **Calibration examples**: Good vs bad finding examples
6. **Self-review**: Prompts instruct model to validate output

### Prompt Engineering Notes

- Lens prompts use personas for consistent perspective
- Finding schema is universal across all lenses
- Severity and effort classifications are standardized
- Screenshot handling varies by lens (design/ux get images, perf/a11y don't)
