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
        <div className="text-center">
          <p className="text-red-600">{error || 'Scan not found'}</p>
          <Link to="/" className="text-green-600 hover:text-green-700 mt-4 inline-block">
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
          <div className="text-center py-8">
            <div className="text-red-600 font-medium mb-2">Scan Failed</div>
            <p className="text-gray-600 text-sm">
              Something went wrong during the scan. Please try again.
            </p>
            <Link
              to="/"
              className="mt-4 inline-block px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg"
            >
              Start a new scan
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
