import { Link } from 'react-router-dom'
import ScanForm from '../components/ScanForm'

export default function HomePage() {
  return (
    <div className="max-w-2xl mx-auto px-4 py-12">
      <div className="text-center mb-10">
        <h1 className="text-4xl font-bold text-gray-900 mb-3">
          Is your app ready to ship?
        </h1>
        <p className="text-xl text-gray-600">
          Get a GO / NO-GO verdict from an AI-powered QA agent.
        </p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <ScanForm />
      </div>

      <div className="mt-8 text-center">
        <Link to="/history" className="text-gray-500 hover:text-gray-700">
          View scan history
        </Link>
      </div>

      <div className="mt-12 grid grid-cols-3 gap-6 text-center">
        <div>
          <div className="text-3xl mb-2">7</div>
          <div className="text-sm text-gray-600">Quality Lenses</div>
        </div>
        <div>
          <div className="text-3xl mb-2">2</div>
          <div className="text-sm text-gray-600">Report Types</div>
        </div>
        <div>
          <div className="text-3xl mb-2">~5min</div>
          <div className="text-sm text-gray-600">Scan Time</div>
        </div>
      </div>

      <div className="mt-12 bg-gray-50 rounded-lg p-6">
        <h2 className="font-semibold text-gray-900 mb-4">What GoNoGo evaluates:</h2>
        <div className="grid grid-cols-2 gap-3 text-sm text-gray-600">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Functionality & Bugs
          </div>
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Design Quality
          </div>
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            User Experience
          </div>
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Performance
          </div>
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Accessibility
          </div>
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Code & Content
          </div>
        </div>
      </div>
    </div>
  )
}
