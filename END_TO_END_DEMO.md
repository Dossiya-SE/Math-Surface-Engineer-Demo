# Engineer Mathematics Surfaces: end-to-end demonstration

## Realistic user prompt

> Our research repository renders equations correctly in LaTeX and Quarto, but several formulas appear as raw text or broken headings on GitHub. Audit every documentation surface, repair only confirmed GitHub Markdown defects without changing the mathematics, prove semantic and structural preservation, and install a CI gate that prevents regressions. Preserve code examples, currency, notebooks, generated HTML, and archival quotations.

## Audited snapshot

- Exact local fixture baseline: `ca2029c660b3bfd3b55736b638cd26828c0f18f8`; published GitHub baseline: `b1ed6901a80d84a85cbf21317f735eb54913b082`.
- Repair engine: `engineer-math-surfaces 1.2.0`; final governance and verification gate: `engineer-math-surfaces 1.3.0`.
- Declared surfaces: GitHub Markdown, MDX, Quarto, LaTeX, Jupyter, generated HTML, and archival Markdown.
- Baseline scanner scope: five tracked Markdown/MDX files. Final governance scan: seven Markdown/MDX files, with non-ignored untracked-file inventory coverage. Native non-Markdown surfaces were validated separately where their engine was available.

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
| Scanner regression suite | PASS in CI | 25 of 25 deterministic tests, including untracked inventory, `MSM010` body preservation, and cmark integration |
| Automatic semantic preservation | PASS for recorded spans | Four legacy TeX bodies retain ledger SHA-256 digests |
| Collision-body preservation | PASS independently | Pre/post TeX-body SHA-256 values match: `f4dfc991f907c9a891657cc914ccd39252d8d201e2e41b709ee1a667e865ea72` |
| Archive preservation | PASS | Whole-file pre/post SHA-256 values match: `468a1ed7e239f91ac801cb98de98993aa8caf6e1bb6f639ec408c3669756f449` |
| Formula extraction | PASS | Ten intended formulas, including the governance equation; no code or currency fragments |
| LaTeX engine | PASS | `pdflatex` completed after the declared dependency repair |
| Quarto source via Pandoc | PASS, limited | Pandoc emitted two MathML nodes; the Quarto CLI itself was unavailable |
| Notebook via Pandoc | PASS, limited | Notebook JSON parsed and Pandoc emitted two MathML nodes |
| `cmark-gfm` structural parity | PASS in CI | Pinned `cmark-gfm` preserved 59 normalized README nodes and 11 `docs/model.md` nodes |
| MathJax 4 + KaTeX strict validation | PASS in CI | Exact-pinned MathJax 4.1.3 and KaTeX 0.18.4 accepted all ten extracted formulas with zero failures |
| MDX compiler | UNINSPECTED | No project MDX compiler was available in the fixture |
| Actual GitHub rendering | PASS | Hosted README exposes five accessible GitHub math trees; code examples and literal currency remain prose/code |
| Visual regression | PASS | Pinned Chromium rendered all ten formulas; the CI-generated candidate was visually reviewed for legibility and clipping, then committed as the enforced baseline |

The advanced-gate bootstrap is retained in [GitHub Actions run 32602376752](https://github.com/Dossiya-SE/Math-Surface-Engineer-Demo/actions/runs/32602376752). After adding the approved README navigation, [GitHub Actions run 32603225170](https://github.com/Dossiya-SE/Math-Surface-Engineer-Demo/actions/runs/32603225170) generated the refreshed visual candidate with artifact digest `sha256:53b4bb8d7d825964fb01d4802a5f06bf508def5bcc097a65017e126353e435eb`; the reviewed current PNG is `sha256:367ff7dc8fe1d3945412f65ecace3efda35010459ed03f9cc64958148834fbf1`.

## Release decision

The requested GitHub Markdown repair is **approved**: semantic, normalized structural, dual-renderer, hosted-rendering, and visual gates all pass. Broader cross-surface certification remains explicitly partial because the fixture has no MDX compiler and the native Quarto CLI was unavailable; those gaps are not relabeled as successes.

## Installed governance

- `.math-surface.json`: surface and exclusion policy.
- `.github/math-surface/math_surface.py`: deterministic audit, repair, and extraction engine.
- `.github/math-surface/validate_renderers.mjs`: pinned MathJax 4 and KaTeX validator.
- `.github/math-surface/validate_gfm_structure.py`: GFM structural comparison gate.
- `.github/math-surface/fixtures/pre-repair-README.txt`: immutable historical source fixture; `structural-oracle-README.txt`: the approved navigation/badge structure expressed with the legacy math containers for normalized parity testing.
- `.github/math-surface/test_math_surface.py`: 25 deterministic regression tests.
- `.github/math-surface/package.json`: exact renderer/test dependency pins.
- `.github/math-surface/playwright.config.mjs` and `math-render.spec.mjs`: controlled visual and embedded-MathML regression fixture.
- `.github/math-surface/math-render.spec.mjs-snapshots/math-surface-linux.png`: human-reviewed Chromium reference image.
- `.github/workflows/math-surface-audit.yml`: pinned cmark build, repaired-document structural parity, SARIF, audit, extraction, dual-renderer enforcement, regression tests, retained artifacts, and enforced visual regression.

## Limitations exposed by the exercise

1. The original repair ledger was produced by version 1.2.0 and did not record the `MSM010` dollar-display body, so this demonstration used an independent hash plus exact pre-repair fixtures. Version 1.3.0 now records and tests both sides of that preservation invariant for future repairs.
2. Formula extraction conservatively paired two unescaped currency amounts. Making currency explicit with escaped dollar signs removed the ambiguity.
3. The scanner intentionally audits Markdown and MDX only; Quarto, LaTeX, notebooks, generated HTML, and live GitHub output require their own adapters and engines.
4. Native Quarto and project-specific MDX compilation remain outside the available fixture toolchain and are reported as limited or uninspected rather than inferred.
