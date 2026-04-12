import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: [
      {
        find: '@prototype',
        replacement: path.resolve(__dirname, '../ordix-prototype.jsx')
      },
      {
        find: 'react/jsx-runtime',
        replacement: path.resolve(__dirname, './node_modules/react/jsx-runtime.js')
      },
      {
        find: 'react/jsx-dev-runtime',
        replacement: path.resolve(__dirname, './node_modules/react/jsx-dev-runtime.js')
      },
      {
        find: 'react-dom/client',
        replacement: path.resolve(__dirname, './node_modules/react-dom/client.js')
      },
      {
        find: 'react-dom',
        replacement: path.resolve(__dirname, './node_modules/react-dom/index.js')
      },
      {
        find: 'react',
        replacement: path.resolve(__dirname, './node_modules/react/index.js')
      },
      {
        find: 'lucide-react',
        replacement: path.resolve(__dirname, './node_modules/lucide-react/dist/esm/lucide-react.js')
      }
    ]
  },
  server: {
    fs: {
      allow: [path.resolve(__dirname, '..')]
    }
  }
});
