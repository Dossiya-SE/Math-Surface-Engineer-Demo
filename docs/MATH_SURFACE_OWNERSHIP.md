# Mathematics surface ownership

Each path has one rendering contract. A delimiter is evaluated against its owning surface, not against a universal Markdown rule.

| Path | Surface | Governing parser or renderer | Automatic GitHub rewrite |
|---|---|---|---|
| `README.md`, `docs/*.md` | GitHub Markdown | GFM host parser, then GitHub MathJax | High-confidence active spans only |
| `site/*.mdx` | MDX | Project MDX compiler and math plugin | Disabled; review manually |
| `paper/*.qmd` | Quarto | Pandoc/Quarto | Never |
| `tex/*.tex` | LaTeX | Declared TeX engine | Never |
| `notebooks/*.ipynb` | Jupyter notebook | Notebook Markdown and MathJax | Never from the Markdown fixer |
| `public/*.html` | Generated HTML | Source generator and browser renderer | Never; repair the generator |
| `archive/*.md` | Verbatim archive | Provenance-preserving text | Disabled unless explicitly authorized |

## Release rule

Release requires all four gates:

```math
G_{\mathrm{release}}
=
G_{\mathrm{syntax}}
\land G_{\mathrm{semantic}}
\land G_{\mathrm{render}}
\land G_{\mathrm{provenance}}.
```

An unavailable required engine is `UNEXECUTED`, never `PASS`.
