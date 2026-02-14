import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

interface ActiveScan {
  id: string
  url: string
}

interface ActiveScanContextType {
  activeScan: ActiveScan | null
  setActiveScan: (scan: ActiveScan | null) => void
  clearActiveScan: () => void
}

const ActiveScanContext = createContext<ActiveScanContextType | null>(null)

const STORAGE_KEY = 'gonogo_active_scan'

export function ActiveScanProvider({ children }: { children: ReactNode }) {
  const [activeScan, setActiveScanState] = useState<ActiveScan | null>(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored ? JSON.parse(stored) : null
  })

  const setActiveScan = (scan: ActiveScan | null) => {
    setActiveScanState(scan)
    if (scan) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(scan))
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  }

  const clearActiveScan = () => {
    setActiveScanState(null)
    localStorage.removeItem(STORAGE_KEY)
  }

  return (
    <ActiveScanContext.Provider value={{ activeScan, setActiveScan, clearActiveScan }}>
      {children}
    </ActiveScanContext.Provider>
  )
}

export function useActiveScan() {
  const context = useContext(ActiveScanContext)
  if (!context) {
    throw new Error('useActiveScan must be used within ActiveScanProvider')
  }
  return context
}
