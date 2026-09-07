# Mathematical Surface Engineering Demonstrator

[![Mathematics surface audit](https://github.com/Dossiya-SE/Math-Surface-Engineer-Demo/actions/workflows/math-surface-audit.yml/badge.svg?branch=main)](https://github.com/Dossiya-SE/Math-Surface-Engineer-Demo/actions/workflows/math-surface-audit.yml)
[![Latest release](https://img.shields.io/github/v/release/Dossiya-SE/Math-Surface-Engineer-Demo?display_name=tag&sort=semver)](https://github.com/Dossiya-SE/Math-Surface-Engineer-Demo/releases/latest)

A reproducible engineering demonstrator for **publishing, auditing, repairing, and regression-testing mathematical content across heterogeneous documentation renderers**.

The repository uses one coupled-infrastructure resilience model as a controlled mathematical fixture. The scientific contribution of this repository is the **cross-surface mathematics workflow**, not a claim that the fixture is a calibrated infrastructure model.

```text
mathematical source
→ surface-specific rendering
→ structural + semantic audit
→ repair at the source of truth
→ renderer validation
→ reviewed visual regression
→ release gate
```

## What this repository verifies

The same mathematical content is exercised across:

- GitHub Markdown;
- MDX;
- Quarto/Pandoc;
- LaTeX;
- Jupyter Markdown/MathJax;
- generated HTML.

The audit distinguishes mathematical content from ordinary text, code literals, currency, archived material, and generated outputs so that repairs do not silently mutate non-mathematical fixtures.

## Project navigation

| Destination | Purpose |
|---|---|
| [End-to-end demonstration](END_TO_END_DEMO.md) | Prompt, findings, repairs, verification evidence, and limitations |
| [Surface ownership contract](docs/MATH_SURFACE_OWNERSHIP.md) | Renderer boundaries, review responsibility, and release gate |
| [Model fixture](docs/model.md) | Additional GitHub Markdown formulas used by the gate |
| [Audit policy](.math-surface.json) | Included surfaces, exclusions, and governance requirements |
| [CI workflow](.github/workflows/math-surface-audit.yml) | Pinned structural, semantic, renderer, and visual checks |
| [Reviewed visual baseline](.github/math-surface/math-render.spec.mjs-snapshots/math-surface-linux.png) | Human-approved Chromium reference image |

## Controlled mathematical fixture

The state vector is $x(t) = [p(t), w(t), r(t)]^\top$, where the components represent power, water, and road service.

The recovery dynamics are

$$
\dot{x}(t) = A x(t) + B u(t) + H \eta(t).
$$

The release criterion combines service continuity and equity:

```math
G_i^{\mathrm{release}}
=
G_i^{\mathrm{service}} \land G_i^{\mathrm{equity}}
```

The dimensionless resilience score $R \in [0,1]$ already uses GitHub-compatible syntax.

The intervention law is $\dot{u}(t)=-Kx(t)$.

The calibration budget is \$125 per district; that currency is not mathematics.

Inline code such as `\(literal_api_token\)` and fenced examples must remain byte-identical:

```text
\[
not mathematics: preserve this fixture
\]
```

## Surface inventory

- `README.md` and `docs/*.md`: GitHub Markdown.
- `site/*.mdx`: MDX, with project-specific dollar-delimited math.
- `paper/*.qmd`: Quarto/Pandoc.
- `tex/*.tex`: LaTeX.
- `notebooks/*.ipynb`: Jupyter Markdown plus MathJax.
- `public/*.html`: generated HTML; repair its generator, not the output.
- `archive/*.md`: verbatim historical material.

## Renderer versions

The controlled environment currently pins **MathJax 4.1.3**, **KaTeX 0.18.4**, and **cmark-gfm 0.29.0.gfm.13** through the repository audit configuration rather than presenting renderer versions as project identity badges.

## Scientific boundary

Passing the mathematics-surface audit demonstrates that the configured documentation surfaces preserve the intended mathematical fixture under the repository's structural, semantic, renderer, and visual checks. It does **not** establish empirical validity of the coupled-infrastructure model itself.
