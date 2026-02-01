import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'
// Desactivado temporalmente en GitHub Codespaces
// import { registerServiceWorker } from './utils/pwa'

// Registrar Service Worker para PWA (solo en producción)
// if (import.meta.env.PROD) {
//   registerServiceWorker();
// }

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
