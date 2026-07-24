import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import * as compiler from '@vue/compiler-sfc';

export default defineConfig({
  plugins: [vue({ compiler })],
  server: {
    port: 5173
  }
});
