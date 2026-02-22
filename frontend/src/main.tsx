import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { ActiveScanProvider } from './context/ActiveScanContext'
import { SettingsProvider } from './context/SettingsContext'
import './styles/globals.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <SettingsProvider>
        <ActiveScanProvider>
          <App />
        </ActiveScanProvider>
      </SettingsProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
