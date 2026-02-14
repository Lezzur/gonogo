const API_BASE = '/api'

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
