import { useEffect, useState } from 'react'
import { streamFixLoopProgress, getFixLoopStatus, stopFixLoop, advanceFixLoop, getFixDiff, FixLoopEvent, FixLoopStatusResponse, FixCycleInfo, DiffResponse } from '../api/client'

interface FixLoopProgressProps {
  scanId: string
  loopId: string
  onComplete: () => void
}

export default function FixLoopProgress({ scanId, loopId, onComplete }: FixLoopProgressProps) {
  const [status, setStatus] = useState<FixLoopStatusResponse | null>(null)
  const [currentMessage, setCurrentMessage] = useState('Initializing fix loop...')
  const [error, setError] = useState('')
  const [completionReason, setCompletionReason] = useState<string>('')
  const [expandedCycles, setExpandedCycles] = useState<Set<number>>(new Set())
  const [diff, setDiff] = useState<DiffResponse | null>(null)
  const [loadingDiff, setLoadingDiff] = useState(false)
  const [stopping, setStopping] = useState(false)
  const [deployUrl, setDeployUrl] = useState('')
  const [submittingDeploy, setSubmittingDeploy] = useState(false)
  const [startTime] = useState(Date.now())

  useEffect(() => {
    // Initial status fetch
    getFixLoopStatus(scanId, loopId)
      .then(setStatus)
      .catch(err => setError(err.message))

    // Subscribe to SSE stream
    const unsubscribe = streamFixLoopProgress(
      scanId,
      loopId,
      (event: FixLoopEvent) => {
        setCurrentMessage(event.message)

        if (event.type === 'cycle_complete') {
          // Refresh full status to get updated cycle info
          getFixLoopStatus(scanId, loopId).then(setStatus)
        }
      },
      (finalStatus: FixLoopStatusResponse) => {
        setStatus(finalStatus)

        // Determine completion reason
        if (finalStatus.status === 'completed') {
          const lastCycle = finalStatus.cycles[finalStatus.cycles.length - 1]
          if (lastCycle?.verdict_after === 'GO') {
            setCompletionReason('verdict_reached')
          } else if (finalStatus.current_cycle >= finalStatus.max_cycles) {
            setCompletionReason('max_cycles')
          }
        } else if (finalStatus.status === 'stopped') {
          setCompletionReason('user_stopped')
        } else if (finalStatus.status === 'failed') {
          setCompletionReason('error')
        }

        onComplete()
      },
      (errorMessage: string) => {
        setError(errorMessage)
        setCompletionReason('error')
      }
    )

    return unsubscribe
  }, [scanId, loopId, onComplete])

  const toggleCycleExpanded = (cycleNumber: number) => {
    setExpandedCycles(prev => {
      const next = new Set(prev)
      if (next.has(cycleNumber)) {
        next.delete(cycleNumber)
      } else {
        next.add(cycleNumber)
      }
      return next
    })
  }

  const handleViewDiff = async () => {
    if (loadingDiff || diff) return

    setLoadingDiff(true)
    try {
      const diffData = await getFixDiff(scanId, loopId)
      setDiff(diffData)
    } catch (err) {
      console.error('Failed to load diff:', err)
    } finally {
      setLoadingDiff(false)
    }
  }

  const handleStop = async () => {
    if (!confirm('Stop the fix loop after the current cycle completes?')) return

    setStopping(true)
    try {
      await stopFixLoop(scanId, loopId)
      setCurrentMessage('Stopping after current cycle...')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop fix loop')
    } finally {
      setStopping(false)
    }
  }

  const handleDeploySubmit = async () => {
    if (!deployUrl.trim()) {
      alert('Please enter the deploy URL')
      return
    }

    setSubmittingDeploy(true)
    try {
      await advanceFixLoop(scanId, loopId)
      setDeployUrl('')
      setCurrentMessage('Rescanning deployed site...')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to continue fix loop')
    } finally {
      setSubmittingDeploy(false)
    }
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-red-800 mb-2">Fix Loop Failed</h3>
        <p className="text-red-700">{error}</p>
      </div>
    )
  }

  if (!status) {
    return (
      <div className="text-center py-12">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 mb-4">
          <svg className="w-8 h-8 text-gray-600 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        </div>
        <p className="text-gray-600">Loading fix loop status...</p>
      </div>
    )
  }

  const isRunning = status.status === 'running'
  const isComplete = ['completed', 'stopped', 'failed'].includes(status.status)
  const elapsedSeconds = Math.floor((Date.now() - startTime) / 1000)
  const elapsedMinutes = Math.floor(elapsedSeconds / 60)
  const elapsedRemainder = elapsedSeconds % 60

  // Calculate totals
  const originalVerdict = status.cycles[0]?.verdict_after || 'N/A'
  const originalScore = status.cycles[0]?.score_after || 0
  const currentVerdict = status.cycles.length > 0
    ? status.cycles[status.cycles.length - 1]?.verdict_after || 'N/A'
    : 'N/A'
  const currentScore = status.cycles.length > 0
    ? status.cycles[status.cycles.length - 1]?.score_after || 0
    : 0

  // Check if awaiting manual deploy
  const awaitingDeploy = status.status === 'paused' && currentMessage.includes('awaiting_deploy_url')

  return (
    <div className="space-y-6">
      {/* Live Status */}
      <div className="text-center">
        {isRunning && (
          <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-green-100 mb-4 animate-pulse">
            <svg className="w-12 h-12 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
        )}
        {isComplete && (
          <div className={`inline-flex items-center justify-center w-24 h-24 rounded-full mb-4 ${
            completionReason === 'verdict_reached' ? 'bg-green-100' :
            completionReason === 'error' ? 'bg-red-100' : 'bg-gray-100'
          }`}>
            <svg className={`w-12 h-12 ${
              completionReason === 'verdict_reached' ? 'text-green-600' :
              completionReason === 'error' ? 'text-red-600' : 'text-gray-600'
            }`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              {completionReason === 'verdict_reached' ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              ) : completionReason === 'error' ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              )}
            </svg>
          </div>
        )}
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          {isRunning ? `Cycle ${status.current_cycle}/${status.max_cycles}` : 'Fix Loop Complete'}
        </h2>
        <p className="text-lg text-gray-600">{currentMessage}</p>
      </div>

      {/* Cycle Progress Bar */}
      <div className="flex justify-center items-center gap-3">
        {Array.from({ length: status.max_cycles }, (_, i) => {
          const cycleNum = i + 1
          const cycle = status.cycles.find(c => c.cycle_number === cycleNum)
          const isActive = cycleNum === status.current_cycle && isRunning
          const isCompleted = cycle?.status === 'completed'
          const isFailed = cycle?.status === 'failed'

          return (
            <div key={cycleNum} className="flex flex-col items-center gap-1">
              <div className={`w-12 h-12 rounded-full flex items-center justify-center font-semibold text-sm ${
                isActive ? 'bg-green-600 text-white ring-4 ring-green-200' :
                isCompleted ? 'bg-green-600 text-white' :
                isFailed ? 'bg-red-600 text-white' :
                'bg-gray-300 text-gray-600'
              }`}>
                {cycleNum}
              </div>
              <span className="text-xs text-gray-500">
                {isCompleted ? '✓' : isFailed ? '✗' : isActive ? '...' : ''}
              </span>
            </div>
          )
        })}
      </div>

      {/* Manual Deploy Prompt */}
      {awaitingDeploy && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <h3 className="font-semibold text-yellow-800 mb-2">Manual Deploy Required</h3>
          <p className="text-sm text-yellow-700 mb-3">
            Please deploy the fixes and provide the URL to continue the rescan.
          </p>
          <div className="flex gap-2">
            <input
              type="url"
              value={deployUrl}
              onChange={(e) => setDeployUrl(e.target.value)}
              placeholder="https://your-preview-url.com"
              className="flex-1 px-3 py-2 border border-yellow-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500"
              disabled={submittingDeploy}
            />
            <button
              onClick={handleDeploySubmit}
              disabled={submittingDeploy || !deployUrl.trim()}
              className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submittingDeploy ? 'Continuing...' : 'Continue'}
            </button>
          </div>
        </div>
      )}

      {/* Running Totals */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-sm text-gray-600 mb-1">Findings Fixed</div>
          <div className="text-2xl font-bold text-green-600">{status.total_findings_fixed}</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-sm text-gray-600 mb-1">Total Cost</div>
          <div className="text-2xl font-bold text-gray-900">${status.total_cost_usd.toFixed(2)}</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-sm text-gray-600 mb-1">Elapsed Time</div>
          <div className="text-2xl font-bold text-gray-900">{elapsedMinutes}m {elapsedRemainder}s</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="text-sm text-gray-600 mb-1">Files Modified</div>
          <div className="text-2xl font-bold text-gray-900">{status.total_files_modified}</div>
        </div>
      </div>

      {/* Verdict/Score Progress */}
      <div className="bg-gray-50 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm text-gray-600">Verdict Progress</div>
            <div className="text-lg font-semibold text-gray-900">
              {originalVerdict} → {currentVerdict}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-600 text-right">Score Progress</div>
            <div className="text-lg font-semibold text-gray-900">
              {originalScore} → {currentScore}
              {currentScore > originalScore && (
                <span className="text-green-600 ml-2">+{currentScore - originalScore}</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Cycle History Cards */}
      <div className="space-y-3">
        <h3 className="text-lg font-semibold text-gray-900">Cycle History</h3>
        {status.cycles.map((cycle: FixCycleInfo) => (
          <div
            key={cycle.cycle_number}
            className="bg-white border border-gray-200 rounded-lg overflow-hidden"
          >
            <button
              onClick={() => toggleCycleExpanded(cycle.cycle_number)}
              className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50"
            >
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${
                  cycle.status === 'completed' ? 'bg-green-600 text-white' :
                  cycle.status === 'failed' ? 'bg-red-600 text-white' :
                  cycle.status === 'running' ? 'bg-blue-600 text-white' :
                  'bg-gray-300 text-gray-600'
                }`}>
                  {cycle.cycle_number}
                </div>
                <div className="text-left">
                  <div className="font-semibold text-gray-900">
                    Cycle {cycle.cycle_number}
                    {cycle.status === 'running' && ' (In Progress)'}
                  </div>
                  {cycle.status === 'completed' && (
                    <div className="text-sm text-gray-600">
                      ✓ {cycle.findings_fixed || 0} fixed
                      {(cycle.findings_introduced || 0) > 0 && ` | ⚠ ${cycle.findings_introduced} new`}
                      {(cycle.findings_unchanged || 0) > 0 && ` | — ${cycle.findings_unchanged} unchanged`}
                    </div>
                  )}
                </div>
              </div>
              <svg
                className={`w-5 h-5 text-gray-400 transition-transform ${
                  expandedCycles.has(cycle.cycle_number) ? 'rotate-180' : ''
                }`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {expandedCycles.has(cycle.cycle_number) && cycle.status === 'completed' && (
              <div className="px-4 pb-4 space-y-3 border-t border-gray-100">
                <div className="grid grid-cols-2 gap-4 pt-3">
                  <div>
                    <div className="text-xs text-gray-600">Delta</div>
                    <div className="text-sm font-medium text-gray-900">
                      ✓ {cycle.findings_fixed || 0} fixed
                      {(cycle.findings_introduced || 0) > 0 && ` | ⚠ ${cycle.findings_introduced} new`}
                      {(cycle.findings_unchanged || 0) > 0 && ` | — ${cycle.findings_unchanged} unchanged`}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-600">Score Change</div>
                    <div className="text-sm font-medium text-gray-900">
                      {cycle.score_after || 'N/A'}
                      {cycle.cycle_number > 1 && status.cycles[cycle.cycle_number - 2]?.score_after && (
                        <span className="text-green-600 ml-1">
                          (+{(cycle.score_after || 0) - (status.cycles[cycle.cycle_number - 2].score_after || 0)})
                        </span>
                      )}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-600">Cost</div>
                    <div className="text-sm font-medium text-gray-900">
                      ${(cycle.claude_code_cost_usd || 0).toFixed(2)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-600">Duration</div>
                    <div className="text-sm font-medium text-gray-900">
                      {cycle.completed_at && cycle.started_at
                        ? `${Math.floor((new Date(cycle.completed_at).getTime() - new Date(cycle.started_at).getTime()) / 60000)}m ${Math.floor(((new Date(cycle.completed_at).getTime() - new Date(cycle.started_at).getTime()) % 60000) / 1000)}s`
                        : 'N/A'}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-600">Files Modified</div>
                    <div className="text-sm font-medium text-gray-900">{cycle.files_modified || 0}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-600">Verdict After</div>
                    <div className="text-sm font-medium text-gray-900">{cycle.verdict_after || 'N/A'}</div>
                  </div>
                </div>
                {cycle.claude_code_session_id && (
                  <div className="pt-2 border-t border-gray-100">
                    <div className="text-xs text-gray-600 mb-1">Claude Code Session</div>
                    <div className="text-xs font-mono text-gray-500">{cycle.claude_code_session_id}</div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Controls */}
      <div className="flex gap-3">
        {isRunning && !stopping && (
          <button
            onClick={handleStop}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
          >
            Stop After Current Cycle
          </button>
        )}
        {stopping && (
          <button
            disabled
            className="px-4 py-2 bg-red-600 text-white rounded-lg opacity-50 cursor-not-allowed"
          >
            Stopping...
          </button>
        )}
        {status.strategy === 'branch' && status.branch_name && (
          <button
            onClick={handleViewDiff}
            disabled={loadingDiff}
            className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50"
          >
            {loadingDiff ? 'Loading...' : diff ? 'Diff Loaded' : 'View Branch Diff'}
          </button>
        )}
      </div>

      {/* Diff Display */}
      {diff && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h3 className="font-semibold text-gray-900 mb-3">
            Branch Diff: {diff.branch_name}
          </h3>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {diff.files_changed.map((file) => (
              <div
                key={file.path}
                className="flex items-center justify-between text-sm bg-white p-2 rounded border border-gray-200"
              >
                <span className="font-mono text-gray-700">{file.path}</span>
                <div className="flex gap-3 text-xs">
                  <span className="text-green-600">+{file.additions}</span>
                  <span className="text-red-600">-{file.deletions}</span>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-3 pt-3 border-t border-gray-200 text-sm text-gray-600">
            Total: <span className="text-green-600">+{diff.total_additions}</span>{' '}
            <span className="text-red-600">-{diff.total_deletions}</span>
          </div>
        </div>
      )}

      {/* Completion Message */}
      {isComplete && (
        <div className={`rounded-lg p-4 ${
          completionReason === 'verdict_reached' ? 'bg-green-50 border border-green-200' :
          completionReason === 'error' ? 'bg-red-50 border border-red-200' :
          'bg-gray-50 border border-gray-200'
        }`}>
          <h3 className={`font-semibold mb-2 ${
            completionReason === 'verdict_reached' ? 'text-green-800' :
            completionReason === 'error' ? 'text-red-800' :
            'text-gray-800'
          }`}>
            {completionReason === 'verdict_reached' && 'GO Verdict Reached!'}
            {completionReason === 'max_cycles' && 'Maximum Cycles Completed'}
            {completionReason === 'user_stopped' && 'Stopped by User'}
            {completionReason === 'error' && 'Fix Loop Failed'}
          </h3>
          <p className={`text-sm ${
            completionReason === 'verdict_reached' ? 'text-green-700' :
            completionReason === 'error' ? 'text-red-700' :
            'text-gray-700'
          }`}>
            {completionReason === 'verdict_reached' &&
              'Your site has achieved a GO verdict. Review the changes and deploy when ready.'}
            {completionReason === 'max_cycles' &&
              'Completed all configured fix cycles. Review the improvements and decide next steps.'}
            {completionReason === 'user_stopped' &&
              'Fix loop stopped as requested. You can review the changes made so far.'}
            {completionReason === 'error' &&
              'An error occurred during the fix loop. Check the logs for details.'}
          </p>
          {status.strategy === 'branch' && status.branch_name && (
            <div className="mt-3 pt-3 border-t border-gray-300">
              <p className="text-sm font-medium text-gray-800 mb-1">
                Review and merge branch:
              </p>
              <code className="text-sm bg-white px-2 py-1 rounded border border-gray-300">
                {status.branch_name}
              </code>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
