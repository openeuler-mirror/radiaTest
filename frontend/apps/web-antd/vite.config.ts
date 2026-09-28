import process from 'node:process';

import { defineConfig } from '@vben/vite-config';

const defaultEnv = {
  VITE_APP_NAMESPACE: 'kronos',
  VITE_APP_STORE_SECURE_KEY: 'kronos-local-store',
  VITE_APP_TITLE: 'radiaTest',
  VITE_ARCHIVER: 'false',
  VITE_BASE: '/',
  VITE_COMPRESS: 'none',
  VITE_GLOB_API_URL: '/api/v1',
  VITE_INJECT_APP_LOADING: 'true',
  VITE_NITRO_MOCK: 'false',
  VITE_PWA: 'false',
  VITE_ROUTER_HISTORY: 'hash',
};

for (const [key, value] of Object.entries(defaultEnv)) {
  process.env[key] ??= value;
}

export default defineConfig(async () => {
  return {
    application: {},
    vite: {},
  };
});
