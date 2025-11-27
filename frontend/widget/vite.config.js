import { defineConfig } from 'vite';
import preact from '@preact/preset-vite';
import cssInjectedByJsPlugin from 'vite-plugin-css-injected-by-js';
export default defineConfig({
  plugins: [preact(), cssInjectedByJsPlugin()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: undefined,
        entryFileNames: 'bizdnaii-widget.js',
        format: 'iife',
        name: 'BizDNAiiWidget'
      },
    },
  },
  define: { 'process.env': {} }
});
