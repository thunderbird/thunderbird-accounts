import {fileURLToPath, URL} from 'node:url';
import {defineConfig, loadEnv} from 'vite';
import vue from '@vitejs/plugin-vue';

// https://vitejs.dev/config/
export default defineConfig(({mode}) => {
  // Load env file based on `mode` in the current working directory.
  const env = loadEnv(mode, process.cwd());

  // Build watch options
  const watch = {
    usePolling: env.VITE_SERVER_WATCH_POLLING === 'true'
  };
  if (env.VITE_SERVER_WATCH_INTERVAL) {
    watch.interval = Number(env.VITE_SERVER_WATCH_INTERVAL);
  }
  if (env.VITE_SERVER_WATCH_BINARY_INTERVAL) {
    watch.binaryInterval = Number(env.VITE_SERVER_WATCH_BINARY_INTERVAL);
  }

  return {
    base: "/static/",
    root: "./",
    plugins: [
      vue({
        script: {
          defineModel: true,
        },
      }),
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./assets/app/vue', import.meta.url)),
      },
      extensions: ['.ts', '.js', '.vue'],
    },
    server: {
      host: '0.0.0.0',
      watch: watch,
      // This is the "default" value, but when unspecified CORS seems to activate and get angry at me.
      cors: {origin: /^https?:\/\/(?:(?:[^:]+\.)?localhost|127\.0\.0\.1|\[::1\])(?::\d+)?$/},
    },
    build: {
      sourcemap: true,
      manifest: "manifest.json",
      outDir: './static/',
      emptyOutDir: false,
      rollupOptions: {
        input: {
          'app': 'assets/app/app.ts'
        },
        output: {
          entryFileNames: (assetInfo) => {
            console.log(assetInfo);
            return '[name]-[hash].js';
          },
          assetFileNames: "[name]-[hash].[ext]",
        }
      }
    },
  }
});
