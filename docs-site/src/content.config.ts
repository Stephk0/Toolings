import { defineCollection, z } from 'astro:content';
import { docsLoader } from '@astrojs/starlight/loaders';
import { docsSchema } from '@astrojs/starlight/schema';

const toolSchema = z.object({
  name: z.string(),
  version: z.string(),
  status: z.enum(['active', 'maintenance', 'beta', 'experimental']).default('active'),
  category: z.enum([
    'Export',
    'Modeling',
    'Animation',
    'Modifiers',
    'UV/Materials',
    'Rigging',
    'Workflow',
    'Compositor',
  ]),
  blenderVersion: z.string().default('4.5+'),
  author: z.string().default('Stephan Viranyi'),
  downloadUrl: z.string().optional(),
  sourcePath: z.string().optional(),
  summary: z.string().optional(),
  detailLevel: z.enum(['detailed', 'stub']).default('stub'),
});

export const collections = {
  docs: defineCollection({
    loader: docsLoader(),
    schema: docsSchema({
      extend: z.object({
        tool: toolSchema.optional(),
      }),
    }),
  }),
};
