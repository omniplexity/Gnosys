import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    open: true,
    proxy: {
      '/api': 'http://127.0.0.1:8766'
    }
  },
  resolve: {
    alias: {
      '@gnosys/shared': path.resolve(__dirname, '../../packages/shared/src/index.ts')
    }
  }
});
