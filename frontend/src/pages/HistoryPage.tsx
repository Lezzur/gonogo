import { useEffect, useState } from 'react'
import { listScans, ScanResult } from '../api/client'
import ScanHistory from '../components/ScanHistory'
import ScanComparison from '../components/ScanComparison'

export default function HistoryPage() {
  const [scans, setScans] = useState<ScanResult[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedScans, setSelectedScans] = useState<string[]>([])
  const [compareMode, setCompareMode] = useState(false)

  useEffect(() => {
    async function fetchScans() {
      try {
        const data = await listScans()
        setScans(data.scans)
      } catch (err) {
        console.error('Failed to fetch scans:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchScans()
  }, [])

  const handleCompareToggle = () => {
    setCompareMode(!compareMode)
    setSelectedScans([])
  }

  const handleScanSelect = (scanId: string) => {
    if (selectedScans.includes(scanId)) {
      setSelectedScans(selectedScans.filter(id => id !== scanId))
    } else if (selectedScans.length < 2) {
      setSelectedScans([...selectedScans, scanId])
    }
  }

  const scan1 = scans.find(s => s.id === selectedScans[0])
  const scan2 = scans.find(s => s.id === selectedScans[1])

  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Scan History</h1>
        {scans.length >= 2 && (
          <button
            onClick={handleCompareToggle}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${
              compareMode
                ? 'bg-gray-900 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {compareMode ? 'Cancel Compare' : 'Compare Scans'}
          </button>
        )}
      </div>

      {loading ? (
        <div className="text-center py-12">
          <div className="animate-spin w-8 h-8 border-4 border-green-600 border-t-transparent rounded-full mx-auto" />
          <p className="mt-4 text-gray-600">Loading scans...</p>
        </div>
      ) : (
        <>
          {compareMode && (
            <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-800">
                {selectedScans.length === 0 && 'Select two scans to compare'}
                {selectedScans.length === 1 && 'Select one more scan to compare'}
                {selectedScans.length === 2 && 'Showing comparison below'}
              </p>
            </div>
          )}

          {compareMode ? (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="w-12 py-3 px-4"></th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">URL</th>
                    <th className="text-center py-3 px-4 text-sm font-medium text-gray-500">Score</th>
                    <th className="text-center py-3 px-4 text-sm font-medium text-gray-500">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {scans.filter(s => s.status === 'completed').map((scan) => (
                    <tr
                      key={scan.id}
                      className={`border-b border-gray-100 cursor-pointer ${
                        selectedScans.includes(scan.id) ? 'bg-green-50' : 'hover:bg-gray-50'
                      }`}
                      onClick={() => handleScanSelect(scan.id)}
                    >
                      <td className="py-3 px-4">
                        <input
                          type="checkbox"
                          checked={selectedScans.includes(scan.id)}
                          onChange={() => handleScanSelect(scan.id)}
                          className="w-4 h-4 text-green-600 rounded"
                        />
                      </td>
                      <td className="py-3 px-4 font-medium">{new URL(scan.url).hostname}</td>
                      <td className="py-3 px-4 text-center">{scan.overall_score ?? '-'}</td>
                      <td className="py-3 px-4 text-center text-sm text-gray-600">
                        {new Date(scan.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200">
              <ScanHistory scans={scans} />
            </div>
          )}

          {compareMode && scan1 && scan2 && (
            <div className="mt-8">
              <ScanComparison scan1={scan1} scan2={scan2} />
            </div>
          )}
        </>
      )}
    </div>
  )
}
