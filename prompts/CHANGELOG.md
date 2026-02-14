# Prompt Changelog

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
