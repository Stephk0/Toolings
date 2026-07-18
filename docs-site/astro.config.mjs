import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  site: 'https://stephko.github.io',
  base: '/Toolings',
  integrations: [
    starlight({
      title: 'Stephko Toolings',
      description: 'Production-ready Blender, Unity, and 3DS Max tools by Stephan Viranyi.',
      social: {
        github: 'https://github.com/Stephk0/Toolings',
        linkedin: 'https://www.linkedin.com/in/stephanviranyi/',
      },
      sidebar: [
        {
          label: 'Start here',
          items: [
            { label: 'Overview', slug: 'index' },
            { label: 'Installing addons', slug: 'guides/installing' },
            { label: 'Hosting & distribution', slug: 'guides/distribution' },
            { label: 'Updating these docs', slug: 'guides/updating-docs' },
          ],
        },
        {
          label: 'Tools — detailed',
          items: [
            { label: 'Mass Exporter', slug: 'tools/mass-exporter' },
            { label: 'Edge Constraint Mode', slug: 'tools/edge-constraint-mode' },
            { label: 'Tile UV Projector', slug: 'tools/tile-uv-projector' },
            { label: 'Quick Animation Export', slug: 'tools/quick-animation-export' },
          ],
        },
        {
          label: 'Tools — overview',
          collapsed: true,
          items: [
            { label: 'Skin Transfer Setup', slug: 'tools/skin-transfer-setup' },
            { label: 'Modifier List Stephko', slug: 'tools/modifier-list-stephko' },
            { label: 'Synced Modifiers', slug: 'tools/synced-modifiers' },
            { label: 'Compositor Render Sets', slug: 'tools/compositor-render-sets' },
            { label: 'Add Bounds To Name', slug: 'tools/add-bounds-to-name' },
          ],
        },
      ],
      customCss: ['./src/styles/custom.css'],
      lastUpdated: true,
    }),
  ],
});
