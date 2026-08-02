import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from 'tailwindcss'
import autoprefixer from 'autoprefixer'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      // We register the SW ourselves in main.jsx (with an explicit reload on
      // update) instead of the plugin's auto-injected script, which only
      // calls navigator.serviceWorker.register() and never reloads an
      // already-open tab — that's what forced a manual unregister+hard-
      // refresh after every deploy during development.
      injectRegister: false,
      // Only cache the app shell — API calls are never cached
      workbox: {
        maximumFileSizeToCacheInBytes: 8 * 1024 * 1024,
        globPatterns: ['**/*.{js,css,html,ico,svg,woff2}'],
        globIgnores: ['assets/help-screens/**'],
        runtimeCaching: [
          {
            // Google Fonts — cache-first, 1 year
            urlPattern: /^https:\/\/fonts\.(googleapis|gstatic)\.com\/.*/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'google-fonts',
              expiration: { maxEntries: 20, maxAgeSeconds: 365 * 24 * 60 * 60 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            // API — network only (never serve stale quiz state)
            urlPattern: /\/api\//,
            handler: 'NetworkOnly',
          },
        ],
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api\//, /^\/diag\.html$/],
      },
      manifest: {
        name: 'Swaya.me',
        short_name: 'Swaya',
        description: 'Live quizzes, polls, and tests — one room, every voice.',
        start_url: '/',
        scope: '/',
        display: 'standalone',
        orientation: 'portrait-primary',
        theme_color: '#6366F1',
        background_color: '#F8FAFC',
        icons: [
          { src: '/android-chrome-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: '/android-chrome-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
          { src: '/apple-touch-icon.png',       sizes: '180x180', type: 'image/png' },
        ],
        shortcuts: [
          {
            name: 'Join a session',
            short_name: 'Join',
            description: 'Enter a join code and participate',
            url: '/join',
            icons: [{ src: '/favicon-48x48.png', sizes: '48x48' }],
          },
          {
            name: 'My activities',
            short_name: 'Activities',
            description: 'View and run your activities',
            url: '/activities',
            icons: [{ src: '/favicon-48x48.png', sizes: '48x48' }],
          },
        ],
      },
    }),
  ],
  css: {
    postcss: {
      plugins: [
        tailwindcss({
          content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
          corePlugins: { preflight: false },
          theme: { extend: {} },
        }),
        autoprefixer,
      ],
    },
  },
  build: {
    // Vite's default (empty the out dir first, then write) creates a real
    // window where sw.js and index.html briefly don't exist on disk at all —
    // any service-worker update check that lands in that window gets a 404
    // and gives up until its next scheduled retry. Writing files in place
    // instead removes that window; hashed asset chunks just accumulate
    // across rebuilds in this dev environment as a result (fine — they're
    // harmless clutter, not a correctness issue, and can be swept
    // periodically if it matters).
    emptyOutDir: false,
    rollupOptions: {
      output: {
        entryFileNames: 'assets/[name]-[hash].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
      }
    }
  }
})
