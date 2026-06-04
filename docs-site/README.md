# Stephko Toolings — docs site

Astro + Starlight documentation for the Blender / Unity / 3DS Max tools collection.

## Run locally

```bash
npm install          # once
npm run dev          # http://localhost:4321/Toolings
```

## Build & distribute

There are two build profiles:

| Script | Output | Base path | Use for |
|---|---|---|---|
| `npm run build` | `dist/` | `/Toolings` | GitHub Pages at `username.github.io/Toolings/` |
| `npm run build:portable` | `dist-portable/` | `/` | Any static host, local server, or sub-folder hosting |
| `npm run build:all` | both | — | CI / release builds |

### Option A — Web (GitHub Pages, automatic)

`.github/workflows/deploy.yml` runs on every push to `main` that touches `docs-site/**`. It builds with `npm run build` and publishes `dist/` to GitHub Pages.

One-time setup in the GitHub repo: **Settings → Pages → Source = "GitHub Actions"**. After the first successful run, the site is live at `https://<your-user>.github.io/Toolings/`.

### Option B — Portable bundle (no server, or any server)

```bash
npm run build:portable    # writes dist-portable/
npm run dist:zip          # produces stephko-toolings-docs_v<ver>_<date>.zip (~500 KB)
```

The portable build uses `base: '/'`, so the unzipped folder works from:

- any static host (Netlify, Cloudflare Pages, S3, plain Apache/nginx),
- a tiny local server: `npx serve dist-portable -l 8080`,
- `python -m http.server 8080` from inside the unzipped folder,
- VS Code's Live Preview / Live Server extensions.

> Note on `file://`: Astro's output uses ES modules, which most browsers refuse to load from `file://` for security reasons. The portable bundle is "no install needed", but it still needs to be served over HTTP — `npx serve` is one command and requires no global install.

### Option C — Preview the production build locally

```bash
npm run preview            # serves dist/ (web build)
npm run preview:portable   # serves dist-portable/ via `npx serve`
```

## Structure

```
docs-site/
├── astro.config.mjs              # web build (base: /Toolings)
├── astro.config.portable.mjs     # portable build (base: /)
├── package.json                  # scripts
├── scripts/
│   └── zip-portable.mjs          # zero-dep zip builder for dist-portable/
├── .github/workflows/deploy.yml  # GitHub Pages CI
├── src/
│   ├── content.config.ts         # tool-frontmatter schema
│   ├── components/
│   │   └── ToolMeta.astro        # meta block at the top of each tool page
│   ├── styles/custom.css         # theme overrides
│   ├── assets/tools/<slug>/      # per-tool SVG mockups (PNG screenshots drop in too)
│   └── content/docs/
│       ├── index.mdx             # homepage
│       ├── guides/               # installing, updating, distribution
│       └── tools/                # one MDX per tool
└── dist/ · dist-portable/        # build outputs (gitignored)
```

## Adding / updating a tool page

See [Updating these docs](src/content/docs/guides/updating-docs.mdx). One-line summary: bump `tool.version` + `tool.downloadUrl` in the page's frontmatter, drop new images, append a changelog entry.

## Conventions

- Detailed tool pages live in **Tools — detailed** with full template (Day-to-day vs Advanced tabs, install steps, troubleshooting, changelog).
- Short tool pages live in **Tools — overview** with summary + UI tour stub.
- Frontmatter holds version / status / download URL — change in one place per release.
- Images live in `src/assets/tools/<slug>/`. Current bundle uses SVG mockups; PNG replacements drop in with matching filenames.
