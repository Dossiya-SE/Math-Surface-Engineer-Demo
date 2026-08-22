import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { expect, test } from "@playwright/test";
import katex from "katex";

const require = createRequire(import.meta.url);
const fragmentsPath = process.env.MATH_FRAGMENTS || "math-fragments.json";
const fragments = JSON.parse(fs.readFileSync(fragmentsPath, "utf8"));
const katexCssPath = require.resolve("katex/dist/katex.min.css");
const katexCss = fs.readFileSync(katexCssPath, "utf8");
const katexBase = pathToFileURL(`${path.dirname(katexCssPath)}${path.sep}`).href;

test("mathematics is visible and exposes MathML", async ({ page }) => {
  const equations = fragments.map((record, index) => {
    const rendered = katex.renderToString(String(record.tex ?? ""), {
      displayMode: Boolean(record.display),
      output: "htmlAndMathml",
      strict: "error",
      throwOnError: true,
      trust: false,
    });
    return `<section data-index="${index}"><code>${record.path}:${record.line}</code>${rendered}</section>`;
  }).join("\n");
  await page.setContent(`<!doctype html>
    <html><head><meta charset="utf-8"><base href="${katexBase}">
    <style>${katexCss}
      body{margin:0;background:#fff;color:#111;font:16px system-ui,sans-serif}
      main{box-sizing:border-box;width:1200px;padding:32px}
      section{margin:0 0 24px;padding:16px;border:1px solid #d0d7de;border-radius:8px;overflow:auto}
      code{display:block;margin-bottom:12px;color:#57606a;font-size:12px}
    </style></head><body><main>${equations}</main></body></html>`);
  await page.evaluate(() => document.fonts.ready);
  await expect(page.locator(".katex")).toHaveCount(fragments.length);
  await expect(page.locator(".katex-mathml annotation[encoding='application/x-tex']"))
    .toHaveCount(fragments.length);
  await expect(page.locator("main")).toHaveScreenshot("math-surface.png");
});
