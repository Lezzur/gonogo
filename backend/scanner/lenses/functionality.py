from typing import List
from schemas import ReconData, IntentAnalysis, TechStack, Finding, Evidence, Recommendation
from llm.client import LLMClient
from llm.prompt_loader import load_prompt


def generate_chat_findings(recon_data: ReconData) -> List[Finding]:
    """Generate findings for chat interaction issues."""
    findings = []

    for page in recon_data.pages:
        chat = page.chat_interaction
        if not chat:
            continue

        if chat.detected:
            # Chat detected but couldn't open
            if not chat.could_open and chat.widget_type != "iframe":
                findings.append(Finding(
                    id=f"CHAT-001-{page.url[-20:]}",
                    lens="functionality",
                    severity="high",
                    effort="moderate",
                    confidence=0.9,
                    title="Chat widget failed to open",
                    description=f"A chat widget was detected on {page.url} but could not be opened when clicked. Users will be unable to access chat support.",
                    evidence=Evidence(
                        page_url=page.url,
                        dom_selector=chat.selector,
                        console_errors=chat.console_errors_during_test[:5] if chat.console_errors_during_test else None,
                        raw_data={"error": chat.error}
                    ),
                    recommendation=Recommendation(
                        human_readable="Verify the chat widget is properly initialized and the click handler is working.",
                        ai_actionable=f"Check the chat widget at selector '{chat.selector}'. Ensure JavaScript event handlers are attached and the widget library is loaded correctly."
                    )
                ))

            # Chat opened but couldn't send message
            elif chat.could_open and not chat.could_send_message:
                findings.append(Finding(
                    id=f"CHAT-002-{page.url[-20:]}",
                    lens="functionality",
                    severity="high",
                    effort="moderate",
                    confidence=0.85,
                    title="Chat input field not found or not functional",
                    description=f"The chat widget on {page.url} opened but no input field could be found or interacted with.",
                    evidence=Evidence(
                        page_url=page.url,
                        dom_selector=chat.selector,
                        screenshot_ref=chat.screenshot_open,
                        console_errors=chat.console_errors_during_test[:5] if chat.console_errors_during_test else None,
                        raw_data={"error": chat.error}
                    ),
                    recommendation=Recommendation(
                        human_readable="Ensure the chat input field is visible and accessible after opening the widget.",
                        ai_actionable="Check that the chat input textarea or input field is rendered and not hidden. Verify focus handling."
                    )
                ))

            # Message sent but no response
            elif chat.could_send_message and not chat.got_response:
                findings.append(Finding(
                    id=f"CHAT-003-{page.url[-20:]}",
                    lens="functionality",
                    severity="critical",
                    effort="significant",
                    confidence=0.95,
                    title="AI/Chat assistant not responding",
                    description=f"A test message was sent to the chat on {page.url} but no response was received within 10 seconds. The chat functionality appears to be broken.",
                    evidence=Evidence(
                        page_url=page.url,
                        dom_selector=chat.selector,
                        screenshot_ref=chat.screenshot_open,
                        console_errors=chat.console_errors_during_test[:5] if chat.console_errors_during_test else None,
                        raw_data={"error": chat.error, "widget_type": chat.widget_type}
                    ),
                    recommendation=Recommendation(
                        human_readable="The chat/AI assistant is not responding to messages. Check the backend API, websocket connection, or AI service integration.",
                        ai_actionable="Investigate the chat backend: check API endpoints, websocket connections, AI service (OpenAI, Anthropic, etc.) configuration, and error logs. The issue may be in the chat route handler or AI client initialization."
                    )
                ))

            # Console errors during chat interaction
            if chat.console_errors_during_test and len(chat.console_errors_during_test) > 0:
                error_msgs = chat.console_errors_during_test[:3]
                findings.append(Finding(
                    id=f"CHAT-004-{page.url[-20:]}",
                    lens="functionality",
                    severity="medium",
                    effort="moderate",
                    confidence=0.8,
                    title="JavaScript errors during chat interaction",
                    description=f"Console errors occurred while testing the chat widget on {page.url}: {'; '.join(error_msgs[:2])}",
                    evidence=Evidence(
                        page_url=page.url,
                        dom_selector=chat.selector,
                        console_errors=error_msgs,
                        raw_data={"all_errors": chat.console_errors_during_test}
                    ),
                    recommendation=Recommendation(
                        human_readable="Fix the JavaScript errors that occur during chat interaction.",
                        ai_actionable=f"Debug the following console errors: {error_msgs}"
                    )
                ))

    return findings


def generate_form_test_findings(recon_data: ReconData) -> List[Finding]:
    """Generate findings from form input testing."""
    findings = []

    for page in recon_data.pages:
        for form_test in page.form_test_results:
            # Check for inputs that showed errors with valid data
            for test_result in form_test.test_results:
                # Valid input rejected
                if test_result.test_type.startswith("valid") and test_result.visual_feedback == "error":
                    findings.append(Finding(
                        id=f"FORM-001-{test_result.selector[-15:]}",
                        lens="functionality",
                        severity="high",
                        effort="moderate",
                        confidence=0.9,
                        title=f"Form validation rejects valid {test_result.input_type} input",
                        description=f"The input field '{test_result.label or test_result.selector}' on {page.url} shows an error state when valid test data ('{test_result.test_value}') is entered. This may prevent users from submitting the form.",
                        evidence=Evidence(
                            page_url=page.url,
                            dom_selector=test_result.selector,
                            screenshot_ref=form_test.screenshot_filled,
                            raw_data={
                                "test_value": test_result.test_value,
                                "test_type": test_result.test_type,
                                "validation_message": test_result.validation_message,
                                "visual_feedback": test_result.visual_feedback
                            }
                        ),
                        recommendation=Recommendation(
                            human_readable=f"Review the validation logic for this {test_result.input_type} field. The current validation may be too strict.",
                            ai_actionable=f"Check the validation regex/logic for input '{test_result.selector}'. Test value '{test_result.test_value}' should be accepted."
                        )
                    ))

                # Console errors during input
                if test_result.console_errors:
                    findings.append(Finding(
                        id=f"FORM-002-{test_result.selector[-15:]}",
                        lens="functionality",
                        severity="medium",
                        effort="moderate",
                        confidence=0.85,
                        title=f"JavaScript errors when typing in {test_result.input_type} field",
                        description=f"Console errors occurred while typing into '{test_result.label or test_result.selector}' on {page.url}: {test_result.console_errors[0][:100]}",
                        evidence=Evidence(
                            page_url=page.url,
                            dom_selector=test_result.selector,
                            console_errors=test_result.console_errors[:3],
                            raw_data={"input_type": test_result.input_type}
                        ),
                        recommendation=Recommendation(
                            human_readable="Fix JavaScript errors that occur during form input.",
                            ai_actionable=f"Debug errors in input handler for '{test_result.selector}': {test_result.console_errors[0][:200]}"
                        )
                    ))

            # Check for overall form console errors
            if form_test.console_errors_during_test and len(form_test.console_errors_during_test) > 2:
                findings.append(Finding(
                    id=f"FORM-003-{form_test.form_selector[-15:]}",
                    lens="functionality",
                    severity="medium",
                    effort="moderate",
                    confidence=0.8,
                    title="Multiple JavaScript errors during form interaction",
                    description=f"Multiple console errors ({len(form_test.console_errors_during_test)}) occurred while testing the form at '{form_test.form_selector}' on {page.url}.",
                    evidence=Evidence(
                        page_url=page.url,
                        dom_selector=form_test.form_selector,
                        console_errors=form_test.console_errors_during_test[:5],
                        screenshot_ref=form_test.screenshot_filled
                    ),
                    recommendation=Recommendation(
                        human_readable="Multiple JavaScript errors indicate potential issues with form handling.",
                        ai_actionable=f"Review form event handlers and validation logic for {form_test.form_selector}"
                    )
                ))

    return findings


async def evaluate_functionality(
    recon_data: ReconData,
    intent: IntentAnalysis,
    tech_stack: TechStack,
    api_key: str,
    llm_provider: str = "gemini"
) -> List[Finding]:
    """Step 3: Evaluate functionality - JS errors, broken links, forms, chat, etc."""

    client = LLMClient(api_key, llm_provider)

    # Generate chat interaction findings first (no LLM needed)
    chat_findings = generate_chat_findings(recon_data)
    print(f"🗨️ Chat interaction check: {len(chat_findings)} findings")

    # Generate form test findings (no LLM needed)
    form_findings = generate_form_test_findings(recon_data)
    print(f"📝 Form input test check: {len(form_findings)} findings")

    # Gather evidence
    console_errors = []
    for page in recon_data.pages:
        for log in page.console_logs:
            if log.get("level") == "error":
                console_errors.append({
                    "page": page.url,
                    "message": log.get("message", "")
                })

    broken_links = [
        link.model_dump() for link in recon_data.links_audit
        if link.status_code >= 400 or link.status_code == 0
    ]

    forms = []
    for page in recon_data.pages:
        for form in page.form_elements:
            forms.append({
                "page": page.url,
                "form": form
            })

    # Gather form test results
    form_test_data = []
    for page in recon_data.pages:
        for form_test in page.form_test_results:
            form_test_data.append({
                "page": page.url,
                "form_selector": form_test.form_selector,
                "inputs_tested": form_test.inputs_tested,
                "inputs_with_validation": form_test.inputs_with_validation,
                "inputs_with_errors": form_test.inputs_with_errors,
                "test_results": [
                    {
                        "selector": r.selector,
                        "input_type": r.input_type,
                        "test_type": r.test_type,
                        "validation_message": r.validation_message,
                        "visual_feedback": r.visual_feedback
                    }
                    for r in form_test.test_results
                ]
            })

    interactive_elements = []
    for page in recon_data.pages:
        interactive_elements.extend([
            {"page": page.url, **el}
            for el in page.interactive_elements[:20]
        ])

    broken_images = []
    for page in recon_data.pages:
        for img in page.images:
            if not img.get("loaded"):
                broken_images.append({
                    "page": page.url,
                    "src": img.get("src"),
                    "alt": img.get("alt")
                })

    prompt = load_prompt(
        "functionality_lens",
        intent_analysis=intent.model_dump(),
        tech_stack=tech_stack.model_dump(),
        console_errors=console_errors[:50],
        broken_links=broken_links[:50],
        forms=forms[:20],
        form_test_results=form_test_data[:10],
        interactive_elements=interactive_elements[:50],
        broken_images=broken_images[:20]
    )

    result = await client.generate(prompt, model_tier="flash")

    print(f"🔍 Functionality lens LLM returned: {len(result.get('findings', []))} findings")

    findings = []
    for f in result.get("findings", []):
        try:
            findings.append(Finding(**f))
        except Exception as e:
            print(f"⚠️  Failed to parse finding: {e}")
            continue

    # Combine all findings
    all_findings = chat_findings + form_findings + findings
    print(f"✅ Functionality lens: {len(chat_findings)} chat + {len(form_findings)} form + {len(findings)} LLM = {len(all_findings)} total findings")
    return all_findings
