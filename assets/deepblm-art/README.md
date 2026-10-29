# DeepBLM optical art

Five original geometric/material illustrations for the DeepBLM workbench. They are decorative visual metaphors, not customer imagery, business evidence, generated strategy analysis, photographs or Apple assets.

- `insight.webp`: prism and optical lens — understanding the starting point.
- `strategy.webp`: orbital nodes — connected strategic choices.
- `execution.webp`: layered steps — turning choices into action.
- `foundation.webp`: balanced columns and a supporting ring — leadership and shared values.
- `review.webp`: document planes and a lens — review and revision.

Each deployed image is 1600 × 1000, encoded as WebP. The application loads only same-origin raster files; no image-generation API, third-party CDN, external font or additional browser dependency is used. SVG sources in `svg/` are original scripted compositions for reproducibility, not user content, and are not inserted into the application DOM.

## Rebuild (optional, not needed to serve the site)

The generator renders SVG at 2× with Chromium, then downsamples and encodes with Pillow. Use a Python environment with Playwright and an interpreter with Pillow:

```sh
# WSL default encoder interpreter: /usr/bin/python3
.venv/bin/python scripts/render-deepblm-art.py
# Alternative Pillow environment:
DEEPBLM_PIL_PYTHON=/path/to/python-with-pillow .venv/bin/python scripts/render-deepblm-art.py
# Regenerate vector sources only, without either image dependency:
python scripts/render-deepblm-art.py --svg-only
```

Temporary renders use `TMPDIR` when set and are cleaned after encoding. Re-rendering requires the local Chromium installation; no network is needed during generation. The website itself has no build step and never executes this generator.

The Node tests check actual WebP headers, file budgets, local SVG source safety and five-group mapping. The real-browser studio suite checks decoded dimensions, semantic step mapping, image-error fallback and forced-colors/reduced-motion layouts. Decorative images have empty `alt` text and fixed dimensions; they never enter the planning draft, model payload or exported business document.

Design references (principles only, no Apple artwork or trademark copied):
- https://developer.apple.com/design/human-interface-guidelines/materials
- https://developer.apple.com/design/human-interface-guidelines/generative-ai
