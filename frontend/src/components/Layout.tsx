import { Link, useLocation } from 'react-router-dom'
import { ReactNode } from 'react'
import { useActiveScan } from '../context/ActiveScanContext'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const { activeScan } = useActiveScan()
  const location = useLocation()

  const isOnActiveScan = activeScan && location.pathname === `/scan/${activeScan.id}`
  const showActiveScanBanner = activeScan && !isOnActiveScan

  return (
    <div className="min-h-screen flex flex-col">
      {showActiveScanBanner && (
        <div className="bg-blue-600 text-white px-4 py-2">
          <div className="max-w-5xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
              <span className="text-sm">
                Scan in progress: <span className="font-medium">{new URL(activeScan.url).hostname}</span>
              </span>
            </div>
            <Link
              to={`/scan/${activeScan.id}`}
              className="text-sm font-medium bg-white/20 hover:bg-white/30 px-3 py-1 rounded"
            >
              Return to scan
            </Link>
          </div>
        </div>
      )}
      <header className="border-b border-gray-200 bg-white">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <svg className="w-8 h-8" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="45" fill="#22c55e" stroke="#166534" strokeWidth="4"/>
              <path d="M30 50 L45 65 L70 35" stroke="white" strokeWidth="8" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <span className="text-xl font-bold text-gray-900">GoNoGo</span>
          </Link>
          <nav className="flex items-center gap-6">
            <Link to="/" className="text-gray-600 hover:text-gray-900">
              New Scan
            </Link>
            <Link to="/history" className="text-gray-600 hover:text-gray-900">
              History
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1">
        {children}
      </main>

      <footer className="border-t border-gray-200 bg-white py-6">
        <div className="max-w-5xl mx-auto px-4 text-center text-sm text-gray-500">
          GoNoGo — Your pre-launch checkpoint
        </div>
      </footer>
    </div>
  )
}
