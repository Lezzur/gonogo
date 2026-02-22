import { useState, FormEvent } from 'react'
import { checkFixLoopPrerequisites, startFixLoop, PrerequisiteCheckResponse, FixLoopStartResponse } from '../api/client'

interface FixLoopConfigProps {
  scanId: string
  apiKey: string
  llmProvider: string
  onLoopStarted: (loopId: string) => void
}

export default function FixLoopConfig({ scanId, apiKey, llmProvider, onLoopStarted }: FixLoopConfigProps) {
  const [repoPath, setRepoPath] = useState('')
  const [prerequisiteCheck, setPrerequisiteCheck] = useState<PrerequisiteCheckResponse | null>(null)
  const [isChecking, setIsChecking] = useState(false)
  const [checkError, setCheckError] = useState('')

  const [applyMode, setApplyMode] = useState<'branch' | 'direct'>('branch')
  const [permissionMode, setPermissionMode] = useState<'full' | 'cautious'>('full')

  const [severityCritical, setSeverityCritical] = useState(true)
  const [severityHigh, setSeverityHigh] = useState(true)
  const [severityMedium, setSeverityMedium] = useState(false)
  const [severityLow, setSeverityLow] = useState(false)

  const [deployMode, setDeployMode] = useState<'preview' | 'local' | 'manual'>('preview')
  const [deployCommand, setDeployCommand] = useState('vercel deploy --branch {branch}')
  const [localDevUrl, setLocalDevUrl] = useState('http://localhost:3000')

  const [maxCycles, setMaxCycles] = useState(3)
  const [stopCondition, setStopCondition] = useState<'GO' | 'GO_WITH_CONDITIONS' | 'manual'>('GO')

  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [startErrorDetails, setStartErrorDetails] = useState<string | null>(null)

  async function handleCheckPrerequisites() {
    if (!repoPath.trim()) {
      setCheckError('Repository path is required')
      return
    }

    setIsChecking(true)
    setCheckError('')
    setPrerequisiteCheck(null)

    try {
      const result = await checkFixLoopPrerequisites(scanId)
      setPrerequisiteCheck(result)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error occurred'
      setCheckError(`Failed to check prerequisites: ${errorMsg}`)
      console.error('Prerequisite check failed:', err)
    } finally {
      setIsChecking(false)
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setStartErrorDetails(null)
    setIsSubmitting(true)

    try {
      const severityFilter: string[] = []
      if (severityCritical) severityFilter.push('critical')
      if (severityHigh) severityFilter.push('high')
      if (severityMedium) severityFilter.push('medium')
      if (severityLow) severityFilter.push('low')

      if (severityFilter.length === 0) {
        setError('Please select at least one severity level')
        setIsSubmitting(false)
        return
      }

      const result: FixLoopStartResponse = await startFixLoop({
        scan_id: scanId,
        severity_filter: severityFilter,
        strategy: applyMode,
        branch_name: applyMode === 'branch' ? `gonogo/fix-${scanId.slice(0, 8)}` : undefined,
        max_cycles: maxCycles,
        stop_on_verdict: stopCondition === 'manual' ? undefined : stopCondition,
        deploy_command: deployMode === 'preview' ? deployCommand : undefined,
        deploy_strategy: deployMode,
        api_key: apiKey,
        llm_provider: llmProvider
      })

      onLoopStarted(result.loop_id)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error occurred'
      setError('Failed to start fix loop')
      setStartErrorDetails(errorMsg)
      console.error('Fix loop start failed:', err)
      setIsSubmitting(false)
    }
  }

  const showFullAutomationWarning = applyMode === 'direct' && permissionMode === 'full'

  return (
    <div className="max-w-3xl mx-auto">
      <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Automated Fix Loop</h2>
          <p className="text-gray-600 mt-1">
            Claude Code will fix issues, redeploy, and rescan automatically.
          </p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <svg className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="flex-1">
                <h3 className="font-semibold text-red-800 mb-1">{error}</h3>
                {startErrorDetails && (
                  <div className="mt-2">
                    <p className="text-sm text-red-700 font-medium mb-1">Error Details:</p>
                    <pre className="text-xs text-red-700 bg-red-100 p-2 rounded border border-red-300 overflow-x-auto">
                      {startErrorDetails}
                    </pre>
                  </div>
                )}
                <div className="mt-3 space-y-1">
                  <p className="text-sm text-red-700 font-medium">Troubleshooting steps:</p>
                  <ul className="text-sm text-red-700 list-disc list-inside space-y-1">
                    <li>Verify the repository path is correct</li>
                    <li>Ensure prerequisite checks passed</li>
                    <li>Check that your API key is valid</li>
                    <li>Confirm the scan ID exists</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Repository Path */}
          <div>
            <label htmlFor="repoPath" className="block text-sm font-medium text-gray-700 mb-1">
              Repository Path <span className="text-red-500">*</span>
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                id="repoPath"
                value={repoPath}
                onChange={(e) => {
                  setRepoPath(e.target.value)
                  setPrerequisiteCheck(null)
                }}
                placeholder="/path/to/project"
                required
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
              />
              <button
                type="button"
                onClick={handleCheckPrerequisites}
                disabled={isChecking || !repoPath.trim()}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-800 disabled:bg-gray-400 text-white font-medium rounded-lg transition-colors"
              >
                {isChecking ? 'Checking...' : 'Check'}
              </button>
            </div>

            {checkError && (
              <p className="mt-2 text-sm text-red-600">{checkError}</p>
            )}

            {prerequisiteCheck && (
              <div className={`mt-2 p-3 rounded-lg border ${prerequisiteCheck.ready ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                <div className="flex items-center gap-2">
                  {prerequisiteCheck.ready ? (
                    <>
                      <span className="text-green-600 font-bold">✓</span>
                      <span className="text-sm text-green-800 font-medium">Ready for automated fixes</span>
                    </>
                  ) : (
                    <>
                      <span className="text-red-600 font-bold">✗</span>
                      <span className="text-sm text-red-800 font-medium">Not ready</span>
                    </>
                  )}
                </div>

                {prerequisiteCheck.errors && prerequisiteCheck.errors.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {prerequisiteCheck.errors.map((err, i) => (
                      <li key={i} className="text-sm text-red-700">• {err}</li>
                    ))}
                  </ul>
                )}

                {prerequisiteCheck.warnings && prerequisiteCheck.warnings.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {prerequisiteCheck.warnings.map((warn, i) => (
                      <li key={i} className="text-sm text-amber-700">• {warn}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>

          {/* Apply Mode */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Apply Mode
            </label>
            <div className="space-y-2">
              <label className="flex items-start gap-3 cursor-pointer p-3 border border-gray-200 rounded-lg hover:bg-gray-50">
                <input
                  type="radio"
                  value="branch"
                  checked={applyMode === 'branch'}
                  onChange={(e) => setApplyMode(e.target.value as 'branch')}
                  className="mt-1"
                />
                <div>
                  <div className="font-medium text-gray-900">Git Branch (Recommended)</div>
                  <div className="text-sm text-gray-600">
                    Applies fixes to a new branch. Full rollback capability — discard the branch if fixes are bad. You can review the diff before merging.
                  </div>
                </div>
              </label>

              <label className="flex items-start gap-3 cursor-pointer p-3 border border-gray-200 rounded-lg hover:bg-gray-50">
                <input
                  type="radio"
                  value="direct"
                  checked={applyMode === 'direct'}
                  onChange={(e) => setApplyMode(e.target.value as 'direct')}
                  className="mt-1"
                />
                <div>
                  <div className="font-medium text-gray-900">Direct Edits</div>
                  <div className="text-sm text-gray-600">
                    Modifies files in place. Zero git overhead, fastest path for solo devs iterating rapidly. No safety net if a fix breaks something.
                  </div>
                </div>
              </label>
            </div>
          </div>

          {/* Permission Mode */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Permission Mode
            </label>
            <div className="space-y-2">
              <label className="flex items-start gap-3 cursor-pointer p-3 border border-gray-200 rounded-lg hover:bg-gray-50">
                <input
                  type="radio"
                  value="full"
                  checked={permissionMode === 'full'}
                  onChange={(e) => setPermissionMode(e.target.value as 'full')}
                  className="mt-1"
                />
                <div>
                  <div className="font-medium text-gray-900">Full Automation</div>
                  <div className="text-sm text-gray-600">
                    Claude Code can run any operation. Git branch provides safety.
                  </div>
                </div>
              </label>

              <label className="flex items-start gap-3 cursor-pointer p-3 border border-gray-200 rounded-lg hover:bg-gray-50">
                <input
                  type="radio"
                  value="cautious"
                  checked={permissionMode === 'cautious'}
                  onChange={(e) => setPermissionMode(e.target.value as 'cautious')}
                  className="mt-1"
                />
                <div>
                  <div className="font-medium text-gray-900">Cautious</div>
                  <div className="text-sm text-gray-600">
                    Claude Code can edit files freely but needs approval for bash commands. May result in incomplete fixes if Claude Code needs to run install/build commands.
                  </div>
                </div>
              </label>
            </div>

            {showFullAutomationWarning && (
              <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <div className="flex gap-2">
                  <span className="text-amber-600 flex-shrink-0">⚠</span>
                  <p className="text-sm text-amber-800">
                    Full automation without git branch means no rollback. Consider switching to Git Branch mode or Cautious permissions.
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Severity Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Severity Filter
            </label>
            <div className="grid grid-cols-2 gap-2">
              <label className="flex items-center gap-2 cursor-pointer p-3 border border-gray-200 rounded-lg hover:bg-gray-50">
                <input
                  type="checkbox"
                  checked={severityCritical}
                  onChange={(e) => setSeverityCritical(e.target.checked)}
                  className="w-4 h-4 text-green-600 rounded focus:ring-green-500"
                />
                <span className="font-medium text-gray-900">Critical</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer p-3 border border-gray-200 rounded-lg hover:bg-gray-50">
                <input
                  type="checkbox"
                  checked={severityHigh}
                  onChange={(e) => setSeverityHigh(e.target.checked)}
                  className="w-4 h-4 text-green-600 rounded focus:ring-green-500"
                />
                <span className="font-medium text-gray-900">High</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer p-3 border border-gray-200 rounded-lg hover:bg-gray-50">
                <input
                  type="checkbox"
                  checked={severityMedium}
                  onChange={(e) => setSeverityMedium(e.target.checked)}
                  className="w-4 h-4 text-green-600 rounded focus:ring-green-500"
                />
                <span className="font-medium text-gray-900">Medium</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer p-3 border border-gray-200 rounded-lg hover:bg-gray-50">
                <input
                  type="checkbox"
                  checked={severityLow}
                  onChange={(e) => setSeverityLow(e.target.checked)}
                  className="w-4 h-4 text-green-600 rounded focus:ring-green-500"
                />
                <span className="font-medium text-gray-900">Low</span>
              </label>
            </div>
          </div>

          {/* Deploy Mode */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Deploy Mode
            </label>
            <select
              value={deployMode}
              onChange={(e) => setDeployMode(e.target.value as 'preview' | 'local' | 'manual')}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
            >
              <option value="preview">Preview Deploy</option>
              <option value="local">Local Dev Server</option>
              <option value="manual">Manual</option>
            </select>

            {deployMode === 'preview' && (
              <div className="mt-3">
                <label htmlFor="deployCommand" className="block text-sm font-medium text-gray-700 mb-1">
                  Deploy Command
                </label>
                <input
                  type="text"
                  id="deployCommand"
                  value={deployCommand}
                  onChange={(e) => setDeployCommand(e.target.value)}
                  placeholder="vercel deploy --branch {branch}"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                />
                <p className="mt-1 text-sm text-gray-500">
                  Use {'{branch}'} as a placeholder for the branch name.
                </p>
              </div>
            )}

            {deployMode === 'local' && (
              <div className="mt-3">
                <label htmlFor="localDevUrl" className="block text-sm font-medium text-gray-700 mb-1">
                  Local Dev Server URL
                </label>
                <input
                  type="url"
                  id="localDevUrl"
                  value={localDevUrl}
                  onChange={(e) => setLocalDevUrl(e.target.value)}
                  placeholder="http://localhost:3000"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                />
              </div>
            )}

            {deployMode === 'manual' && (
              <div className="mt-3 p-3 bg-gray-50 border border-gray-200 rounded-lg">
                <p className="text-sm text-gray-600">
                  GoNoGo will pause after each fix cycle and wait for you to manually deploy and confirm. You'll be prompted to provide the deployed URL before rescanning.
                </p>
              </div>
            )}
          </div>

          {/* Max Cycles */}
          <div>
            <label htmlFor="maxCycles" className="block text-sm font-medium text-gray-700 mb-1">
              Max Cycles
            </label>
            <input
              type="number"
              id="maxCycles"
              value={maxCycles}
              onChange={(e) => setMaxCycles(parseInt(e.target.value))}
              min={1}
              max={10}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
            />
            <p className="mt-1 text-sm text-gray-500">
              Number of scan → fix → rescan cycles (1-10). Default: 3.
            </p>
          </div>

          {/* Stop Condition */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Stop Condition
            </label>
            <select
              value={stopCondition}
              onChange={(e) => setStopCondition(e.target.value as 'GO' | 'GO_WITH_CONDITIONS' | 'manual')}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
            >
              <option value="GO">Stop on GO (Recommended)</option>
              <option value="GO_WITH_CONDITIONS">Stop on GO WITH CONDITIONS</option>
              <option value="manual">Manual stop only</option>
            </select>
            <p className="mt-1 text-sm text-gray-500">
              Loop will stop early if this verdict is reached, regardless of remaining cycles.
            </p>
          </div>

          {/* Submit Button */}
          <div className="pt-4 border-t border-gray-200">
            <button
              type="submit"
              disabled={isSubmitting || (prerequisiteCheck?.ready === false)}
              className="w-full py-4 px-6 bg-green-700 hover:bg-green-800 disabled:bg-green-400 text-white text-lg font-semibold rounded-lg transition-colors"
            >
              {isSubmitting ? 'Starting Fix Loop...' : 'Start Automated Fix Loop'}
            </button>
            <p className="mt-2 text-center text-sm text-gray-500">
              Estimated cost: ~$2-5 per cycle
            </p>
          </div>
        </form>
      </div>
    </div>
  )
}
