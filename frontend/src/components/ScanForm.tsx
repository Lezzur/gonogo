import { useState, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { createScan } from '../api/client'
import { useActiveScan } from '../context/ActiveScanContext'

export default function ScanForm() {
  const navigate = useNavigate()
  const { setActiveScan } = useActiveScan()
  const [url, setUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [llmProvider, setLlmProvider] = useState('gemini')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [userBrief, setUserBrief] = useState('')
  const [techStack, setTechStack] = useState('')
  const [testRoute, setTestRoute] = useState('')
  const [authUsername, setAuthUsername] = useState('')
  const [authPassword, setAuthPassword] = useState('')
  const [showAuth, setShowAuth] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      const normalizedUrl = url.startsWith('http') ? url : `https://${url}`
      const result = await createScan({
        url,
        api_key: apiKey,
        llm_provider: llmProvider,
        user_brief: userBrief || undefined,
        tech_stack: techStack || undefined,
        test_route: testRoute || undefined,
        auth_username: authUsername || undefined,
        auth_password: authPassword || undefined
      })
      setActiveScan({ id: result.id, url: normalizedUrl })
      navigate(`/scan/${result.id}`)
    } catch (err) {
      setError('Failed to start scan. Please check your inputs and try again.')
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      <div>
        <label htmlFor="url" className="block text-sm font-medium text-gray-700 mb-1">
          URL to scan
        </label>
        <input
          type="url"
          id="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://your-app.com"
          required
          className="w-full px-4 py-3 text-lg border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
        />
        </div>

      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showAuth}
            onChange={(e) => setShowAuth(e.target.checked)}
            className="w-4 h-4 text-green-600 rounded focus:ring-green-500"
          />
          <span className="text-sm font-medium text-gray-900">Requires user log in or authentication</span>
        </label>
        {showAuth && (
          <div className="space-y-3 mt-3 pt-3 border-t border-gray-200">
            <div>
              <label htmlFor="authUsername" className="block text-sm font-medium text-gray-700 mb-1">
                Email / Username
              </label>
              <input
                type="text"
                id="authUsername"
                value={authUsername}
                onChange={(e) => setAuthUsername(e.target.value)}
                placeholder="user@example.com"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
              />
            </div>
            <div>
              <label htmlFor="authPassword" className="block text-sm font-medium text-gray-700 mb-1">
                Password
              </label>
              <input
                type="password"
                id="authPassword"
                value={authPassword}
                onChange={(e) => setAuthPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
              />
            </div>
            <p className="text-xs text-gray-600">
              🔒 Credentials are used only for this scan and never stored.
            </p>
          </div>
        )}
      </div>

      <div>
        <label htmlFor="apiKey" className="block text-sm font-medium text-gray-700 mb-1">
          API Key
        </label>
        <input
          type="password"
          id="apiKey"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="Your Gemini or Claude API key"
          required
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
        />
        <p className="mt-1 text-sm text-gray-500">
          Your key is used only for this scan and never stored.{' '}
          <span className="text-gray-600">
            Get one from{' '}
            <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer" className="text-green-700 underline hover:text-green-800">
              Google AI Studio
            </a>
            {' '}or{' '}
            <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener noreferrer" className="text-green-700 underline hover:text-green-800">
              Anthropic Console
            </a>
          </span>
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
              checked={llmProvider === 'gemini'}
              onChange={(e) => setLlmProvider(e.target.value)}
              className="mr-2"
            />
            Gemini
          </label>
          <label className="flex items-center">
            <input
              type="radio"
              value="claude"
              checked={llmProvider === 'claude'}
              onChange={(e) => setLlmProvider(e.target.value)}
              className="mr-2"
            />
            Claude
          </label>
        </div>
      </div>

      <button
        type="button"
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
      >
        <svg className={`w-4 h-4 transition-transform ${showAdvanced ? 'rotate-90' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        Advanced options
      </button>

      {showAdvanced && (
        <div className="space-y-4 pl-4 border-l-2 border-gray-100">
          <div>
            <label htmlFor="brief" className="block text-sm font-medium text-gray-700 mb-1">
              Brief / Instructions (optional)
            </label>
            <textarea
              id="brief"
              value={userBrief}
              onChange={(e) => setUserBrief(e.target.value)}
              placeholder="Tell GoNoGo about your project — what it does, who it's for, what to focus on..."
              rows={3}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
            />
          </div>

          <div>
            <label htmlFor="techStack" className="block text-sm font-medium text-gray-700 mb-1">
              Tech Stack (optional)
            </label>
            <input
              type="text"
              id="techStack"
              value={techStack}
              onChange={(e) => setTechStack(e.target.value)}
              placeholder="e.g., Next.js, Tailwind, Supabase"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
            />
          </div>

          <div>
            <label htmlFor="testRoute" className="block text-sm font-medium text-gray-700 mb-1">
              Test Route (optional)
            </label>
            <input
              type="text"
              id="testRoute"
              value={testRoute}
              onChange={(e) => setTestRoute(e.target.value)}
              placeholder="e.g., test the checkout flow"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
            />
            <p className="mt-1 text-sm text-gray-500">
              Tell GoNoGo to focus on a specific user flow.
            </p>
          </div>
        </div>
      )}

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full py-4 px-6 bg-green-700 hover:bg-green-800 disabled:bg-green-400 text-white text-lg font-semibold rounded-lg transition-colors"
      >
        {isSubmitting ? 'Starting scan...' : 'Run GoNoGo'}
      </button>
    </form>
  )
}
