import React from 'react'
import ReactDOM from 'react-dom/client'
import { Provider } from 'react-redux'
import App from './App.jsx'
import { store } from './store/store'
import './locales/i18n'
import 'bootstrap/dist/css/bootstrap-grid.min.css'
import 'bootstrap/dist/css/bootstrap-utilities.min.css'
import './index.css'

// When a lazy-loaded chunk 404s (stale service worker serving old index.html
// after a new deploy), reload once to let the new SW serve the correct files.
window.addEventListener('unhandledrejection', (event) => {
  const msg = event.reason?.message ?? ''
  if (
    event.reason?.name === 'ChunkLoadError' ||
    /dynamically imported module/.test(msg) ||
    /Loading chunk \d+ failed/.test(msg)
  ) {
    const key = 'swaya_chunk_reload'
    if (!sessionStorage.getItem(key)) {
      sessionStorage.setItem(key, '1')
      window.location.reload()
    }
  }
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Provider store={store}>
      <App />
    </Provider>
  </React.StrictMode>,
)
