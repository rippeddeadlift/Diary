import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve, join } from 'path'
import fs from 'node:fs'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),

    // Dev-only: serve ../trips/* at /trips/*
    // and ../fitness/* at /fitness/*
    {
      name: 'serve-data-from-parent',
      configureServer(server) {
        const tripsRoot = resolve(__dirname, '..', 'trips')
        const fitnessRoot = resolve(__dirname, '..', 'fitness')

        function serveDir(mount: string, rootDir: string) {
          server.middlewares.use(mount, (req, res, next) => {
            try {
              const url = (req.url ?? '/').split('?')[0]
              const rel = url.replace(/^\//, '')
              const filePath = join(rootDir, rel)

              // Prevent path traversal
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

              // Minimal content-type handling
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
      }
    }
  ],
  server: {
    // Allow accessing parent folder during dev
    fs: { allow: ['..'] }
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  // In production build we want to host app/ and trips/ under the same root.
  // We'll copy dist -> ../app later.
  base: './'
})
