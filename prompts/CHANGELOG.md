# Prompt Changelog

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
