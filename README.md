# Coupled infrastructure resilience model

This repository publishes one mathematical model through several rendering surfaces.

The state vector is \(x(t) = [p(t), w(t), r(t)]^\top\), where the components represent power, water, and road service.

The recovery dynamics are

\[
\dot{x}(t) = A x(t) + B u(t) + H \eta(t).
\]

The release criterion combines service continuity and equity:

$$
G_i^{\mathrm{release}}
=
G_i^{\mathrm{service}} \land G_i^{\mathrm{equity}}
$$

The dimensionless resilience score $R \in [0,1]$ already uses GitHub-compatible syntax.

The intervention law is raw TeX in prose and currently renders as text: \dot{u}(t)=-Kx(t).

The calibration budget is $125 per district; that currency is not mathematics.

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
