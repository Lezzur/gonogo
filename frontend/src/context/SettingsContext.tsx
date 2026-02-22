import { createContext, useContext, useState, ReactNode, useCallback } from 'react'

export interface AppSettings {
  // API Configuration
  apiKey: string
  llmProvider: 'gemini' | 'claude'

  // Fix Loop Defaults
  maxCycles: number
  stopCondition: 'GO' | 'GO_WITH_CONDITIONS' | 'on_loop_end' | 'manual'
  applyMode: 'branch' | 'direct'
  permissionMode: 'full' | 'cautious'
  deployMode: 'preview' | 'local' | 'manual'
  deployCommand: string
  localDevUrl: string
  severityFilter: {
    critical: boolean
    high: boolean
    medium: boolean
    low: boolean
  }

  // Scan Defaults
  defaultRepoPath: string
  defaultUserBrief: string
  defaultTechStack: string
}

const DEFAULT_SETTINGS: AppSettings = {
  apiKey: '',
  llmProvider: 'gemini',
  maxCycles: 3,
  stopCondition: 'GO',
  applyMode: 'branch',
  permissionMode: 'full',
  deployMode: 'preview',
  deployCommand: 'vercel deploy --branch {branch}',
  localDevUrl: 'http://localhost:3000',
  severityFilter: {
    critical: true,
    high: true,
    medium: true,
    low: true,
  },
  defaultRepoPath: '',
  defaultUserBrief: '',
  defaultTechStack: '',
}

const STORAGE_KEY = 'gonogo-settings'

interface SettingsContextType {
  settings: AppSettings
  updateSettings: (partial: Partial<AppSettings>) => void
  resetSettings: () => void
}

const SettingsContext = createContext<SettingsContextType | null>(null)

function loadSettings(): AppSettings {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) }
    }
  } catch (e) {
    console.error('Failed to load settings from localStorage:', e)
  }
  return DEFAULT_SETTINGS
}

function saveSettings(settings: AppSettings) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
  } catch (e) {
    console.error('Failed to save settings to localStorage:', e)
  }
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<AppSettings>(loadSettings)

  const updateSettings = useCallback((partial: Partial<AppSettings>) => {
    setSettings(prev => {
      const next = { ...prev, ...partial }
      saveSettings(next)
      return next
    })
  }, [])

  const resetSettings = useCallback(() => {
    setSettings(DEFAULT_SETTINGS)
    saveSettings(DEFAULT_SETTINGS)
  }, [])

  return (
    <SettingsContext.Provider value={{ settings, updateSettings, resetSettings }}>
      {children}
    </SettingsContext.Provider>
  )
}

export function useSettings() {
  const context = useContext(SettingsContext)
  if (!context) {
    throw new Error('useSettings must be used within SettingsProvider')
  }
  return context
}
