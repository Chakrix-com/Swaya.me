import React from 'react'
import ReactDOM from 'react-dom/client'
import { Provider } from 'react-redux'
import App from './App.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'
import { store } from './store/store'
import './locales/i18n'
import 'bootstrap/dist/css/bootstrap-grid.min.css'
import 'bootstrap/dist/css/bootstrap-utilities.min.css'
import './index.css'
import { registerSW } from 'virtual:pwa-register'

// Auto-update the service worker and reload once it activates, instead of
// silently installing in the background and waiting for some future
// navigation to take over (the old default required manually unregistering
// the SW + hard-refreshing to see a new deploy).
//
// Two layers, deliberately redundant:
// 1. A raw serviceWorker.controllerchange listener — the lowest-level signal
//    the platform offers, fires whenever ANY new SW takes control, regardless
//    of vite-plugin-pwa's internal event wiring. This is the real safety net.
// 2. registerSW()'s own onNeedReload callback (the correct callback name for
//    registerType:'autoUpdate' — onNeedRefresh, used previously, is only
//    read in 'prompt' mode and was silently never called).
// 3. Active polling for a new SW every 15s, since this is a dev environment
//    where we rebuild far more often than the browser's own (throttled, up
//    to 24h) update check would ever notice on its own.
if ('serviceWorker' in navigator) {
  let reloaded = false
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (reloaded) return
    reloaded = true
    window.location.reload()
  })
}

registerSW({
  immediate: true,
  onRegisteredSW(_swUrl, registration) {
    if (!registration) return
    setInterval(() => registration.update(), 15000)
  },
  onNeedReload() {
    window.location.reload()
  },
})

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
    <ErrorBoundary>
      <Provider store={store}>
        <App />
      </Provider>
    </ErrorBoundary>
  </React.StrictMode>,
)
