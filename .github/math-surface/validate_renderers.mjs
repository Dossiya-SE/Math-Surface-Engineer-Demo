#!/usr/bin/env node

import crypto from "node:crypto";
import fs from "node:fs";

const input = process.argv[2];
const requireMode = process.argv[3] || "available";
const modes = new Set(["available", "mathjax", "both"]);
if (!input || !modes.has(requireMode)) {
  console.error("Usage: validate_renderers.mjs FRAGMENTS.json [available|mathjax|both]");
  process.exit(2);
}

const records = JSON.parse(fs.readFileSync(input, "utf8"));
if (!Array.isArray(records)) {
  console.error("FRAGMENTS.json must contain an array.");
  process.exit(2);
}

let katex = null;
let mathjaxReady = false;

try {
  const module = await import("katex");
  katex = module.default || module;
} catch (_error) {
  console.error("KaTeX unavailable; install the project-pinned katex package.");
}

try {
  global.MathJax = {
    loader: {
      paths: { mathjax: "@mathjax/src/bundle" },
      load: ["adaptors/liteDOM"],
      require: (file) => import(file),
    },
    tex: {
      formatError(_jax, error) {
        throw error;
      },
    },
  };
  await import("@mathjax/src/bundle/tex-svg.js");
  await global.MathJax.startup.promise;
  mathjaxReady = true;
} catch (error) {
  console.error(`MathJax 4 unavailable: ${error.message}`);
}

if (!katex && !mathjaxReady) {
  process.exit(2);
}
if (requireMode === "mathjax" && !mathjaxReady) {
  process.exit(2);
}
if (requireMode === "both" && (!mathjaxReady || !katex)) {
  process.exit(2);
}

const results = [];
let failures = 0;
for (const record of records) {
  const tex = String(record.tex ?? "");
  const item = {
    path: record.path,
    line: record.line,
    display: Boolean(record.display),
    texSha256: crypto.createHash("sha256").update(tex, "utf8").digest("hex"),
    mathjax: "SKIPPED",
    katex: "SKIPPED",
  };
  if (mathjaxReady) {
    try {
      const node = await global.MathJax.tex2svgPromise(tex, {
        display: item.display,
        em: 16,
        ex: 8,
        containerWidth: 80 * 16,
      });
      const adaptor = global.MathJax.startup.adaptor;
      const svg = adaptor.tags(node, "svg")[0];
      if (!svg) {
        throw new Error("conversion produced no SVG node");
      }
      const output = adaptor.serializeXML(svg);
      if (/data-mjx-error|mjx-merror/i.test(output)) {
        throw new Error("conversion produced a MathJax error node");
      }
      item.mathjax = "PASS";
    } catch (error) {
      item.mathjax = `FAIL: ${error.message}`;
      failures += 1;
    }
  }
  if (katex) {
    try {
      katex.renderToString(tex, {
        displayMode: item.display,
        throwOnError: true,
        strict: "error",
        trust: false,
        output: "htmlAndMathml",
      });
      item.katex = "PASS";
    } catch (error) {
      item.katex = `FAIL: ${error.message}`;
      if (requireMode === "both") {
        failures += 1;
      }
    }
  }
  results.push(item);
}

console.log(JSON.stringify({
  formulas: records.length,
  requireMode,
  mathjaxAvailable: mathjaxReady,
  mathjaxVersion: mathjaxReady ? global.MathJax.version : null,
  katexAvailable: Boolean(katex),
  katexVersion: katex?.version ?? null,
  failures,
  results,
}, null, 2));

if (mathjaxReady && typeof global.MathJax.done === "function") {
  global.MathJax.done();
}
process.exit(failures ? 1 : 0);
