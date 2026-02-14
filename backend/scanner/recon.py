import asyncio
import json
import re
from datetime import datetime
from typing import Optional, Dict, List, Any
from urllib.parse import urljoin, urlparse
from pathlib import Path

from playwright.async_api import async_playwright, Page, Browser
from config import SCREENSHOTS_DIR, MAX_DEEP_PAGES, MAX_SHALLOW_PAGES, MAX_SCAN_DURATION_SECONDS
from schemas import ReconData, PageData, LinkAudit


# Page type patterns
PAGE_TYPE_PATTERNS = {
    "homepage": [r"^/$", r"^/home$", r"^/index"],
    "listing": [r"/products?$", r"/items$", r"/catalog", r"/browse", r"/search", r"/list"],
    "detail": [r"/products?/[\w-]+$", r"/items?/[\w-]+$", r"/post/", r"/article/"],
    "form": [r"/contact", r"/signup", r"/register", r"/login", r"/checkout"],
    "settings": [r"/settings", r"/profile", r"/account", r"/preferences"],
    "dashboard": [r"/dashboard", r"/admin", r"/panel"],
    "about": [r"/about", r"/team", r"/company"],
    "legal": [r"/privacy", r"/terms", r"/legal", r"/policy"],
}


def classify_page_type(url: str) -> str:
    """Classify a URL into a page type category."""
    path = urlparse(url).path.lower()

    for page_type, patterns in PAGE_TYPE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, path):
                return page_type

    return "other"


async def capture_page_data(
    page: Page,
    url: str,
    scan_id: str,
    test_depth: str = "deep"
) -> PageData:
    """Capture comprehensive data from a single page."""
    screenshots_path = SCREENSHOTS_DIR / scan_id
    screenshots_path.mkdir(parents=True, exist_ok=True)

    # Get page title
    title = await page.title()
    page_type = classify_page_type(url)

    # Generate filename-safe URL slug
    url_slug = re.sub(r'[^\w\-]', '_', urlparse(url).path or "home")[:50]

    page_data = PageData(
        url=url,
        page_type=page_type,
        test_depth=test_depth,
        title=title
    )

    if test_depth == "deep":
        # Desktop screenshot
        desktop_path = screenshots_path / f"{url_slug}_desktop.png"
        await page.set_viewport_size({"width": 1280, "height": 800})
        await page.screenshot(path=str(desktop_path), full_page=True)
        page_data.screenshot_desktop = str(desktop_path)

        # Mobile screenshot
        mobile_path = screenshots_path / f"{url_slug}_mobile.png"
        await page.set_viewport_size({"width": 375, "height": 667})
        await page.screenshot(path=str(mobile_path), full_page=True)
        page_data.screenshot_mobile = str(mobile_path)

        # Reset viewport
        await page.set_viewport_size({"width": 1280, "height": 800})

        # DOM snapshot
        page_data.dom_snapshot = await page.content()

        # Capture interactive elements
        page_data.interactive_elements = await page.evaluate("""
            () => {
                const elements = [];
                document.querySelectorAll('button, a, input, select, textarea, [onclick], [role="button"]').forEach(el => {
                    elements.push({
                        tag: el.tagName.toLowerCase(),
                        selector: el.id ? '#' + el.id : (el.className ? '.' + el.className.split(' ')[0] : el.tagName.toLowerCase()),
                        type: el.type || null,
                        text: el.textContent?.slice(0, 100) || '',
                        href: el.href || null
                    });
                });
                return elements.slice(0, 100);
            }
        """)

        # Capture form elements
        page_data.form_elements = await page.evaluate("""
            () => {
                const forms = [];
                document.querySelectorAll('form').forEach(form => {
                    const inputs = [];
                    form.querySelectorAll('input, select, textarea').forEach(input => {
                        inputs.push({
                            selector: input.id ? '#' + input.id : input.name,
                            type: input.type || 'text',
                            label: input.labels?.[0]?.textContent || '',
                            required: input.required,
                            placeholder: input.placeholder || ''
                        });
                    });
                    forms.push({
                        action: form.action,
                        method: form.method,
                        inputs: inputs
                    });
                });
                return forms;
            }
        """)

        # Capture images
        page_data.images = await page.evaluate("""
            () => {
                const images = [];
                document.querySelectorAll('img').forEach(img => {
                    images.push({
                        src: img.src,
                        alt: img.alt || '',
                        width: img.naturalWidth,
                        height: img.naturalHeight,
                        loaded: img.complete && img.naturalHeight > 0
                    });
                });
                return images.slice(0, 50);
            }
        """)

    elif test_depth == "spot_check":
        # Just desktop screenshot
        desktop_path = screenshots_path / f"{url_slug}_desktop.png"
        await page.set_viewport_size({"width": 1280, "height": 800})
        await page.screenshot(path=str(desktop_path), full_page=True)
        page_data.screenshot_desktop = str(desktop_path)

    return page_data


async def run_lighthouse(url: str, scan_id: str) -> Dict[str, Any]:
    """Run Lighthouse CLI and return parsed results."""
    import os
    output_path = SCREENSHOTS_DIR / scan_id / "lighthouse.json"

    try:
        # Set UTF-8 environment for subprocess
        env = os.environ.copy()
        env['PYTHONUTF8'] = '1'

        process = await asyncio.create_subprocess_exec(
            "lighthouse", url,
            "--output=json",
            f"--output-path={output_path}",
            "--chrome-flags=--headless --no-sandbox",
            "--only-categories=performance,accessibility,best-practices,seo",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )

        await asyncio.wait_for(process.communicate(), timeout=120)

        if output_path.exists():
            with open(output_path, encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Lighthouse failed: {e}")

    return {}


async def run_axe_core(page: Page) -> Dict[str, Any]:
    """Inject axe-core and run accessibility audit."""
    try:
        # Inject axe-core
        await page.add_script_tag(url="https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.2/axe.min.js")
        await asyncio.sleep(0.5)

        # Run audit
        results = await page.evaluate("() => axe.run()")
        return results
    except Exception as e:
        print(f"axe-core failed: {e}")
        return {}


async def discover_links(page: Page, base_url: str) -> List[Dict[str, Any]]:
    """Discover all links on the page."""
    base_domain = urlparse(base_url).netloc

    links = await page.evaluate("""
        () => {
            const links = [];
            document.querySelectorAll('a[href]').forEach(a => {
                links.push({
                    href: a.href,
                    text: a.textContent?.trim().slice(0, 100) || ''
                });
            });
            return links;
        }
    """)

    result = []
    for link in links:
        href = link.get("href", "")
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue

        parsed = urlparse(href)
        is_internal = parsed.netloc == base_domain or not parsed.netloc

        result.append({
            "url": href,
            "anchor_text": link.get("text", ""),
            "is_internal": is_internal
        })

    return result


async def run_reconnaissance(
    url: str,
    scan_id: str,
    test_route: Optional[str] = None,
    auth_credentials: Optional[Dict[str, str]] = None
) -> ReconData:
    """Main reconnaissance function - crawls site and gathers all data."""
    start_time = datetime.utcnow()
    base_domain = urlparse(url).netloc

    recon_data = ReconData(
        url=url,
        crawled_at=start_time
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        # Capture console logs
        console_logs = []

        page = await context.new_page()
        page.on("console", lambda msg: console_logs.append({
            "level": msg.type,
            "message": msg.text,
            "location": str(msg.location) if msg.location else None
        }))

        # Track network requests
        network_requests = []
        failed_requests = []

        async def handle_request(request):
            network_requests.append({
                "url": request.url,
                "method": request.method,
                "resource_type": request.resource_type
            })

        async def handle_response(response):
            if response.status >= 400:
                failed_requests.append({
                    "url": response.url,
                    "status": response.status
                })

        page.on("request", handle_request)
        page.on("response", handle_response)

        try:
            # Navigate to main URL first
            await page.goto(url, wait_until="networkidle", timeout=30000)
            initial_url = page.url

            # Handle authentication if credentials provided
            if auth_credentials and (auth_credentials.get("username") or auth_credentials.get("password")):
                try:
                    print(f"🔐 Attempting login with provided credentials...")

                    # Check if we're already on a login page
                    current_url = page.url.lower()
                    on_login_page = any(path in current_url for path in ['/login', '/signin', '/sign-in', '/auth'])

                    # If not on login page, try common login URLs
                    if not on_login_page:
                        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                        login_paths = ['/login', '/signin', '/sign-in', '/auth/login']

                        for path in login_paths:
                            try:
                                login_url = f"{base_url}{path}"
                                print(f"  Trying login page: {login_url}")
                                response = await page.goto(login_url, wait_until="networkidle", timeout=10000)
                                if response and response.status < 400:
                                    print(f"  ✓ Found login page at {path}")
                                    break
                            except Exception:
                                continue
                        else:
                            print(f"  ⚠️  Could not find login page, trying to authenticate on current page...")

                    # Wait a bit for form to render
                    await page.wait_for_timeout(1000)

                    # Try to find email/username input with better selectors
                    username_input = await page.query_selector(
                        'input[type="email"], input[type="text"], input[name*="email" i], '
                        'input[name*="username" i], input[id*="email" i], input[id*="username" i], '
                        'input[placeholder*="email" i], input[placeholder*="username" i]'
                    )
                    if username_input:
                        await username_input.fill(auth_credentials.get("username", ""))
                        print(f"  ✓ Filled username/email field")
                    else:
                        print(f"  ⚠️  Could not find username/email input field")

                    # Try to find password input
                    password_input = await page.query_selector('input[type="password"]')
                    if password_input:
                        await password_input.fill(auth_credentials.get("password", ""))
                        print(f"  ✓ Filled password field")
                    else:
                        print(f"  ⚠️  Could not find password input field")

                    # Try to find and click submit button (case-insensitive, multiple patterns)
                    submit_button = await page.query_selector(
                        'button[type="submit"], input[type="submit"], '
                        'button:has-text("Log in"), button:has-text("log in"), button:has-text("LOGIN"), '
                        'button:has-text("Sign in"), button:has-text("sign in"), button:has-text("SIGN IN"), '
                        'button:has-text("Submit"), button:has-text("submit"), '
                        'button[class*="submit" i], button[class*="login" i]'
                    )

                    if submit_button:
                        # Store current URL to detect redirect
                        pre_submit_url = page.url
                        await submit_button.click()
                        print(f"  ✓ Clicked submit button")

                        # Wait for navigation or network idle
                        try:
                            await page.wait_for_load_state("networkidle", timeout=15000)
                        except Exception:
                            await page.wait_for_timeout(3000)

                        # Verify login success
                        post_submit_url = page.url
                        if post_submit_url != pre_submit_url:
                            print(f"  ✅ Login successful - redirected from {pre_submit_url} to {post_submit_url}")
                        else:
                            # Check for error messages
                            error_element = await page.query_selector('[class*="error" i], [class*="alert" i], [role="alert"]')
                            if error_element:
                                error_text = await error_element.inner_text()
                                print(f"  ❌ Login failed - error message: {error_text[:100]}")
                            else:
                                # Check if we're still on login page
                                if any(path in page.url.lower() for path in ['/login', '/signin', '/sign-in', '/auth']):
                                    print(f"  ⚠️  Still on login page after submit - login may have failed")
                                else:
                                    print(f"  ✅ Login appears successful (no redirect but no error)")
                    else:
                        print(f"  ⚠️  Could not find submit button")

                except Exception as e:
                    print(f"  ❌ Login attempt failed with exception: {e}")
                    print(f"  Continuing scan anyway...")

            # Extract meta tags
            recon_data.meta_tags = await page.evaluate("""
                () => {
                    const meta = {};
                    document.querySelectorAll('meta').forEach(m => {
                        const name = m.getAttribute('name') || m.getAttribute('property');
                        if (name) meta[name] = m.getAttribute('content');
                    });
                    return meta;
                }
            """)

            # Extract OG tags
            recon_data.og_tags = await page.evaluate("""
                () => {
                    const og = {};
                    document.querySelectorAll('meta[property^="og:"]').forEach(m => {
                        og[m.getAttribute('property')] = m.getAttribute('content');
                    });
                    return og;
                }
            """)

            # Detect framework signatures
            recon_data.framework_signatures = await page.evaluate("""
                () => {
                    const signatures = {};
                    if (window.__NEXT_DATA__) signatures.nextjs = true;
                    if (window.__NUXT__) signatures.nuxt = true;
                    if (document.querySelector('[data-reactroot]')) signatures.react = true;
                    if (document.querySelector('[ng-app], [ng-controller]')) signatures.angular = true;
                    if (document.querySelector('[data-v-]')) signatures.vue = true;
                    if (document.querySelector('.wp-content')) signatures.wordpress = true;
                    if (document.querySelector('script[src*="shopify"]')) signatures.shopify = true;

                    // Check for common libraries
                    document.querySelectorAll('script[src]').forEach(s => {
                        const src = s.src.toLowerCase();
                        if (src.includes('tailwind')) signatures.tailwind = true;
                        if (src.includes('bootstrap')) signatures.bootstrap = true;
                        if (src.includes('jquery')) signatures.jquery = true;
                        if (src.includes('stripe')) signatures.stripe = true;
                    });

                    return signatures;
                }
            """)

            # Discover all links
            discovered_links = await discover_links(page, url)
            internal_urls = set([url])

            for link in discovered_links:
                if link["is_internal"]:
                    full_url = urljoin(url, link["url"])
                    internal_urls.add(full_url)

            # Categorize pages by type
            page_type_map: Dict[str, List[str]] = {}
            for page_url in internal_urls:
                ptype = classify_page_type(page_url)
                if ptype not in page_type_map:
                    page_type_map[ptype] = []
                page_type_map[ptype].append(page_url)

            recon_data.page_type_map = page_type_map
            recon_data.total_pages_found = len(internal_urls)

            # Deep test one representative per page type
            deep_tested = 0
            shallow_crawled = 0

            for page_type, urls in page_type_map.items():
                if deep_tested >= MAX_DEEP_PAGES:
                    break

                # Deep test first representative
                rep_url = urls[0]
                try:
                    await page.goto(rep_url, wait_until="networkidle", timeout=30000)
                    page_data = await capture_page_data(page, rep_url, scan_id, "deep")
                    page_data.console_logs = [log for log in console_logs if log["level"] in ("error", "warning")]
                    recon_data.pages.append(page_data)
                    deep_tested += 1
                except Exception as e:
                    print(f"Failed to deep test {rep_url}: {e}")

                # Spot check additional pages
                for spot_url in urls[1:4]:
                    if deep_tested >= MAX_DEEP_PAGES:
                        break
                    try:
                        await page.goto(spot_url, wait_until="networkidle", timeout=15000)
                        page_data = await capture_page_data(page, spot_url, scan_id, "spot_check")
                        recon_data.pages.append(page_data)
                        deep_tested += 1
                    except Exception as e:
                        print(f"Failed to spot check {spot_url}: {e}")

            # Shallow crawl remaining
            for page_url in list(internal_urls)[:MAX_SHALLOW_PAGES]:
                if shallow_crawled >= MAX_SHALLOW_PAGES:
                    break
                if any(p.url == page_url for p in recon_data.pages):
                    continue

                try:
                    response = await page.goto(page_url, wait_until="domcontentloaded", timeout=10000)
                    status = response.status if response else 0

                    recon_data.links_audit.append(LinkAudit(
                        url=page_url,
                        source_page=url,
                        status_code=status,
                        is_internal=True,
                        anchor_text=""
                    ))
                    shallow_crawled += 1
                except Exception:
                    recon_data.links_audit.append(LinkAudit(
                        url=page_url,
                        source_page=url,
                        status_code=0,
                        is_internal=True,
                        anchor_text=""
                    ))
                    shallow_crawled += 1

            recon_data.pages_deep_tested = deep_tested
            recon_data.pages_shallow_crawled = shallow_crawled

            # Run Lighthouse on homepage
            recon_data.lighthouse_report = await run_lighthouse(url, scan_id)

            # Run axe-core on homepage
            await page.goto(url, wait_until="networkidle", timeout=30000)
            recon_data.axe_report = await run_axe_core(page)

        finally:
            await browser.close()

        recon_data.scan_duration_seconds = (datetime.utcnow() - start_time).total_seconds()

        return recon_data
