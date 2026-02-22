const API_BASE = `${import.meta.env.VITE_API_URL ?? ''}/api`

export interface ScanCreateRequest {
  url: string
  user_brief?: string
  tech_stack?: string
  test_route?: string
  api_key: string
  llm_provider: string
  auth_username?: string
  auth_password?: string
}

export interface ScanResult {
  id: string
  status: string
  url: string
  verdict?: string
  overall_score?: number
  overall_grade?: string
  lens_scores?: Record<string, { score: number; grade: string; summary: string }>
  findings_count?: Record<string, number>
  top_3_actions?: string[]
  duration_seconds?: number
  created_at: string
  completed_at?: string
  report_a_available: boolean
  report_b_available: boolean
  parent_scan_id?: string
}

export interface ProgressEvent {
  step: string
  message: string
  percent: number
}

export async function createScan(data: ScanCreateRequest): Promise<{ id: string; status: string }> {
  const response = await fetch(`${API_BASE}/scans`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })

  if (!response.ok) {
    throw new Error('Failed to create scan')
  }

  return response.json()
}

export async function getScan(scanId: string): Promise<ScanResult> {
  const response = await fetch(`${API_BASE}/scans/${scanId}`)

  if (!response.ok) {
    throw new Error('Failed to fetch scan')
  }

  return response.json()
}

export async function listScans(limit = 20, offset = 0): Promise<{ scans: ScanResult[] }> {
  const response = await fetch(`${API_BASE}/scans?limit=${limit}&offset=${offset}`)

  if (!response.ok) {
    throw new Error('Failed to fetch scans')
  }

  return response.json()
}

export function subscribeToProgress(
  scanId: string,
  onProgress: (event: ProgressEvent) => void,
  onComplete: (data: { verdict: string; overall_score: number }) => void,
  onError: (message: string) => void
): () => void {
  const eventSource = new EventSource(`${API_BASE}/scans/${scanId}/stream`)

  eventSource.addEventListener('progress', (e) => {
    const data = JSON.parse(e.data)
    onProgress(data)
  })

  eventSource.addEventListener('complete', (e) => {
    const data = JSON.parse(e.data)
    onComplete(data)
    eventSource.close()
  })

  eventSource.addEventListener('error', (e) => {
    if (e instanceof MessageEvent) {
      const data = JSON.parse(e.data)
      onError(data.message)
    }
    eventSource.close()
  })

  eventSource.onerror = () => {
    eventSource.close()
  }

  return () => eventSource.close()
}

export function getReportUrl(scanId: string, reportType: 'a' | 'b'): string {
  return `${API_BASE}/scans/${scanId}/reports/${reportType}`
}

// Fix Loop Interfaces
export interface FixLoopStartRequest {
  scan_id: string
  severity_filter: string[]
  strategy: 'branch' | 'direct'
  branch_name?: string
  max_cycles?: number
  stop_on_verdict?: string
  deploy_command?: string
  deploy_strategy?: 'preview' | 'manual' | 'local'
  api_key: string
  llm_provider: string
}

export interface FixCycleInfo {
  cycle_number: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  started_at?: string
  completed_at?: string
  claude_code_session_id?: string
  claude_code_cost_usd?: number
  claude_code_turns_used?: number
  files_modified?: number
  findings_fixed?: number
  findings_introduced?: number
  findings_unchanged?: number
  verdict_after?: string
  score_after?: number
}

export interface FixLoopStartResponse {
  loop_id: string
  scan_id: string
  status: string
  strategy: string
  branch_name?: string
  created_at: string
}

export interface FixLoopStatusResponse {
  loop_id: string
  scan_id: string
  status: 'running' | 'paused' | 'completed' | 'failed' | 'stopped'
  current_cycle: number
  max_cycles: number
  severity_filter: string[]
  strategy: 'branch' | 'direct'
  branch_name?: string
  cycles: FixCycleInfo[]
  total_cost_usd: number
  total_files_modified: number
  total_findings_fixed: number
  created_at: string
  updated_at: string
}

export interface PrerequisiteCheckResponse {
  ready: boolean
  checks: {
    has_git_repo: boolean
    has_clean_working_tree?: boolean
    has_deploy_command?: boolean
    has_scan_report: boolean
    scan_verdict?: string
  }
  warnings?: string[]
  errors?: string[]
}

export interface DiffResponse {
  loop_id: string
  branch_name?: string
  files_changed: {
    path: string
    additions: number
    deletions: number
    status: 'modified' | 'added' | 'deleted'
  }[]
  total_additions: number
  total_deletions: number
  diff_url?: string
}

export interface StopResponse {
  loop_id: string
  status: string
  message: string
}

export interface FixLoopEvent {
  type: 'cycle_start' | 'progress' | 'cycle_complete' | 'complete' | 'error' | 'stopped'
  cycle?: number
  message: string
  data?: {
    files_modified?: number
    cost_usd?: number
    verdict?: string
    score?: number
    findings_fixed?: number
    findings_introduced?: number
  }
}

// Fix Loop API Functions
export async function checkFixLoopPrerequisites(scanId: string): Promise<PrerequisiteCheckResponse> {
  const response = await fetch(`${API_BASE}/scans/${scanId}/fix-loop/prerequisites`)

  if (!response.ok) {
    throw new Error('Failed to check fix loop prerequisites')
  }

  return response.json()
}

export async function startFixLoop(data: FixLoopStartRequest): Promise<FixLoopStartResponse> {
  const response = await fetch(`${API_BASE}/scans/${data.scan_id}/fix-loop`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })

  if (!response.ok) {
    throw new Error('Failed to start fix loop')
  }

  return response.json()
}

export async function getFixLoopStatus(scanId: string, loopId: string): Promise<FixLoopStatusResponse> {
  const response = await fetch(`${API_BASE}/scans/${scanId}/fix-loop/${loopId}`)

  if (!response.ok) {
    throw new Error('Failed to fetch fix loop status')
  }

  return response.json()
}

export async function advanceFixLoop(scanId: string, loopId: string): Promise<{ status: string; cycle: number }> {
  const response = await fetch(`${API_BASE}/scans/${scanId}/fix-loop/${loopId}/advance`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  })

  if (!response.ok) {
    throw new Error('Failed to advance fix loop')
  }

  return response.json()
}

export async function getFixDiff(scanId: string, loopId: string): Promise<DiffResponse> {
  const response = await fetch(`${API_BASE}/scans/${scanId}/fix-loop/${loopId}/diff`)

  if (!response.ok) {
    throw new Error('Failed to fetch fix diff')
  }

  return response.json()
}

export async function stopFixLoop(scanId: string, loopId: string): Promise<StopResponse> {
  const response = await fetch(`${API_BASE}/scans/${scanId}/fix-loop/${loopId}/stop`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  })

  if (!response.ok) {
    throw new Error('Failed to stop fix loop')
  }

  return response.json()
}

export function streamFixLoopProgress(
  scanId: string,
  loopId: string,
  onEvent: (event: FixLoopEvent) => void,
  onComplete: (data: FixLoopStatusResponse) => void,
  onError: (message: string) => void
): () => void {
  const eventSource = new EventSource(`${API_BASE}/scans/${scanId}/fix-loop/${loopId}/stream`)

  eventSource.addEventListener('cycle_start', (e) => {
    const data = JSON.parse(e.data)
    onEvent(data)
  })

  eventSource.addEventListener('progress', (e) => {
    const data = JSON.parse(e.data)
    onEvent(data)
  })

  eventSource.addEventListener('cycle_complete', (e) => {
    const data = JSON.parse(e.data)
    onEvent(data)
  })

  eventSource.addEventListener('complete', (e) => {
    const data = JSON.parse(e.data)
    onComplete(data)
    eventSource.close()
  })

  eventSource.addEventListener('stopped', (e) => {
    const data = JSON.parse(e.data)
    onEvent(data)
    eventSource.close()
  })

  eventSource.addEventListener('error', (e) => {
    if (e instanceof MessageEvent) {
      const data = JSON.parse(e.data)
      onError(data.message)
    }
    eventSource.close()
  })

  eventSource.onerror = () => {
    eventSource.close()
  }

  return () => eventSource.close()
}
