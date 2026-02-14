import { Link } from 'react-router-dom'
import { ScanResult } from '../api/client'

interface ScanHistoryProps {
  scans: ScanResult[]
}

function VerdictBadge({ verdict }: { verdict?: string }) {
  if (!verdict) return null

  const styles = {
    'GO': 'bg-green-100 text-green-800',
    'NO-GO': 'bg-red-100 text-red-800',
    'GO_WITH_CONDITIONS': 'bg-yellow-100 text-yellow-800'
  }

  const labels = {
    'GO': 'GO',
    'NO-GO': 'NO-GO',
    'GO_WITH_CONDITIONS': 'CONDITIONAL'
  }

  return (
    <span className={`inline-block px-2 py-1 rounded-full text-xs font-medium uppercase ${styles[verdict as keyof typeof styles] || 'bg-gray-100 text-gray-800'}`}>
      {labels[verdict as keyof typeof labels] || verdict}
    </span>
  )
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-block px-2 py-1 rounded-full text-xs font-medium ${
      status === 'completed' ? 'bg-gray-100 text-gray-600' :
      status === 'running' ? 'bg-blue-100 text-blue-800' :
      status === 'failed' ? 'bg-red-100 text-red-800' :
      'bg-gray-100 text-gray-800'
    }`}>
      {status}
    </span>
  )
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatDuration(seconds?: number): string {
  if (!seconds) return '-'
  if (seconds < 60) return `${Math.round(seconds)}s`
  return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
}

function ChevronRight() {
  return (
    <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
    </svg>
  )
}

export default function ScanHistory({ scans }: ScanHistoryProps) {
  if (scans.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">No scans yet. Run your first scan!</p>
        <Link to="/" className="text-green-700 underline hover:text-green-800 font-medium mt-2 inline-block">
          Start a scan
        </Link>
      </div>
    )
  }

  return (
    <>
      {/* Mobile card layout */}
      <div className="md:hidden divide-y divide-gray-100">
        {scans.map((scan) => (
          <Link
            key={scan.id}
            to={`/scan/${scan.id}`}
            className="block p-4 hover:bg-gray-50 active:bg-gray-100"
          >
            <div className="flex items-center justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="font-medium text-gray-900 truncate">
                  {new URL(scan.url).hostname}
                </div>
                <div className="text-sm text-gray-500 mt-1">
                  {formatDate(scan.created_at)}
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <VerdictBadge verdict={scan.verdict} />
                  <StatusBadge status={scan.status} />
                  {scan.overall_score !== undefined && (
                    <span className="text-sm font-medium text-gray-700">
                      {scan.overall_score}/100
                    </span>
                  )}
                </div>
              </div>
              <ChevronRight />
            </div>
          </Link>
        ))}
      </div>

      {/* Desktop table layout */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">URL</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Date</th>
              <th className="text-center py-3 px-4 text-sm font-medium text-gray-500">Verdict</th>
              <th className="text-center py-3 px-4 text-sm font-medium text-gray-500">Score</th>
              <th className="text-center py-3 px-4 text-sm font-medium text-gray-500">Duration</th>
              <th className="text-center py-3 px-4 text-sm font-medium text-gray-500">Status</th>
              <th className="w-10"></th>
            </tr>
          </thead>
          <tbody>
            {scans.map((scan) => (
              <tr key={scan.id} className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer group">
                <td className="py-3 px-4">
                  <Link
                    to={`/scan/${scan.id}`}
                    className="text-gray-900 group-hover:text-green-600 font-medium"
                  >
                    {new URL(scan.url).hostname}
                  </Link>
                </td>
                <td className="py-3 px-4 text-sm text-gray-600">
                  {formatDate(scan.created_at)}
                </td>
                <td className="py-3 px-4 text-center">
                  <VerdictBadge verdict={scan.verdict} />
                </td>
                <td className="py-3 px-4 text-center">
                  {scan.overall_score !== undefined ? (
                    <span className="font-medium">{scan.overall_score}</span>
                  ) : (
                    <span className="text-gray-600">-</span>
                  )}
                </td>
                <td className="py-3 px-4 text-center text-sm text-gray-600">
                  {formatDuration(scan.duration_seconds)}
                </td>
                <td className="py-3 px-4 text-center">
                  <StatusBadge status={scan.status} />
                </td>
                <td className="py-3 px-4">
                  <Link to={`/scan/${scan.id}`} className="opacity-0 group-hover:opacity-100 transition-opacity">
                    <ChevronRight />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
