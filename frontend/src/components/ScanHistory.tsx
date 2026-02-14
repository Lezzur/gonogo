import { Link } from 'react-router-dom'
import { ScanResult } from '../api/client'

interface ScanHistoryProps {
  scans: ScanResult[]
}

function VerdictBadge({ verdict }: { verdict?: string }) {
  if (!verdict) return <span className="text-gray-400">-</span>

  const styles = {
    'GO': 'bg-green-100 text-green-800',
    'NO-GO': 'bg-red-100 text-red-800',
    'GO_WITH_CONDITIONS': 'bg-yellow-100 text-yellow-800'
  }

  const labels = {
    'GO': 'GO',
    'NO-GO': 'NO-GO',
    'GO_WITH_CONDITIONS': 'CONDITIONS'
  }

  return (
    <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${styles[verdict as keyof typeof styles] || 'bg-gray-100 text-gray-800'}`}>
      {labels[verdict as keyof typeof labels] || verdict}
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

export default function ScanHistory({ scans }: ScanHistoryProps) {
  if (scans.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">No scans yet. Run your first scan!</p>
        <Link to="/" className="text-green-600 hover:text-green-700 font-medium mt-2 inline-block">
          Start a scan
        </Link>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">URL</th>
            <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Date</th>
            <th className="text-center py-3 px-4 text-sm font-medium text-gray-500">Verdict</th>
            <th className="text-center py-3 px-4 text-sm font-medium text-gray-500">Score</th>
            <th className="text-center py-3 px-4 text-sm font-medium text-gray-500">Duration</th>
            <th className="text-center py-3 px-4 text-sm font-medium text-gray-500">Status</th>
          </tr>
        </thead>
        <tbody>
          {scans.map((scan) => (
            <tr key={scan.id} className="border-b border-gray-100 hover:bg-gray-50">
              <td className="py-3 px-4">
                <Link
                  to={`/scan/${scan.id}`}
                  className="text-gray-900 hover:text-green-600 font-medium"
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
                  <span className="text-gray-400">-</span>
                )}
              </td>
              <td className="py-3 px-4 text-center text-sm text-gray-600">
                {formatDuration(scan.duration_seconds)}
              </td>
              <td className="py-3 px-4 text-center">
                <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                  scan.status === 'completed' ? 'bg-green-100 text-green-800' :
                  scan.status === 'running' ? 'bg-blue-100 text-blue-800' :
                  scan.status === 'failed' ? 'bg-red-100 text-red-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {scan.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
