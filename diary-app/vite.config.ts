import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve, join } from 'path'
import fs from 'node:fs'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),

    // Dev-only: serve ../trips/* at /trips/*
    {
      name: 'serve-trips-from-parent',
      configureServer(server) {
        const tripsRoot = resolve(__dirname, '..', 'trips')

        server.middlewares.use('/trips', (req, res, next) => {
          try {
            const url = (req.url ?? '/').split('?')[0]
            const rel = url.replace(/^\//, '')
            const filePath = join(tripsRoot, rel)

            // Prevent path traversal
            if (!filePath.startsWith(tripsRoot)) {
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
            else if (filePath.endsWith('.gpx') || filePath.endsWith('.xml')) res.setHeader('content-type', 'application/xml; charset=utf-8')

            fs.createReadStream(filePath).pipe(res)
          } catch (e) {
            next(e)
          }
        })
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
