import { useState } from 'react'
import { ScanResult, getReportUrl } from '../api/client'
import FixLoopConfig from './FixLoopConfig'
import FixLoopProgress from './FixLoopProgress'

interface ScanResultsProps {
  scan: ScanResult
  onLoopComplete?: () => void
}

function VerdictBadge({ verdict }: { verdict: string }) {
  const styles = {
    'GO': 'bg-green-500 text-white',
    'NO-GO': 'bg-red-500 text-white',
    'GO_WITH_CONDITIONS': 'bg-amber-500 text-white'
  }

  const labels = {
    'GO': 'GO',
    'NO-GO': 'NO-GO',
    'GO_WITH_CONDITIONS': 'GO WITH CONDITIONS'
  }

  return (
    <span className={`inline-block px-6 py-3 rounded-full text-2xl font-bold ${styles[verdict as keyof typeof styles] || 'bg-gray-500 text-white'}`}>
      {labels[verdict as keyof typeof labels] || verdict}
    </span>
  )
}

function GradeCircle({ score, grade }: { score: number; grade: string }) {
  const color = score >= 80 ? 'text-green-600' : score >= 60 ? 'text-yellow-600' : 'text-red-600'

  return (
    <div className="flex flex-col items-center">
      <div className={`text-5xl font-bold ${color}`}>{score}</div>
      <div className="text-gray-500 text-lg">/100 ({grade})</div>
    </div>
  )
}

function LensScoreCard({ name, score, grade, summary }: { name: string; score: number; grade: string; summary: string }) {
  const bgColor = score >= 80 ? 'bg-green-50 border-green-200' : score >= 60 ? 'bg-yellow-50 border-yellow-200' : 'bg-red-50 border-red-200'

  return (
    <div className={`p-4 rounded-lg border ${bgColor}`}>
      <div className="flex justify-between items-center mb-1">
        <span className="font-medium text-gray-900 capitalize">{name.replace('_', ' ')}</span>
        <span className="font-bold">{score} ({grade})</span>
      </div>
      <p className="text-sm text-gray-600">{summary}</p>
    </div>
  )
}

export default function ScanResults({ scan, onLoopComplete }: ScanResultsProps) {
  const [fixLoopActive, setFixLoopActive] = useState(false)
  const [loopId, setLoopId] = useState<string | null>(null)

  const hasFindings = scan.findings_count &&
    (scan.findings_count.critical || 0) +
    (scan.findings_count.high || 0) +
    (scan.findings_count.medium || 0) +
    (scan.findings_count.low || 0) > 0

  const showFixLoopConfig = hasFindings && !fixLoopActive && !loopId

  const handleLoopStarted = (newLoopId: string) => {
    setLoopId(newLoopId)
    setFixLoopActive(true)
  }

  const handleLoopComplete = () => {
    setFixLoopActive(false)
    if (onLoopComplete) {
      onLoopComplete()
    }
  }

  if (fixLoopActive && loopId) {
    return <FixLoopProgress scanId={scan.id} loopId={loopId} onComplete={handleLoopComplete} />
  }

  return (
    <div className="space-y-8">
      <div className="text-center">
        {scan.verdict && <VerdictBadge verdict={scan.verdict} />}
      </div>

      {scan.overall_score !== undefined && scan.overall_grade && (
        <div className="text-center">
          <GradeCircle score={scan.overall_score} grade={scan.overall_grade} />
        </div>
      )}

      <div className="flex justify-center gap-4">
        {scan.report_a_available && (
          <a
            href={getReportUrl(scan.id, 'a')}
            download
            className="px-6 py-3 bg-gray-900 hover:bg-gray-800 text-white font-medium rounded-lg transition-colors"
          >
            Download Report A (AI Handoff)
          </a>
        )}
        {scan.report_b_available && (
          <a
            href={getReportUrl(scan.id, 'b')}
            download
            className="px-6 py-3 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-colors"
          >
            Download Report B (Full Review)
          </a>
        )}
      </div>

      {scan.top_3_actions && scan.top_3_actions.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Top 3 Actions</h3>
          <ol className="space-y-3">
            {scan.top_3_actions.map((action, i) => (
              <li key={i} className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-green-100 text-green-700 flex items-center justify-center text-sm font-bold">
                  {i + 1}
                </span>
                <span className="text-gray-700">{action}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {scan.findings_count && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Findings Summary</h3>
          <div className="flex gap-4">
            <div className="flex-1 text-center p-3 bg-red-50 rounded-lg">
              <div className="text-2xl font-bold text-red-600">{scan.findings_count.critical || 0}</div>
              <div className="text-sm text-gray-600">Critical</div>
            </div>
            <div className="flex-1 text-center p-3 bg-orange-50 rounded-lg">
              <div className="text-2xl font-bold text-orange-600">{scan.findings_count.high || 0}</div>
              <div className="text-sm text-gray-600">High</div>
            </div>
            <div className="flex-1 text-center p-3 bg-yellow-50 rounded-lg">
              <div className="text-2xl font-bold text-yellow-600">{scan.findings_count.medium || 0}</div>
              <div className="text-sm text-gray-600">Medium</div>
            </div>
            <div className="flex-1 text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-gray-600">{scan.findings_count.low || 0}</div>
              <div className="text-sm text-gray-600">Low</div>
            </div>
          </div>
        </div>
      )}

      {scan.lens_scores && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Score Breakdown</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(scan.lens_scores).map(([name, data]) => (
              <LensScoreCard
                key={name}
                name={name}
                score={data.score}
                grade={data.grade}
                summary={data.summary}
              />
            ))}
          </div>
        </div>
      )}

      {showFixLoopConfig && (
        <div className="border-t border-gray-200 pt-8">
          <FixLoopConfig
            scanId={scan.id}
            apiKey={localStorage.getItem('apiKey') || ''}
            llmProvider={localStorage.getItem('llmProvider') || 'gemini'}
            onLoopStarted={handleLoopStarted}
          />
        </div>
      )}

      {scan.duration_seconds && (
        <p className="text-center text-sm text-gray-500">
          Scan completed in {Math.round(scan.duration_seconds)} seconds
        </p>
      )}
    </div>
  )
}
