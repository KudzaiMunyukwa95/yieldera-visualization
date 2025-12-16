import React from 'react'
import ReactDOM from 'react-dom/client'
import AutomatedVisualizationModule from './components/VisualizationModule.jsx'
import './index.css'

// Remove loading screen when React loads
document.body.classList.add('loaded');

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1>🌾 Yieldera Agricultural Intelligence Platform</h1>
          <p>Advanced satellite-based analysis for agricultural risk assessment</p>
        </div>
      </header>
      
      <main className="app-main">
        <AutomatedVisualizationModule 
          apiBaseUrl={import.meta.env.VITE_API_BASE_URL || '/api/v1'} 
        />
      </main>
      
      <footer className="app-footer">
        <p>
          Powered by Google Earth Engine • Developed by{' '}
          <a href="https://yieldera.com" target="_blank" rel="noopener noreferrer">
            Yieldera
          </a>
        </p>
      </footer>
    </div>
  </React.StrictMode>,
)
