import { defineConfig } from '@playwright/test';
import * as dotenv from 'dotenv';

// .env.local takes priority over .env when present (for local debug URL overrides)
dotenv.config({ path: '.env.local', override: true });
dotenv.config();

const baseURL = process.env.BASE_URL ?? 'https://fa-api.nkn.tw';
const isLocalhost = /^https?:\/\/localhost|^https?:\/\/127\.0\.0\.1/.test(baseURL);

export default defineConfig({
  globalSetup: './global-setup.ts',
  testDir: './tests',
  // API tests are prone to data races when run in parallel; serial execution prioritizes stability.
  // Once stable, enable fullyParallel: true and increase workers for speed.
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }], ['json', { outputFile: 'test-results/report.json' }]],
  timeout: 30_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL,
    extraHTTPHeaders: { Accept: 'application/json' },
    trace: 'retain-on-failure',
  },
  // For localhost: wait until the server launched by the VSCode debugger is ready.
  // If the server is already running, the command is skipped (reuseExistingServer).
  // When using compound launch, polls for up to 30 seconds before timing out.
  webServer: isLocalhost
    ? {
        command: 'sleep infinity',
        url: `${baseURL}/int/docs`,
        reuseExistingServer: true,
        timeout: 30_000,
      }
    : undefined,
});
