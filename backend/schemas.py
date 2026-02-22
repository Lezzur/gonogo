from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# Request schemas
class ScanCreateRequest(BaseModel):
    url: str
    user_brief: Optional[str] = None
    tech_stack: Optional[str] = None
    test_route: Optional[str] = None
    api_key: str
    llm_provider: str = "gemini"
    auth_username: Optional[str] = None
    auth_password: Optional[str] = None
    auth_token: Optional[str] = None
    # Fix loop fields
    fix_loop_enabled: bool = False
    max_cycles: int = 3
    stop_on_verdict: str = "GO"  # "GO", "GO_WITH_CONDITIONS", "never"
    deploy_mode: str = "branch"  # "branch", "manual", "local"
    deploy_command: Optional[str] = None
    severity_filter: Optional[List[str]] = None  # e.g. ["critical", "high"]
    apply_mode: str = "branch"  # "branch" or "direct"
    repo_path: Optional[str] = None


# Response schemas
class ScanCreateResponse(BaseModel):
    id: str
    status: str


class ScanStatusResponse(BaseModel):
    id: str
    status: str
    current_step: Optional[str] = None
    progress_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None


class ScanResultResponse(BaseModel):
    id: str
    status: str
    url: str
    verdict: Optional[str] = None
    overall_score: Optional[int] = None
    overall_grade: Optional[str] = None
    lens_scores: Optional[Dict[str, Any]] = None
    findings_count: Optional[Dict[str, int]] = None
    top_3_actions: Optional[List[str]] = None
    duration_seconds: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    report_a_available: bool = False
    report_b_available: bool = False
    error_message: Optional[str] = None
    warnings: Optional[List[str]] = None
    # Fix loop fields
    parent_scan_id: Optional[str] = None
    current_cycle: Optional[int] = None
    fix_branch: Optional[str] = None

    class Config:
        from_attributes = True


class ScanListResponse(BaseModel):
    scans: List[ScanResultResponse]


# Fix Loop schemas
class FixCycleResponse(BaseModel):
    id: str
    scan_id: str
    cycle_number: int
    rescan_id: Optional[str] = None
    status: str  # pending, fixing, deploying, rescanning, completed, failed
    claude_code_output: Optional[str] = None
    claude_code_cost_usd: Optional[float] = None
    claude_code_duration_seconds: Optional[float] = None
    files_modified: Optional[List[str]] = None
    findings_resolved: int = 0
    findings_new: int = 0
    findings_unchanged: int = 0
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class FixLoopStartRequest(BaseModel):
    repo_path: str
    apply_mode: str = "branch"  # "branch" or "direct"
    deploy_mode: str = "branch"  # "branch", "manual", "local"
    deploy_command: Optional[str] = None
    max_cycles: int = 3
    stop_on_verdict: str = "GO"  # "GO", "GO_WITH_CONDITIONS", "never"
    severity_filter: Optional[List[str]] = None  # e.g. ["critical", "high"]


class FixLoopStatusResponse(BaseModel):
    current_cycle: int
    total_cycles: int
    status: str
    cycles: List[FixCycleResponse] = []
    fix_branch: Optional[str] = None


# Finding schemas (used in pipeline)
class Evidence(BaseModel):
    page_url: Optional[str] = "/"  # Default to root if not specified
    screenshot_ref: Optional[str] = None
    dom_selector: Optional[str] = None
    console_errors: Optional[List[str]] = None
    network_evidence: Optional[str] = None
    lighthouse_metric: Optional[str] = None
    axe_violation: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None


class Recommendation(BaseModel):
    human_readable: Optional[str] = ""
    ai_actionable: Optional[str] = ""


class Finding(BaseModel):
    id: str
    lens: str
    severity: str  # critical | high | medium | low
    effort: str    # quick_fix | moderate | significant
    confidence: float = Field(ge=0.0, le=1.0)
    title: str
    description: str
    evidence: Evidence
    recommendation: Recommendation


# Recon data schemas
class LinkAudit(BaseModel):
    url: str
    source_page: str
    status_code: int
    is_internal: bool
    anchor_text: str


class ChatInteraction(BaseModel):
    detected: bool = False
    widget_type: Optional[str] = None  # e.g., "floating", "embedded", "modal"
    selector: Optional[str] = None
    could_open: bool = False
    could_send_message: bool = False
    got_response: bool = False
    response_time_ms: Optional[int] = None
    error: Optional[str] = None
    console_errors_during_test: List[str] = []
    screenshot_open: Optional[str] = None


class InputTestResult(BaseModel):
    selector: str
    input_type: str  # text, email, password, textarea, etc.
    label: Optional[str] = None
    placeholder: Optional[str] = None
    test_value: str
    test_type: str  # valid, invalid_email, empty_required, special_chars, long_text
    accepted_input: bool = True
    validation_message: Optional[str] = None
    visual_feedback: Optional[str] = None  # error, success, warning, none
    console_errors: List[str] = []
    screenshot_after: Optional[str] = None


class FormTestResults(BaseModel):
    form_selector: str
    page_url: str
    inputs_tested: int = 0
    inputs_with_validation: int = 0
    inputs_with_errors: int = 0
    test_results: List[InputTestResult] = []
    screenshot_filled: Optional[str] = None
    console_errors_during_test: List[str] = []


# Security data schemas
class SSLInfo(BaseModel):
    valid: bool = False
    issuer: Optional[str] = None
    subject: Optional[str] = None
    not_after: Optional[str] = None
    days_until_expiry: Optional[int] = None
    protocol: Optional[str] = None  # TLSv1.2, TLSv1.3
    error: Optional[str] = None


class SecurityHeaders(BaseModel):
    content_security_policy: Optional[str] = None
    strict_transport_security: Optional[str] = None
    x_frame_options: Optional[str] = None
    x_content_type_options: Optional[str] = None
    referrer_policy: Optional[str] = None
    permissions_policy: Optional[str] = None
    server: Optional[str] = None  # Info leakage
    x_powered_by: Optional[str] = None


class CookieInfo(BaseModel):
    name: str
    secure: bool = False
    http_only: bool = False
    same_site: Optional[str] = None


class SecurityData(BaseModel):
    ssl_info: Optional[SSLInfo] = None
    security_headers: Optional[SecurityHeaders] = None
    cookies: List[CookieInfo] = []
    mixed_content: List[Dict[str, Any]] = []
    subresource_integrity_missing: List[str] = []


class PageData(BaseModel):
    url: str
    page_type: str
    test_depth: str
    title: str
    screenshot_desktop: Optional[str] = None
    screenshot_mobile: Optional[str] = None
    dom_snapshot: Optional[str] = None
    console_logs: List[Dict[str, Any]] = []
    network_requests: List[Dict[str, Any]] = []
    failed_requests: List[Dict[str, Any]] = []
    interactive_elements: List[Dict[str, Any]] = []
    form_elements: List[Dict[str, Any]] = []
    images: List[Dict[str, Any]] = []
    computed_styles: Dict[str, Any] = {}
    chat_interaction: Optional[ChatInteraction] = None
    form_test_results: List[FormTestResults] = []


class ReconData(BaseModel):
    url: str
    crawled_at: datetime
    pages: List[PageData] = []
    site_map: Dict[str, Any] = {}
    page_type_map: Dict[str, List[str]] = {}
    lighthouse_report: Dict[str, Any] = {}
    axe_report: Dict[str, Any] = {}
    meta_tags: Dict[str, str] = {}
    og_tags: Dict[str, str] = {}
    framework_signatures: Dict[str, Any] = {}
    links_audit: List[LinkAudit] = []
    total_pages_found: int = 0
    pages_deep_tested: int = 0
    pages_shallow_crawled: int = 0
    scan_duration_seconds: float = 0.0
    security_data: Optional[SecurityData] = None
    auth_wall_detected: bool = False


# Intent analysis output
class TargetAudience(BaseModel):
    description: str
    technical_sophistication: str
    expected_familiarity: str


class IntentAnalysis(BaseModel):
    project_type: str
    primary_purpose: str
    target_audience: TargetAudience
    key_user_journeys: List[str] = []
    success_criteria: List[str] = []
    intent_vs_execution_gaps: List[str] = []
    confidence: float = Field(ge=0.0, le=1.0)


# Tech stack output
class TechStack(BaseModel):
    framework: Optional[str] = None
    ui_library: Optional[str] = None
    language: Optional[str] = None
    hosting_signals: Optional[str] = None
    cms: Optional[str] = None
    notable_libraries: List[str] = []
    confidence: float = Field(ge=0.0, le=1.0)
    user_provided_stack: Optional[str] = None
    discrepancies: List[str] = []


# Synthesis output
class LensScore(BaseModel):
    score: int = Field(ge=0, le=100)
    grade: str
    summary: str


class SynthesisResult(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    overall_grade: str
    verdict: str  # GO | NO-GO | GO_WITH_CONDITIONS
    verdict_reasoning: str
    lens_scores: Dict[str, LensScore] = {}
    findings_count: Dict[str, int] = {}
    top_3_actions: List[str] = []
    deduplicated_findings: List[Finding] = []
    systemic_patterns: List[str] = []


# SSE Progress event
class ProgressEvent(BaseModel):
    step: str
    message: str
    percent: int = Field(ge=0, le=100)
