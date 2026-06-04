# Tool image assets

One folder per tool, matching the slug used in `src/content/docs/tools/<slug>.mdx`.

## Expected filenames

The MDX pages reference filenames in the `<div class="ui-todo">` TODO blocks. Replacing those blocks with `<img>` or `<Image>` should use these conventions per tool:

| Tool | Expected images |
|---|---|
| `mass-exporter/` | `panel.png`, `header.png`, `viewport-example.png` |
| `edge-constraint-mode/` | `header.png`, `before-after.png` |
| `tile-uv-projector/` | `panel.png`, `preview-vs-applied.png` |
| `anim-layers-quick-export/` | `panel.png`, `nla-before.png` |
| `quick-animation-export/` | `panel.png`, `output-folder.png` |
| `skin-transfer-setup/` | `panel.png` |
| `modifier-list-stephko/` | `list-view.png` |
| `synced-modifiers/` | `panel.png` |
| `compositor-render-sets/` | `panel.png` |
| `add-bounds-to-name/` | `panel.png` |

## How to reference

In a tool MDX page:

```mdx
import { Image } from 'astro:assets';
import panel from '../../../assets/tools/mass-exporter/panel.png';

<Image src={panel} alt="Mass Exporter N-panel" />
```

Astro will optimize the image at build time. PNG screenshots from Blender work as-is.

## Conventions

- **N-panel screenshots** — capture only the panel (Edit → Preferences → Add-ons → choose theme; turn off scrollbars if possible). Target width ~500px.
- **Viewport screenshots** — capture the 3D View at 16:9 with a neutral world background. Include the tool's relevant context (selected geometry, header toggles).
- **Before/after** — composite a single image side-by-side rather than two separate files; it reads better inline.
- **Naming** — kebab-case, no version numbers in the filename (the page's frontmatter holds the version).
