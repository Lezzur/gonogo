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

    # Combine LLM findings with chat interaction findings
    all_findings = chat_findings + findings
    print(f"✅ Functionality lens: {len(chat_findings)} chat + {len(findings)} LLM = {len(all_findings)} total findings")
    return all_findings
