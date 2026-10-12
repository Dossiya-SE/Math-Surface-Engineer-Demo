# Visual Governance

## Scope
This file governs scientific and technical visual communication in `Math-Surface-Engineer-Demo`. It does not change the repository's scientific claims, models, data, equations or evidence status.

## Invariants
- Canvas and panel interiors are white.
- No decorative gradients, shadows, textures, or decorative gold/yellow/amber/ochre accents.
- Light Sky Blue `#87CEFA` is the default account accent; Deep Sky Blue `#00BFFF` is reserved for stronger interactive emphasis.
- Additional colors require a declared scientific semantic role and a non-color cue.
- Arrows are used only for direction, causality, flow, dependency, feedback, exchange or sequence.
- Hierarchy, causality, interdependency, state evolution, geometry, quantitative evidence and transformation must use different visual grammars.
- Quantitative charts require correct scales, labels, units and uncertainty where material.
- Animation is permitted only for declared state/time evolution or mathematical transformation.
- Static SVG is the canonical README-safe representation; interactive behavior belongs on an executable web surface.
- Claim strength must not exceed evidence strength.

## Selection rule
```text
hierarchy         -> tree / dendrogram
causality         -> directed graph
interdependency   -> coupled or multilayer network
state evolution   -> trajectory / state space
geometry          -> mathematics-derived SVG / Canvas / WebGL
quantitative data -> scale-correct chart
transformation    -> mechanism-grounded animation
```

## Repository authority
Existing mathematical-rendering and artifact-verification controls remain authoritative.

## Completion gate
A new or revised visual is complete only when content semantics, geometry, accessibility, responsive rendering, color use, reduced-motion behavior where relevant, and README fallback have been checked.
