import { ScanResult } from '../api/client'

interface ScanComparisonProps {
  scan1: ScanResult
  scan2: ScanResult
}

function ScoreBar({ score, color }: { score: number; color: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-100 rounded-full h-2">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="text-sm font-medium w-8">{score}</span>
    </div>
  )
}

export default function ScanComparison({ scan1, scan2 }: ScanComparisonProps) {
  const lenses = ['functionality', 'design', 'ux', 'performance', 'accessibility', 'code_quality']

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-6">Score Comparison</h3>

      <div className="grid grid-cols-3 gap-4 mb-4 text-sm font-medium text-gray-500">
        <div>{new URL(scan1.url).hostname}</div>
        <div className="text-center">Lens</div>
        <div className="text-right">{new URL(scan2.url).hostname}</div>
      </div>

      <div className="space-y-4">
        {lenses.map((lens) => {
          const score1 = scan1.lens_scores?.[lens]?.score ?? 0
          const score2 = scan2.lens_scores?.[lens]?.score ?? 0
          const diff = score2 - score1

          return (
            <div key={lens} className="grid grid-cols-3 gap-4 items-center">
              <ScoreBar score={score1} color="bg-blue-500" />
              <div className="text-center">
                <span className="text-sm font-medium text-gray-700 capitalize">
                  {lens.replace('_', ' ')}
                </span>
                {diff !== 0 && (
                  <span className={`ml-2 text-xs ${diff > 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {diff > 0 ? '+' : ''}{diff}
                  </span>
                )}
              </div>
              <ScoreBar score={score2} color="bg-green-500" />
            </div>
          )
        })}
      </div>

      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="grid grid-cols-3 gap-4 items-center">
          <div className="text-center">
            <div className="text-2xl font-bold">{scan1.overall_score ?? '-'}</div>
            <div className="text-sm text-gray-500">Overall</div>
          </div>
          <div className="text-center text-sm text-gray-400">vs</div>
          <div className="text-center">
            <div className="text-2xl font-bold">{scan2.overall_score ?? '-'}</div>
            <div className="text-sm text-gray-500">Overall</div>
          </div>
        </div>
      </div>
    </div>
  )
}
