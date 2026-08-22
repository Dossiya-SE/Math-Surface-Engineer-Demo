# Engineer Mathematics Surfaces: end-to-end demonstration

## Realistic user prompt

> Our research repository renders equations correctly in LaTeX and Quarto, but several formulas appear as raw text or broken headings on GitHub. Audit every documentation surface, repair only confirmed GitHub Markdown defects without changing the mathematics, prove semantic and structural preservation, and install a CI gate that prevents regressions. Preserve code examples, currency, notebooks, generated HTML, and archival quotations.

## Audited snapshot

- Baseline commit: `ca2029c660b3bfd3b55736b638cd26828c0f18f8`
- Tool: `engineer-math-surfaces 1.2.0`
- Declared surfaces: GitHub Markdown, MDX, Quarto, LaTeX, Jupyter, generated HTML, and archival Markdown.
- Scanner scope: five tracked Markdown/MDX files. Native non-Markdown surfaces were validated separately where their engine was available.

## Baseline findings

| Rule | High confidence | Review | Meaning |
|---|---:|---:|---|
| `MSM001` | 2 | 1 | Legacy inline delimiter on GitHub Markdown; the review item is archival |
| `MSM002` | 2 | 0 | Legacy display delimiter on GitHub Markdown |
| `MSM003` | 0 | 1 | Raw TeX outside a recognized math container |
| `MSM010` | 1 | 0 | A standalone equality line can collide with GFM Setext parsing |
| **Total** | **5** | **2** | Seven findings in three files |

## Repairs

1. The deterministic fixer normalized two inline and two display legacy containers in active GitHub Markdown.
2. It replaced one collision-prone double-dollar display container with a fenced `math` block while preserving its TeX body byte-for-byte.
3. It did not change the raw prose formula. Authorial intent was inspected, then the complete expression was manually wrapped in a GitHub inline-math container.
4. It did not change the archival quotation. Its whole-file pre/post SHA-256 digest is identical.
5. Paired currency amounts were escaped so literal dollar signs cannot be misclassified as one long formula; rendered prose and monetary meaning are unchanged.
6. Native LaTeX compilation exposed a missing `amsmath` dependency for the norm command. The package was added without changing native LaTeX delimiters.

## Verification matrix

| Gate | Result | Evidence |
|---|---|---|
| Dry-run before apply | PASS | Complete deterministic patch inspected before mutation |
| Diff hygiene | PASS | `git diff --check` clean; complete diff inspected |
| Post-fix audit | PASS with one expected review item | Zero high-confidence findings and zero `MSM010`; archival item remains review-only |
| Scanner regression suite | PASS | 18 of 18 deterministic tests |
| Automatic semantic preservation | PASS for recorded spans | Four legacy TeX bodies retain ledger SHA-256 digests |
| Collision-body preservation | PASS independently | Pre/post TeX-body SHA-256 values match: `f4dfc991f907c9a891657cc914ccd39252d8d201e2e41b709ee1a667e865ea72` |
| Archive preservation | PASS | Whole-file pre/post SHA-256 values match: `468a1ed7e239f91ac801cb98de98993aa8caf6e1bb6f639ec408c3669756f449` |
| Formula extraction | PASS | Nine intended formulas; no code or currency fragments |
| LaTeX engine | PASS | `pdflatex` completed after the declared dependency repair |
| Quarto source via Pandoc | PASS, limited | Pandoc emitted two MathML nodes; the Quarto CLI itself was unavailable |
| Notebook via Pandoc | PASS, limited | Notebook JSON parsed and Pandoc emitted two MathML nodes |
| `cmark-gfm` structural parity | UNEXECUTED locally | Required executable was unavailable; this is not counted as a pass |
| MathJax 4 + KaTeX strict validation | UNEXECUTED locally | Exact packages could not be installed in the restricted local network; pinned CI gate is installed |
| MDX compiler | UNINSPECTED | No project MDX compiler was available in the fixture |
| Actual GitHub rendering | UNINSPECTED | Requires the hosted GitHub target |
| Visual regression | UNEXECUTED | A baseline must first be generated and reviewed in the pinned CI environment |

## Release decision

Local release is **blocked**, because the structural and dual-renderer gates are unexecuted. The repository is prepared to execute the missing gates in CI. This is an intentional rigorous outcome: unavailable evidence is not relabeled as success.

## Installed governance

- `.math-surface.json`: surface and exclusion policy.
- `.github/math-surface/math_surface.py`: deterministic audit, repair, and extraction engine.
- `.github/math-surface/validate_renderers.mjs`: pinned MathJax 4 and KaTeX validator.
- `.github/math-surface/validate_gfm_structure.py`: GFM structural comparison gate.
- `.github/math-surface/test_math_surface.py`: 18 deterministic regression tests.
- `.github/math-surface/package.json`: exact renderer/test dependency pins.
- `.github/math-surface/playwright.config.mjs` and `math-render.spec.mjs`: controlled visual and embedded-MathML regression fixture.
- `.github/workflows/math-surface-audit.yml`: SARIF, human audit, extraction, dual-renderer enforcement, regression tests, retained artifacts, and conditional visual regression.

## Limitations exposed by the exercise

1. The current provenance ledger records legacy-delimiter TeX bodies but does not record the `MSM010` dollar-display body. An independent hash was therefore required.
2. Formula extraction conservatively paired two unescaped currency amounts. Making currency explicit with escaped dollar signs removed the ambiguity.
3. The scanner intentionally audits Markdown and MDX only; Quarto, LaTeX, notebooks, generated HTML, and live GitHub output require their own adapters and engines.
