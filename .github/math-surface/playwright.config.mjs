import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: "math-render.spec.mjs",
  fullyParallel: false,
  retries: 0,
  workers: 1,
  use: {
    browserName: "chromium",
    colorScheme: "light",
    deviceScaleFactor: 1,
    locale: "en-US",
    reducedMotion: "reduce",
    timezoneId: "UTC",
    viewport: { width: 1280, height: 900 },
  },
  expect: {
    toHaveScreenshot: {
      animations: "disabled",
      caret: "hide",
      scale: "css",
    },
  },
});
