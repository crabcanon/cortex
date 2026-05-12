import { source } from '@/lib/source';
import { createFromSource } from 'fumadocs-core/search/server';

const cortexDocs = new Set([
  'cortex',
  'cortex-architecture',
  'cortex-deployment',
  'parse',
  'storage',
  'knowledge',
  'evaluation',
  'synthesis',
]);

const cortexOnlySource = {
  ...source,
  getPages: (...args: Parameters<typeof source.getPages>) =>
    source
      .getPages(...args)
      .filter((page) => cortexDocs.has(page.slugs[0] ?? '')),
};

export const { GET } = createFromSource(cortexOnlySource as typeof source, {
  // https://docs.orama.com/docs/orama-js/supported-languages
  language: 'english',
});
