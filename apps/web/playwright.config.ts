import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests', timeout: 120_000, workers: 1,
  use: { baseURL: 'http://127.0.0.1:5173', headless: true, channel: process.platform === 'win32' ? 'chrome' : undefined },
  webServer: { command: 'pnpm dev --host 127.0.0.1', url: 'http://127.0.0.1:5173', reuseExistingServer: !process.env.CI, timeout: 120_000 },
});
