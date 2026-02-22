import { useState } from 'react'
import { useSettings, AppSettings } from '../context/SettingsContext'

export default function SettingsPage() {
  const { settings, updateSettings, resetSettings } = useSettings()
  const [draft, setDraft] = useState<AppSettings>({ ...settings })
  const [saved, setSaved] = useState(false)

  function update<K extends keyof AppSettings>(key: K, value: AppSettings[K]) {
    setDraft(prev => ({ ...prev, [key]: value }))
  }

  function handleSave() {
    updateSettings(draft)
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  function handleReset() {
    resetSettings()
    setDraft({
      apiKey: '',
      llmProvider: 'gemini',
      maxCycles: 3,
      stopCondition: 'GO',
      applyMode: 'branch',
      permissionMode: 'full',
      deployMode: 'preview',
      deployCommand: 'vercel deploy --branch {branch}',
      localDevUrl: 'http://localhost:3000',
      severityFilter: { critical: true, high: true, medium: true, low: true },
      defaultRepoPath: '',
      defaultUserBrief: '',
      defaultTechStack: '',
    })
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600 mt-1">Configure defaults for scans and fix loops. These are saved locally in your browser.</p>
      </div>

      {saved && (
        <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-lg font-medium">
          Settings saved successfully.
        </div>
      )}

      {/* Section 1: API Configuration */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">API Configuration</h2>

        <div>
          <label htmlFor="settings-apiKey" className="block text-sm font-medium text-gray-700 mb-1">
            API Key
          </label>
          <input
            type="password"
            id="settings-apiKey"
            value={draft.apiKey}
            onChange={e => update('apiKey', e.target.value)}
            placeholder="Your Gemini or Claude API key"
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
          />
          <p className="mt-1 text-sm text-gray-500">
            Stored locally in your browser. Pre-fills the API key field when starting a scan.
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            LLM Provider
          </label>
          <div className="flex gap-4">
            <label className="flex items-center">
              <input
                type="radio"
                value="gemini"
                checked={draft.llmProvider === 'gemini'}
                onChange={e => update('llmProvider', e.target.value as 'gemini' | 'claude')}
                className="mr-2"
              />
              Gemini
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                value="claude"
                checked={draft.llmProvider === 'claude'}
                onChange={e => update('llmProvider', e.target.value as 'gemini' | 'claude')}
                className="mr-2"
              />
              Claude
            </label>
          </div>
        </div>
      </div>

      {/* Section 2: Fix Loop Defaults */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">Fix Loop Defaults</h2>
        <p className="text-sm text-gray-500">These pre-fill the fix loop configuration. You can still override per-run.</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="settings-maxCycles" className="block text-sm font-medium text-gray-700 mb-1">
              Max Cycles
            </label>
            <input
              type="number"
              id="settings-maxCycles"
              value={draft.maxCycles}
              onChange={e => update('maxCycles', Math.min(10, Math.max(1, parseInt(e.target.value) || 1)))}
              min={1}
              max={10}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
            />
          </div>

          <div>
            <label htmlFor="settings-stopCondition" className="block text-sm font-medium text-gray-700 mb-1">
              Stop Condition
            </label>
            <select
              id="settings-stopCondition"
              value={draft.stopCondition}
              onChange={e => update('stopCondition', e.target.value as AppSettings['stopCondition'])}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
            >
              <option value="GO">Stop on GO</option>
              <option value="GO_WITH_CONDITIONS">Stop on GO WITH CONDITIONS</option>
              <option value="on_loop_end">On Loop End</option>
              <option value="manual">Manual stop only</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Apply Mode</label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer p-3 border border-gray-200 rounded-lg hover:bg-gray-50 flex-1">
              <input
                type="radio"
                value="branch"
                checked={draft.applyMode === 'branch'}
                onChange={e => update('applyMode', e.target.value as 'branch' | 'direct')}
              />
              <div>
                <div className="font-medium text-gray-900 text-sm">Git Branch</div>
                <div className="text-xs text-gray-500">Recommended</div>
              </div>
            </label>
            <label className="flex items-center gap-2 cursor-pointer p-3 border border-gray-200 rounded-lg hover:bg-gray-50 flex-1">
              <input
                type="radio"
                value="direct"
                checked={draft.applyMode === 'direct'}
                onChange={e => update('applyMode', e.target.value as 'branch' | 'direct')}
              />
              <div>
                <div className="font-medium text-gray-900 text-sm">Direct Edits</div>
                <div className="text-xs text-gray-500">No safety net</div>
              </div>
            </label>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Permission Mode</label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer p-3 border border-gray-200 rounded-lg hover:bg-gray-50 flex-1">
              <input
                type="radio"
                value="full"
                checked={draft.permissionMode === 'full'}
                onChange={e => update('permissionMode', e.target.value as 'full' | 'cautious')}
              />
              <div>
                <div className="font-medium text-gray-900 text-sm">Full Automation</div>
              </div>
            </label>
            <label className="flex items-center gap-2 cursor-pointer p-3 border border-gray-200 rounded-lg hover:bg-gray-50 flex-1">
              <input
                type="radio"
                value="cautious"
                checked={draft.permissionMode === 'cautious'}
                onChange={e => update('permissionMode', e.target.value as 'full' | 'cautious')}
              />
              <div>
                <div className="font-medium text-gray-900 text-sm">Cautious</div>
              </div>
            </label>
          </div>
        </div>

        <div>
          <label htmlFor="settings-deployMode" className="block text-sm font-medium text-gray-700 mb-1">
            Deploy Mode
          </label>
          <select
            id="settings-deployMode"
            value={draft.deployMode}
            onChange={e => update('deployMode', e.target.value as AppSettings['deployMode'])}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
          >
            <option value="preview">Preview Deploy</option>
            <option value="local">Local Dev Server</option>
            <option value="manual">Manual</option>
          </select>
        </div>

        {draft.deployMode === 'preview' && (
          <div>
            <label htmlFor="settings-deployCommand" className="block text-sm font-medium text-gray-700 mb-1">
              Deploy Command
            </label>
            <input
              type="text"
              id="settings-deployCommand"
              value={draft.deployCommand}
              onChange={e => update('deployCommand', e.target.value)}
              placeholder="vercel deploy --branch {branch}"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
            />
            <p className="mt-1 text-sm text-gray-500">
              Use {'{branch}'} as a placeholder for the branch name.
            </p>
          </div>
        )}

        {draft.deployMode === 'local' && (
          <div>
            <label htmlFor="settings-localDevUrl" className="block text-sm font-medium text-gray-700 mb-1">
              Local Dev Server URL
            </label>
            <input
              type="url"
              id="settings-localDevUrl"
              value={draft.localDevUrl}
              onChange={e => update('localDevUrl', e.target.value)}
              placeholder="http://localhost:3000"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
            />
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Severity Filter</label>
          <div className="grid grid-cols-2 gap-2">
            {(['critical', 'high', 'medium', 'low'] as const).map(level => (
              <label key={level} className="flex items-center gap-2 cursor-pointer p-3 border border-gray-200 rounded-lg hover:bg-gray-50">
                <input
                  type="checkbox"
                  checked={draft.severityFilter[level]}
                  onChange={e => update('severityFilter', { ...draft.severityFilter, [level]: e.target.checked })}
                  className="w-4 h-4 text-green-600 rounded focus:ring-green-500"
                />
                <span className="font-medium text-gray-900 capitalize">{level}</span>
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* Section 3: Scan Defaults */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">Scan Defaults</h2>
        <p className="text-sm text-gray-500">Pre-fill values for new scans.</p>

        <div>
          <label htmlFor="settings-repoPath" className="block text-sm font-medium text-gray-700 mb-1">
            Default Repository Path
          </label>
          <input
            type="text"
            id="settings-repoPath"
            value={draft.defaultRepoPath}
            onChange={e => update('defaultRepoPath', e.target.value)}
            placeholder="/path/to/project"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
          />
          <p className="mt-1 text-sm text-gray-500">Pre-fills the repository path in the fix loop config.</p>
        </div>

        <div>
          <label htmlFor="settings-userBrief" className="block text-sm font-medium text-gray-700 mb-1">
            Default Brief / Instructions
          </label>
          <textarea
            id="settings-userBrief"
            value={draft.defaultUserBrief}
            onChange={e => update('defaultUserBrief', e.target.value)}
            placeholder="Tell GoNoGo about your project..."
            rows={3}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
          />
        </div>

        <div>
          <label htmlFor="settings-techStack" className="block text-sm font-medium text-gray-700 mb-1">
            Default Tech Stack
          </label>
          <input
            type="text"
            id="settings-techStack"
            value={draft.defaultTechStack}
            onChange={e => update('defaultTechStack', e.target.value)}
            placeholder="e.g., Next.js, Tailwind, Supabase"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <button
          onClick={handleSave}
          className="flex-1 py-3 px-6 bg-green-700 hover:bg-green-800 text-white font-semibold rounded-lg transition-colors"
        >
          Save Settings
        </button>
        <button
          onClick={handleReset}
          className="py-3 px-6 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium rounded-lg transition-colors border border-gray-300"
        >
          Reset to Defaults
        </button>
      </div>
    </div>
  )
}
