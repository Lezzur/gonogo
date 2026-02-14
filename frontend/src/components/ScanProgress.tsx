import { useEffect, useState } from 'react'
import { subscribeToProgress, ProgressEvent } from '../api/client'

interface ScanProgressProps {
  scanId: string
  onComplete: () => void
}

const STEPS = [
  { key: 'step_0_recon', label: 'Reconnaissance' },
  { key: 'step_1_intent', label: 'Intent Analysis' },
  { key: 'step_2_tech', label: 'Tech Stack Detection' },
  { key: 'step_3_8_lenses', label: 'Quality Evaluation' },
  { key: 'step_9_synthesis', label: 'Synthesis & Scoring' },
  { key: 'step_10_reports', label: 'Report Generation' }
]

export default function ScanProgress({ scanId, onComplete }: ScanProgressProps) {
  const [currentStep, setCurrentStep] = useState('')
  const [message, setMessage] = useState('Initializing scan...')
  const [percent, setPercent] = useState(0)
  const [logs, setLogs] = useState<string[]>([])
  const [showLogs, setShowLogs] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const unsubscribe = subscribeToProgress(
      scanId,
      (event: ProgressEvent) => {
        setCurrentStep(event.step)
        setMessage(event.message)
        setPercent(event.percent)
        setLogs(prev => [...prev, `[${event.step}] ${event.message}`])
      },
      () => {
        onComplete()
      },
      (errorMessage: string) => {
        setError(errorMessage)
      }
    )

    return unsubscribe
  }, [scanId, onComplete])

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-red-800 mb-2">Scan Failed</h3>
        <p className="text-red-700">{error}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-gray-100 mb-4">
          <svg className="w-12 h-12 text-green-600 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Scanning...</h2>
        <p className="text-gray-600">{message}</p>
      </div>

      <div className="bg-gray-100 rounded-full h-3 overflow-hidden">
        <div
          className="bg-green-600 h-full transition-all duration-500"
          style={{ width: `${percent}%` }}
        />
      </div>

      <div className="flex justify-center gap-2">
        {STEPS.map((step, i) => {
          const isActive = step.key === currentStep
          const isPast = STEPS.findIndex(s => s.key === currentStep) > i

          return (
            <div
              key={step.key}
              className={`w-3 h-3 rounded-full ${
                isActive ? 'bg-green-600 ring-4 ring-green-100' :
                isPast ? 'bg-green-600' : 'bg-gray-300'
              }`}
              title={step.label}
            />
          )
        })}
      </div>

      <p className="text-center text-sm text-gray-500">
        Usually takes 2-5 minutes
      </p>

      <div className="text-center">
        <button
          onClick={() => setShowLogs(!showLogs)}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          {showLogs ? 'Hide' : 'Show'} detailed progress
        </button>
      </div>

      {showLogs && (
        <div className="bg-gray-900 rounded-lg p-4 max-h-64 overflow-y-auto">
          <pre className="text-xs text-gray-300 font-mono">
            {logs.map((log, i) => (
              <div key={i}>{log}</div>
            ))}
          </pre>
        </div>
      )}
    </div>
  )
}
