from typing import List
from schemas import ReconData, IntentAnalysis, TechStack, Finding, Evidence, Recommendation
from llm.client import LLMClient
from llm.prompt_loader import load_prompt


def generate_ssl_findings(recon_data: ReconData) -> List[Finding]:
    """Generate findings for SSL/TLS issues."""
    findings = []
    security_data = recon_data.security_data

    if not security_data or not security_data.ssl_info:
        return findings

    ssl = security_data.ssl_info

    if not ssl.valid:
        findings.append(Finding(
            id="SEC-SSL-001",
            lens="security",
            severity="critical",
            effort="moderate",
            confidence=0.95,
            title="SSL/TLS certificate invalid or missing",
            description=f"The site's SSL certificate is invalid or not configured. Error: {ssl.error or 'Unknown'}. Users will see browser security warnings, and sensitive data transmitted is at risk.",
            evidence=Evidence(
                page_url=recon_data.url,
                raw_data={"error": ssl.error}
            ),
            recommendation=Recommendation(
                human_readable="Install a valid SSL certificate. Consider using Let's Encrypt for free certificates.",
                ai_actionable="Configure SSL/TLS certificate. For most hosting providers, enable HTTPS in dashboard. For self-hosted: use certbot with Let's Encrypt."
            )
        ))

    if ssl.valid and ssl.days_until_expiry is not None:
        if ssl.days_until_expiry <= 0:
            findings.append(Finding(
                id="SEC-SSL-002",
                lens="security",
                severity="critical",
                effort="quick_fix",
                confidence=1.0,
                title="SSL certificate has expired",
                description=f"The SSL certificate expired {abs(ssl.days_until_expiry)} days ago. Browsers will block access to the site.",
                evidence=Evidence(
                    page_url=recon_data.url,
                    raw_data={"not_after": ssl.not_after, "days_until_expiry": ssl.days_until_expiry}
                ),
                recommendation=Recommendation(
                    human_readable="Renew your SSL certificate immediately.",
                    ai_actionable="Run `certbot renew` or renew through your SSL provider/hosting dashboard."
                )
            ))
        elif ssl.days_until_expiry <= 14:
            findings.append(Finding(
                id="SEC-SSL-003",
                lens="security",
                severity="high",
                effort="quick_fix",
                confidence=1.0,
                title="SSL certificate expiring soon",
                description=f"The SSL certificate expires in {ssl.days_until_expiry} days (on {ssl.not_after}). Renew before it expires to avoid site access issues.",
                evidence=Evidence(
                    page_url=recon_data.url,
                    raw_data={"not_after": ssl.not_after, "days_until_expiry": ssl.days_until_expiry}
                ),
                recommendation=Recommendation(
                    human_readable="Renew your SSL certificate before expiry.",
                    ai_actionable="Set up automatic certificate renewal with certbot or your hosting provider."
                )
            ))
        elif ssl.days_until_expiry <= 30:
            findings.append(Finding(
                id="SEC-SSL-004",
                lens="security",
                severity="medium",
                effort="quick_fix",
                confidence=1.0,
                title="SSL certificate expiring within 30 days",
                description=f"The SSL certificate expires in {ssl.days_until_expiry} days. Plan for renewal.",
                evidence=Evidence(
                    page_url=recon_data.url,
                    raw_data={"not_after": ssl.not_after, "days_until_expiry": ssl.days_until_expiry}
                ),
                recommendation=Recommendation(
                    human_readable="Schedule SSL certificate renewal.",
                    ai_actionable="Consider enabling auto-renewal to prevent future expiry issues."
                )
            ))

    if ssl.protocol and ssl.protocol in ("TLSv1", "TLSv1.0", "TLSv1.1"):
        findings.append(Finding(
            id="SEC-SSL-005",
            lens="security",
            severity="high",
            effort="moderate",
            confidence=0.95,
            title=f"Outdated TLS protocol version: {ssl.protocol}",
            description=f"The server is using {ssl.protocol}, which is deprecated and has known vulnerabilities. Modern browsers may refuse connections.",
            evidence=Evidence(
                page_url=recon_data.url,
                raw_data={"protocol": ssl.protocol}
            ),
            recommendation=Recommendation(
                human_readable="Upgrade to TLS 1.2 or TLS 1.3.",
                ai_actionable="Update server SSL/TLS configuration to disable TLSv1.0 and TLSv1.1. Enable only TLSv1.2 and TLSv1.3."
            )
        ))

    return findings


def generate_header_findings(recon_data: ReconData) -> List[Finding]:
    """Generate findings for missing security headers."""
    findings = []
    security_data = recon_data.security_data

    if not security_data or not security_data.security_headers:
        return findings

    headers = security_data.security_headers

    if not headers.strict_transport_security:
        findings.append(Finding(
            id="SEC-HDR-001",
            lens="security",
            severity="medium",
            effort="quick_fix",
            confidence=0.9,
            title="Missing Strict-Transport-Security (HSTS) header",
            description="The site does not enforce HTTPS via HSTS. Users could be vulnerable to protocol downgrade attacks.",
            evidence=Evidence(
                page_url=recon_data.url,
                raw_data={"header": "Strict-Transport-Security", "value": None}
            ),
            recommendation=Recommendation(
                human_readable="Add the Strict-Transport-Security header to enforce HTTPS.",
                ai_actionable="Add header: Strict-Transport-Security: max-age=31536000; includeSubDomains"
            )
        ))

    if not headers.content_security_policy:
        findings.append(Finding(
            id="SEC-HDR-002",
            lens="security",
            severity="medium",
            effort="moderate",
            confidence=0.85,
            title="Missing Content-Security-Policy (CSP) header",
            description="No CSP is configured. This increases risk of XSS attacks by allowing any scripts to execute.",
            evidence=Evidence(
                page_url=recon_data.url,
                raw_data={"header": "Content-Security-Policy", "value": None}
            ),
            recommendation=Recommendation(
                human_readable="Implement a Content-Security-Policy to control allowed content sources.",
                ai_actionable="Start with a report-only CSP to identify violations: Content-Security-Policy-Report-Only: default-src 'self'"
            )
        ))

    if not headers.x_frame_options:
        findings.append(Finding(
            id="SEC-HDR-003",
            lens="security",
            severity="medium",
            effort="quick_fix",
            confidence=0.9,
            title="Missing X-Frame-Options header",
            description="The site can be embedded in iframes, making it vulnerable to clickjacking attacks.",
            evidence=Evidence(
                page_url=recon_data.url,
                raw_data={"header": "X-Frame-Options", "value": None}
            ),
            recommendation=Recommendation(
                human_readable="Add X-Frame-Options header to prevent clickjacking.",
                ai_actionable="Add header: X-Frame-Options: DENY (or SAMEORIGIN if embedding is needed)"
            )
        ))

    if not headers.x_content_type_options:
        findings.append(Finding(
            id="SEC-HDR-004",
            lens="security",
            severity="low",
            effort="quick_fix",
            confidence=0.9,
            title="Missing X-Content-Type-Options header",
            description="Without this header, browsers may MIME-sniff responses, potentially treating files as executable.",
            evidence=Evidence(
                page_url=recon_data.url,
                raw_data={"header": "X-Content-Type-Options", "value": None}
            ),
            recommendation=Recommendation(
                human_readable="Add X-Content-Type-Options header to prevent MIME sniffing.",
                ai_actionable="Add header: X-Content-Type-Options: nosniff"
            )
        ))

    if not headers.referrer_policy:
        findings.append(Finding(
            id="SEC-HDR-005",
            lens="security",
            severity="low",
            effort="quick_fix",
            confidence=0.85,
            title="Missing Referrer-Policy header",
            description="No referrer policy is set. Sensitive URL paths may leak to external sites via the Referer header.",
            evidence=Evidence(
                page_url=recon_data.url,
                raw_data={"header": "Referrer-Policy", "value": None}
            ),
            recommendation=Recommendation(
                human_readable="Set a Referrer-Policy to control what information is sent in the Referer header.",
                ai_actionable="Add header: Referrer-Policy: strict-origin-when-cross-origin"
            )
        ))

    # Info leakage headers
    if headers.server:
        findings.append(Finding(
            id="SEC-HDR-006",
            lens="security",
            severity="low",
            effort="quick_fix",
            confidence=0.8,
            title=f"Server header reveals technology: {headers.server}",
            description="The Server header discloses server software information that could help attackers target known vulnerabilities.",
            evidence=Evidence(
                page_url=recon_data.url,
                raw_data={"header": "Server", "value": headers.server}
            ),
            recommendation=Recommendation(
                human_readable="Remove or obfuscate the Server header to reduce information disclosure.",
                ai_actionable="Configure your web server to not send the Server header or set it to a generic value."
            )
        ))

    if headers.x_powered_by:
        findings.append(Finding(
            id="SEC-HDR-007",
            lens="security",
            severity="low",
            effort="quick_fix",
            confidence=0.8,
            title=f"X-Powered-By header reveals technology: {headers.x_powered_by}",
            description="The X-Powered-By header discloses framework/runtime information that attackers could use to target specific vulnerabilities.",
            evidence=Evidence(
                page_url=recon_data.url,
                raw_data={"header": "X-Powered-By", "value": headers.x_powered_by}
            ),
            recommendation=Recommendation(
                human_readable="Remove the X-Powered-By header to hide technology stack details.",
                ai_actionable="For Express.js: app.disable('x-powered-by'). For other frameworks, check server configuration."
            )
        ))

    return findings


def generate_cookie_findings(recon_data: ReconData) -> List[Finding]:
    """Generate findings for insecure cookies."""
    findings = []
    security_data = recon_data.security_data

    if not security_data or not security_data.cookies:
        return findings

    insecure_cookies = []
    no_httponly = []
    no_samesite = []

    for cookie in security_data.cookies:
        # Skip tracking/analytics cookies
        if any(skip in cookie.name.lower() for skip in ["_ga", "_gid", "_gat", "fbp", "_fbp"]):
            continue

        if not cookie.secure:
            insecure_cookies.append(cookie.name)
        if not cookie.http_only:
            no_httponly.append(cookie.name)
        if not cookie.same_site or cookie.same_site.lower() == "none":
            no_samesite.append(cookie.name)

    if insecure_cookies:
        findings.append(Finding(
            id="SEC-COOKIE-001",
            lens="security",
            severity="medium",
            effort="quick_fix",
            confidence=0.9,
            title=f"Cookies without Secure flag: {', '.join(insecure_cookies[:3])}{'...' if len(insecure_cookies) > 3 else ''}",
            description=f"{len(insecure_cookies)} cookie(s) are not marked Secure, allowing transmission over unencrypted HTTP.",
            evidence=Evidence(
                page_url=recon_data.url,
                raw_data={"cookies": insecure_cookies}
            ),
            recommendation=Recommendation(
                human_readable="Set the Secure flag on all cookies to ensure they're only sent over HTTPS.",
                ai_actionable="Set cookie with Secure flag: Set-Cookie: name=value; Secure; HttpOnly; SameSite=Strict"
            )
        ))

    # Only report HttpOnly for session-like cookies
    session_cookies_no_httponly = [c for c in no_httponly if any(s in c.lower() for s in ["session", "auth", "token", "sb-"])]
    if session_cookies_no_httponly:
        findings.append(Finding(
            id="SEC-COOKIE-002",
            lens="security",
            severity="high",
            effort="quick_fix",
            confidence=0.9,
            title=f"Session cookies without HttpOnly flag: {', '.join(session_cookies_no_httponly[:3])}",
            description=f"Session/auth cookies are accessible to JavaScript. If XSS exists, attackers can steal these cookies.",
            evidence=Evidence(
                page_url=recon_data.url,
                raw_data={"cookies": session_cookies_no_httponly}
            ),
            recommendation=Recommendation(
                human_readable="Set HttpOnly flag on session and authentication cookies.",
                ai_actionable="Set cookie with HttpOnly flag: Set-Cookie: session=value; HttpOnly; Secure; SameSite=Strict"
            )
        ))

    # Only report SameSite for auth-related cookies
    auth_cookies_no_samesite = [c for c in no_samesite if any(s in c.lower() for s in ["session", "auth", "token", "csrf", "sb-"])]
    if auth_cookies_no_samesite:
        findings.append(Finding(
            id="SEC-COOKIE-003",
            lens="security",
            severity="medium",
            effort="quick_fix",
            confidence=0.85,
            title=f"Auth cookies without SameSite attribute: {', '.join(auth_cookies_no_samesite[:3])}",
            description="Authentication cookies lack SameSite attribute, potentially enabling CSRF attacks.",
            evidence=Evidence(
                page_url=recon_data.url,
                raw_data={"cookies": auth_cookies_no_samesite}
            ),
            recommendation=Recommendation(
                human_readable="Set SameSite=Strict or SameSite=Lax on authentication cookies.",
                ai_actionable="Set cookie with SameSite: Set-Cookie: auth=value; SameSite=Strict; Secure; HttpOnly"
            )
        ))

    return findings


def generate_mixed_content_findings(recon_data: ReconData) -> List[Finding]:
    """Generate findings for mixed content issues."""
    findings = []
    security_data = recon_data.security_data

    if not security_data or not security_data.mixed_content:
        return findings

    mixed = security_data.mixed_content

    # Group by type
    scripts = [m for m in mixed if m.get("type") == "script"]
    other = [m for m in mixed if m.get("type") != "script"]

    if scripts:
        findings.append(Finding(
            id="SEC-MIXED-001",
            lens="security",
            severity="critical",
            effort="moderate",
            confidence=0.95,
            title=f"Mixed content: {len(scripts)} HTTP script(s) loaded on HTTPS page",
            description="Scripts are loaded over HTTP on an HTTPS page. Browsers block this (active mixed content) and it's a major security risk.",
            evidence=Evidence(
                page_url=recon_data.url,
                raw_data={"scripts": [s.get("url") for s in scripts[:5]]}
            ),
            recommendation=Recommendation(
                human_readable="Update all script sources to use HTTPS.",
                ai_actionable=f"Change script src from http:// to https:// for: {scripts[0].get('url')}"
            )
        ))

    if other:
        findings.append(Finding(
            id="SEC-MIXED-002",
            lens="security",
            severity="medium",
            effort="quick_fix",
            confidence=0.9,
            title=f"Mixed content: {len(other)} HTTP resource(s) on HTTPS page",
            description="Images, stylesheets, or iframes are loaded over HTTP. This causes browser warnings and degrades security.",
            evidence=Evidence(
                page_url=recon_data.url,
                raw_data={"resources": [m.get("url") for m in other[:5]]}
            ),
            recommendation=Recommendation(
                human_readable="Update all resource URLs to use HTTPS.",
                ai_actionable="Change resource URLs from http:// to https://"
            )
        ))

    return findings


def generate_sri_findings(recon_data: ReconData) -> List[Finding]:
    """Generate findings for missing Subresource Integrity."""
    findings = []
    security_data = recon_data.security_data

    if not security_data or not security_data.subresource_integrity_missing:
        return findings

    sri_missing = security_data.subresource_integrity_missing

    # Only flag CDN scripts (common ones that should have SRI)
    cdn_patterns = ["cdn", "unpkg", "jsdelivr", "cloudflare", "bootstrapcdn", "jquery"]
    flagged = [s for s in sri_missing if any(p in s.lower() for p in cdn_patterns)]

    if flagged:
        findings.append(Finding(
            id="SEC-SRI-001",
            lens="security",
            severity="low",
            effort="quick_fix",
            confidence=0.8,
            title=f"CDN scripts without Subresource Integrity: {len(flagged)} found",
            description="External scripts from CDNs are loaded without integrity hashes. If the CDN is compromised, malicious code could execute.",
            evidence=Evidence(
                page_url=recon_data.url,
                raw_data={"scripts": flagged[:5]}
            ),
            recommendation=Recommendation(
                human_readable="Add integrity and crossorigin attributes to external script tags.",
                ai_actionable=f'<script src="{flagged[0]}" integrity="sha384-..." crossorigin="anonymous"></script>'
            )
        ))

    return findings


async def evaluate_security(
    recon_data: ReconData,
    intent: IntentAnalysis,
    tech_stack: TechStack,
    api_key: str,
    llm_provider: str = "gemini"
) -> List[Finding]:
    """Step 7: Evaluate security - SSL, headers, cookies, CVEs, OWASP patterns."""

    # Deterministic checks (no LLM)
    ssl_findings = generate_ssl_findings(recon_data)
    header_findings = generate_header_findings(recon_data)
    cookie_findings = generate_cookie_findings(recon_data)
    mixed_findings = generate_mixed_content_findings(recon_data)
    sri_findings = generate_sri_findings(recon_data)

    deterministic_findings = ssl_findings + header_findings + cookie_findings + mixed_findings + sri_findings
    print(f"🔒 Security deterministic checks: {len(deterministic_findings)} findings")

    # LLM analysis for CVEs and OWASP patterns
    client = LLMClient(api_key, llm_provider)

    # Gather data for LLM analysis
    libraries = tech_stack.notable_libraries if tech_stack else []
    framework = tech_stack.framework if tech_stack else None

    # Get DOM content for XSS pattern analysis (limit size)
    dom_samples = []
    for page in recon_data.pages[:3]:
        if page.dom_snapshot:
            dom_samples.append({
                "url": page.url,
                "snippet": page.dom_snapshot[:5000]  # Limit to 5K chars
            })

    prompt = load_prompt(
        "security_lens",
        intent_analysis=intent.model_dump() if intent else {},
        tech_stack=tech_stack.model_dump() if tech_stack else {},
        libraries=libraries,
        framework=framework,
        dom_samples=dom_samples
    )

    result = await client.generate(prompt, model_tier="flash")

    print(f"🔍 Security lens LLM returned: {len(result.get('findings', []))} findings")

    llm_findings = []
    for f in result.get("findings", []):
        try:
            llm_findings.append(Finding(**f))
        except Exception as e:
            print(f"⚠️  Failed to parse finding: {e}")
            continue

    all_findings = deterministic_findings + llm_findings
    print(f"✅ Security lens: {len(deterministic_findings)} deterministic + {len(llm_findings)} LLM = {len(all_findings)} total")
    return all_findings
