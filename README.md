# Mathematical Surface Engineering Demonstrator

[![Mathematics surface audit](https://github.com/Dossiya-SE/Math-Surface-Engineer-Demo/actions/workflows/math-surface-audit.yml/badge.svg?branch=main)](https://github.com/Dossiya-SE/Math-Surface-Engineer-Demo/actions/workflows/math-surface-audit.yml)
[![Latest release](https://img.shields.io/github/v/release/Dossiya-SE/Math-Surface-Engineer-Demo?display_name=tag&sort=semver)](https://github.com/Dossiya-SE/Math-Surface-Engineer-Demo/releases/latest)
[![MathJax 4.1.3](https://img.shields.io/badge/MathJax-4.1.3-0b7285)](.github/math-surface/package.json)
[![KaTeX 0.18.4](https://img.shields.io/badge/KaTeX-0.18.4-7950f2)](.github/math-surface/package.json)
[![cmark-gfm pinned](https://img.shields.io/badge/cmark--gfm-0.29.0.gfm.13-0969da)](.github/workflows/math-surface-audit.yml)

This repository demonstrates a reproducible audit, repair, verification, and regression-governance workflow for mathematical documentation across multiple rendering surfaces; the coupled-infrastructure equations below are a controlled mathematical fixture, not a claim of a calibrated infrastructure model.

## Project navigation

| Destination | Purpose |
|---|---|
| [End-to-end demonstration](END_TO_END_DEMO.md) | Prompt, findings, repairs, verification evidence, and limitations |
| [Surface ownership contract](docs/MATH_SURFACE_OWNERSHIP.md) | Renderer boundaries, review responsibility, and release gate |
| [Model fixture](docs/model.md) | Controlled mathematical formulas used by the cross-surface gate |
| [Audit policy](.math-surface.json) | Included surfaces, exclusions, and governance requirements |
| [CI workflow](.github/workflows/math-surface-audit.yml) | Pinned structural, semantic, renderer, and visual checks |
| [Reviewed visual baseline](.github/math-surface/math-render.spec.mjs-snapshots/math-surface-linux.png) | Human-approved Chromium reference image |

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