import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const proxyTarget = env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8080'
  const devPort = Number(env.VITE_PORT || 5173)
  const agentProxyTarget = env.VITE_AGENT_PROXY_TARGET || 'http://127.0.0.1:8787'
  const sensorProxyTarget = env.VITE_SENSOR_PROXY_TARGET || 'http://127.0.0.1:5000'
  const faceProxyTarget = env.VITE_FACE_PROXY_TARGET || 'http://127.0.0.1:5001'

  return {
    base: '/',
    plugins: [
      vue(),
      vueDevTools(),
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      },
      extensions: ['.js', '.ts', '.vue', '.json'],
    },
    server: {
      host: '0.0.0.0',
      port: devPort,
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, '')
        },
        '/agent-api': {
          target: agentProxyTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/agent-api/, '')
        },
        '/sensor-api': {
          target: sensorProxyTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/sensor-api/, '/api')
        },
        '/sensor-chart': {
          target: sensorProxyTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/sensor-chart/, '/chart')
        },
        '/face-api': {
          target: faceProxyTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/face-api/, '')
        }
      }
    }
  }
})
