import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { dirname, join } from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'
import type { Plugin } from 'vite'

/**
 * maplibre-gl loads its tile/GeoJSON worker from a URL it derives with
 * `new URL('./maplibre-gl-worker.mjs', import.meta.url)`. Neither bundling path
 * preserves that: Vite's dep pre-bundling rewrites the base to
 * node_modules/.vite/deps/, and the production build inlines the library into
 * assets/index-*.js. Both leave the worker 404ing, and the failure is silent --
 * controls, attribution and the canvas all appear, but nothing is ever painted.
 *
 * So the two worker files are emitted verbatim at a fixed, unhashed path and the
 * app calls setWorkerUrl() to point at them. They must stay side by side: the
 * worker imports './maplibre-gl-shared.mjs' relatively. Copying from node_modules
 * at build time means the pair can never drift from the installed version.
 */
const MAPLIBRE_WORKER_DIR = 'maplibre'
const MAPLIBRE_WORKER_FILES = ['maplibre-gl-worker.mjs', 'maplibre-gl-shared.mjs']

function maplibreWorkerAssets(): Plugin {
  const require = createRequire(import.meta.url)
  const distDir = dirname(require.resolve('maplibre-gl/dist/maplibre-gl.mjs'))
  const read = (name: string) => readFileSync(join(distDir, name))

  return {
    name: 'maplibre-worker-assets',

    // Dev: serve the pair at the same path the built app will request.
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const name = MAPLIBRE_WORKER_FILES.find((file) =>
          req.url?.startsWith(`/${MAPLIBRE_WORKER_DIR}/${file}`),
        )
        if (!name) return next()
        res.setHeader('Content-Type', 'text/javascript; charset=utf-8')
        res.end(read(name))
      })
    },

    // Build: `fileName` rather than `name`, so the paths stay unhashed and adjacent.
    generateBundle() {
      for (const name of MAPLIBRE_WORKER_FILES) {
        this.emitFile({
          type: 'asset',
          fileName: `${MAPLIBRE_WORKER_DIR}/${name}`,
          source: read(name),
        })
      }
    },
  }
}

/**
 * The client never names a host: it fetches relative `/api/...` paths, which the
 * backend answers directly in production (it mounts `dist/` at `/`) and which the
 * dev server proxies here.
 *
 * The backend origin is configurable through VITE_API_PROXY_TARGET. The default is
 * port 8010, NOT the FastAPI-conventional 8000 -- that port is occupied by an
 * unrelated app on the dev machine. Run the backend with:
 *
 *   uvicorn main:app --port 8010 --reload
 *
 * and override with `VITE_API_PROXY_TARGET=http://127.0.0.1:9000 npm run dev` (or a
 * line in .env.local) if you put it somewhere else.
 */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8010'

  return {
    plugins: [react(), maplibreWorkerAssets()],
    build: {
      // maplibre-gl alone is ~1.2 MB unminified. It is one indivisible WebGL renderer,
      // so code-splitting it buys nothing; raise the threshold rather than warn on
      // every build about a number that cannot move.
      chunkSizeWarningLimit: 1600,
    },
    server: {
      port: Number(env.VITE_DEV_PORT || 5173),
      proxy: {
        '/api': { target, changeOrigin: true },
      },
    },
  }
})
