import { Link } from 'react-router-dom'

export default function InstructionsPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">How to Use GoNoGo</h1>
        <p className="text-gray-600 mt-1">Everything you need to know to scan your app and run automated fixes.</p>
      </div>

      {/* Section 1: Overview */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-3">
        <h2 className="text-lg font-semibold text-gray-900">What is GoNoGo?</h2>
        <p className="text-gray-700 text-sm leading-relaxed">
          GoNoGo is an AI-powered QA agent that scans your web app and gives you a
          <strong> GO</strong>, <strong>NO-GO</strong>, or <strong>GO WITH CONDITIONS</strong> verdict.
          It evaluates functionality, design, UX, performance, accessibility, code quality, and security — then
          generates detailed reports with actionable findings.
        </p>
        <p className="text-gray-700 text-sm leading-relaxed">
          Optionally, GoNoGo can <strong>automatically fix</strong> the issues it finds using Claude Code,
          re-deploy, and rescan in a loop until your app passes.
        </p>
      </div>

      {/* Section 2: Running a Scan */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">Running a Scan</h2>
        <p className="text-sm text-gray-500">Works on the hosted version — no local setup required.</p>

        <ol className="space-y-3 text-sm text-gray-700">
          <li className="flex gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-green-100 text-green-700 flex items-center justify-center text-xs font-bold">1</span>
            <div>
              <strong>Configure your API key</strong> — Go to{' '}
              <Link to="/settings" className="text-green-700 underline hover:text-green-800">Settings</Link>{' '}
              and enter your Gemini or Claude API key. Select your preferred LLM provider.
            </div>
          </li>
          <li className="flex gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-green-100 text-green-700 flex items-center justify-center text-xs font-bold">2</span>
            <div>
              <strong>Start a new scan</strong> — Enter the URL of your deployed app. If the site requires login,
              check "Requires user log in" and provide credentials.
            </div>
          </li>
          <li className="flex gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-green-100 text-green-700 flex items-center justify-center text-xs font-bold">3</span>
            <div>
              <strong>Wait for results</strong> — GoNoGo crawls your site, takes screenshots, runs Lighthouse and
              axe audits, and evaluates across 7 quality lenses using AI. This typically takes 3-5 minutes.
            </div>
          </li>
          <li className="flex gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-green-100 text-green-700 flex items-center justify-center text-xs font-bold">4</span>
            <div>
              <strong>Review your verdict</strong> — Download Report A (AI handoff) or Report B (full review).
              Check the score breakdown and top 3 priority actions.
            </div>
          </li>
        </ol>

        <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
          <p className="text-xs text-gray-600">
            <strong>Tip:</strong> Use the Advanced Options to provide a brief about your project and tech stack.
            This helps GoNoGo tailor its evaluation to your specific context.
          </p>
        </div>
      </div>

      {/* Section 3: Fix Loop */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">Automated Fix Loop</h2>
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
          <p className="text-sm text-amber-800">
            The fix loop currently requires running the GoNoGo backend on your local machine.
            It needs direct filesystem access to your repository so Claude Code can edit files.
          </p>
        </div>

        <h3 className="text-sm font-semibold text-gray-900 mt-4">Prerequisites</h3>
        <ul className="space-y-2 text-sm text-gray-700">
          <li className="flex gap-2">
            <span className="text-green-600 flex-shrink-0">-</span>
            <div><strong>Python 3.10+</strong> installed on your machine</div>
          </li>
          <li className="flex gap-2">
            <span className="text-green-600 flex-shrink-0">-</span>
            <div><strong>Node.js 18+</strong> installed on your machine</div>
          </li>
          <li className="flex gap-2">
            <span className="text-green-600 flex-shrink-0">-</span>
            <div>
              <strong>Claude Code CLI</strong> — install with:{' '}
              <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs">npm install -g @anthropic-ai/claude-code</code>
            </div>
          </li>
          <li className="flex gap-2">
            <span className="text-green-600 flex-shrink-0">-</span>
            <div>
              <strong>Claude Code authentication</strong> — run{' '}
              <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs">claude login</code>{' '}
              to authenticate with your Anthropic account. Works with Max Pro subscriptions — no separate API key needed.
            </div>
          </li>
          <li className="flex gap-2">
            <span className="text-green-600 flex-shrink-0">-</span>
            <div><strong>Target repository</strong> cloned locally with a clean git working tree</div>
          </li>
        </ul>

        <h3 className="text-sm font-semibold text-gray-900 mt-4">Step-by-Step Setup</h3>
        <div className="bg-gray-900 rounded-lg p-4 space-y-4 text-sm font-mono">
          <div>
            <div className="text-gray-400 text-xs mb-1"># Terminal 1: Start the backend</div>
            <div className="text-green-400">cd F:\claude-code\claude_projects\gonogo\backend</div>
            <div className="text-green-400">pip install -r requirements.txt</div>
            <div className="text-green-400">playwright install chromium</div>
            <div className="text-green-400">python main.py</div>
          </div>
          <div>
            <div className="text-gray-400 text-xs mb-1"># Terminal 2: Start the frontend</div>
            <div className="text-green-400">cd F:\claude-code\claude_projects\gonogo\frontend</div>
            <div className="text-green-400">set VITE_API_URL=http://localhost:8000</div>
            <div className="text-green-400">npm run dev</div>
          </div>
        </div>

        <h3 className="text-sm font-semibold text-gray-900 mt-4">Running the Fix Loop</h3>
        <ol className="space-y-3 text-sm text-gray-700">
          <li className="flex gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-green-100 text-green-700 flex items-center justify-center text-xs font-bold">1</span>
            <div>Open <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs">http://localhost:5173</code> and run a scan.</div>
          </li>
          <li className="flex gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-green-100 text-green-700 flex items-center justify-center text-xs font-bold">2</span>
            <div>When results appear, scroll to the <strong>Automated Fix Loop</strong> section.</div>
          </li>
          <li className="flex gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-green-100 text-green-700 flex items-center justify-center text-xs font-bold">3</span>
            <div>
              Enter your <strong>local repository path</strong> (e.g., <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs">F:\projects\my-app</code>)
              and click <strong>Check</strong> to verify prerequisites.
            </div>
          </li>
          <li className="flex gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-green-100 text-green-700 flex items-center justify-center text-xs font-bold">4</span>
            <div>
              Configure your preferences — <strong>Git Branch</strong> mode is recommended for safe rollback.
              Select which severity levels to fix.
            </div>
          </li>
          <li className="flex gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-green-100 text-green-700 flex items-center justify-center text-xs font-bold">5</span>
            <div>Click <strong>Start Automated Fix Loop</strong>. Claude Code will read the findings, edit your code, and GoNoGo will rescan to verify.</div>
          </li>
        </ol>

        <h3 className="text-sm font-semibold text-gray-900 mt-4">Fix Loop Options Explained</h3>
        <div className="space-y-2 text-sm text-gray-700">
          <div className="grid grid-cols-[120px_1fr] gap-1">
            <span className="font-medium">Apply Mode</span>
            <span><strong>Git Branch</strong> (recommended) creates a new branch for fixes. <strong>Direct</strong> edits files in place with no safety net.</span>
          </div>
          <div className="grid grid-cols-[120px_1fr] gap-1">
            <span className="font-medium">Permission</span>
            <span><strong>Full</strong> lets Claude Code run any command. <strong>Cautious</strong> requires approval for bash commands.</span>
          </div>
          <div className="grid grid-cols-[120px_1fr] gap-1">
            <span className="font-medium">Deploy Mode</span>
            <span><strong>Preview</strong> auto-deploys with a custom command. <strong>Local</strong> uses your dev server. <strong>Manual</strong> pauses for you to deploy.</span>
          </div>
          <div className="grid grid-cols-[120px_1fr] gap-1">
            <span className="font-medium">Max Cycles</span>
            <span>How many scan-fix-rescan iterations to run (1-10).</span>
          </div>
          <div className="grid grid-cols-[120px_1fr] gap-1">
            <span className="font-medium">Stop Condition</span>
            <span>Stop early when a specific verdict is reached, run all cycles, or stop manually.</span>
          </div>
        </div>
      </div>

      {/* Section 4: Settings */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-3">
        <h2 className="text-lg font-semibold text-gray-900">Settings</h2>
        <p className="text-sm text-gray-700 leading-relaxed">
          The <Link to="/settings" className="text-green-700 underline hover:text-green-800">Settings page</Link>{' '}
          lets you save defaults that pre-fill across the app. Your API key, LLM provider, fix loop preferences,
          and scan defaults are stored locally in your browser — nothing is sent to a server.
        </p>
        <p className="text-sm text-gray-700 leading-relaxed">
          Values set in Settings are defaults only. You can override any value per-scan or per-fix-loop without
          changing your saved settings.
        </p>
      </div>

      {/* Section 5: Roadmap */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-3">
        <h2 className="text-lg font-semibold text-gray-900">Roadmap</h2>
        <ul className="space-y-2 text-sm text-gray-700">
          <li className="flex gap-2">
            <span className="text-gray-400 flex-shrink-0">-</span>
            <div><strong>Remote Fix Loop</strong> — Clone repos from GitHub directly on the server so the fix loop works without local setup.</div>
          </li>
          <li className="flex gap-2">
            <span className="text-gray-400 flex-shrink-0">-</span>
            <div><strong>Desktop App</strong> — Installable Electron app with built-in backend for seamless local scanning and fixing.</div>
          </li>
          <li className="flex gap-2">
            <span className="text-gray-400 flex-shrink-0">-</span>
            <div><strong>CLI Tool</strong> — Run GoNoGo from the terminal: <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs">npx gonogo scan https://mysite.com</code></div>
          </li>
          <li className="flex gap-2">
            <span className="text-gray-400 flex-shrink-0">-</span>
            <div><strong>CI/CD Integration</strong> — Run GoNoGo as a GitHub Action on every pull request.</div>
          </li>
        </ul>
      </div>
    </div>
  )
}
