import { useEffect, useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getScan, ScanResult } from '../api/client'
import ScanProgress from '../components/ScanProgress'
import ScanResults from '../components/ScanResults'
import { useActiveScan } from '../context/ActiveScanContext'

export default function ScanPage() {
  const { scanId } = useParams<{ scanId: string }>()
  const [scan, setScan] = useState<ScanResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const { activeScan, clearActiveScan } = useActiveScan()

  const fetchScan = useCallback(async () => {
    if (!scanId) return

    try {
      const data = await getScan(scanId)
      setScan(data)
      setLoading(false)

      // Clear active scan if this scan is done
      if (activeScan?.id === scanId && (data.status === 'completed' || data.status === 'failed')) {
        clearActiveScan()
      }
    } catch {
      setError('Failed to load scan')
      setLoading(false)
    }
  }, [scanId, activeScan, clearActiveScan])

  useEffect(() => {
    fetchScan()
  }, [fetchScan])

  const handleComplete = useCallback(() => {
    clearActiveScan()
    fetchScan()
  }, [fetchScan, clearActiveScan])

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-4 border-green-600 border-t-transparent rounded-full mx-auto" />
          <p className="mt-4 text-gray-600">Loading scan...</p>
        </div>
      </div>
    )
  }

  if (error || !scan) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-50 flex items-center justify-center">
            <svg className="w-8 h-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-gray-900 mb-1">Scan not found</h2>
          <p className="text-sm text-gray-500 mb-6">
            This scan may have been removed or the link is invalid.
          </p>
          <Link
            to="/"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-green-700 hover:bg-green-800 text-white font-medium rounded-lg transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Start a new scan
          </Link>
        </div>
      </div>
    )
  }

  const isInProgress = scan.status === 'pending' || scan.status === 'running'

  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <div className="mb-6">
        <Link to="/" className="text-gray-500 hover:text-gray-700 text-sm flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          New scan
        </Link>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <div className="mb-6 pb-6 border-b border-gray-200">
          <h1 className="text-xl font-semibold text-gray-900 break-all">{scan.url}</h1>
          <p className="text-sm text-gray-500 mt-1">
            {new Date(scan.created_at).toLocaleString()}
          </p>
        </div>

        {isInProgress ? (
          <ScanProgress scanId={scan.id} onComplete={handleComplete} />
        ) : scan.status === 'completed' ? (
          <ScanResults scan={scan} onLoopComplete={fetchScan} />
        ) : (
          <div className="py-8 space-y-4">
            {scan.warnings && scan.warnings.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                {scan.warnings.map((warning, i) => (
                  <div key={i} className="flex gap-2">
                    <span className="text-amber-600 flex-shrink-0">&#9888;</span>
                    <p className="text-sm text-amber-800">{warning}</p>
                  </div>
                ))}
              </div>
            )}
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="text-red-600 font-semibold mb-1">Scan Failed</div>
              <p className="text-sm text-red-700">
                {scan.error_message || 'Something went wrong during the scan. Please try again.'}
              </p>
            </div>
            <div className="text-center">
              <Link
                to="/"
                className="inline-block px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg"
              >
                Start a new scan
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
