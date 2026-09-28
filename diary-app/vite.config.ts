import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve, join } from 'path'
import fs from 'node:fs'
import { VitePWA } from 'vite-plugin-pwa'
// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      devOptions: {
        enabled: true,
        type: 'module',
      },
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'mask-icon.svg'],
      manifest: {
        name: 'Diary',
        short_name: 'Diary',
        theme_color: '#ffffff',
        icons: [
          { src: 'buch.png', sizes: '192x192', type: 'image/png' },
          { src: 'buch.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' }
        ]
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
        runtimeCaching: [
          {
            // Movie streams use byte ranges and should never be cached as API responses.
            urlPattern: /^\/api\/movies\/stream\/.*/i,
            handler: 'NetworkOnly'
          },
          {
            // Cache thumbnails and media served by the local backend.
            urlPattern: /^\/(files|media)\/.*/i,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'diary-images',
              expiration: {
                maxEntries: 1000,
                maxAgeSeconds: 30 * 24 * 60 * 60 // 30 Tage
              }
            }
          },
          {
            // Cacht deine Logs und JSONs (aus deinem /api/ Proxy)
            urlPattern: /^\/api\/.*/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'diary-api',
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 24 * 60 * 60 // 1 Tag
              }
            }
          }
        ]
      }
    }),
    // Dev-only: serve ../trips/* at /trips/*
    // and ../fitness/* at /fitness/*
    // 1. Wir definieren die Funktion als Konstante (außerhalb der hooks), damit TypeScript glücklich ist
    (() => {
      const setupMiddlewares = (middlewares: any) => {
        const tripsRoot = resolve(__dirname, '..', 'data', 'trips')
        const fitnessRoot = resolve(__dirname, '..', 'data', 'fitness')

        function serveDir(mount: string, rootDir: string) {
          middlewares.use(mount, (req: any, res: any, next: any) => {
            try {
              const url = (req.url ?? '/').split('?')[0]
              const rel = url.replace(/^\//, '')
              const filePath = join(rootDir, rel)

              if (!filePath.startsWith(rootDir)) {
                res.statusCode = 403
                res.end('Forbidden')
                return
              }

              if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
                res.statusCode = 404
                res.end('Not found')
                return
              }

              if (filePath.endsWith('.json')) res.setHeader('content-type', 'application/json; charset=utf-8')
              else if (filePath.endsWith('.md')) res.setHeader('content-type', 'text/markdown; charset=utf-8')
              else if (filePath.endsWith('.csv')) res.setHeader('content-type', 'text/csv; charset=utf-8')
              else if (filePath.endsWith('.gpx') || filePath.endsWith('.xml')) res.setHeader('content-type', 'application/xml; charset=utf-8')

              fs.createReadStream(filePath).pipe(res)
            } catch (e) {
              next(e)
            }
          })
        }

        serveDir('/trips', tripsRoot)
        serveDir('/fitness', fitnessRoot)
      };

      // 2. Wir geben das fertige Plugin-Objekt zurück
      return {
        name: 'serve-data-from-parent',
        configureServer(server: any) {
          setupMiddlewares(server.middlewares)
        },
        configurePreviewServer(server: any) {
          setupMiddlewares(server.middlewares)
        }
      };
    })()
  ],
  server: {
    fs: { allow: ['..'] },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8787',
        changeOrigin: true,
        timeout: 600000,
        proxyTimeout: 600000,
      },
      '/files': {
        target: 'http://127.0.0.1:8787',
        changeOrigin: true,
        timeout: 600000,
        proxyTimeout: 600000,
      },
      '/media': {
        target: 'http://127.0.0.1:8787',
        changeOrigin: true,
        timeout: 600000,
        proxyTimeout: 600000,
      }
    }
  },
  preview: {
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8787',
        changeOrigin: true,
      },
      '/files': {
        target: 'http://127.0.0.1:8787',
        changeOrigin: true,
      },
      '/media': {
        target: 'http://127.0.0.1:8787',
        changeOrigin: true,
      },
    }
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  base: './'
})
