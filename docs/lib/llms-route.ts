import { notFound } from 'next/navigation';
import { getLLMText, getPageMarkdownUrl } from '@/lib/source';
import { getPathLocale } from '@/lib/i18n';

// Each fumadocs collection produces its own `LoaderOutput` generic,
// so we intentionally accept any source here — the runtime surface
// (`getPage`, `getPages`) is the same across all of them.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Source = any;

/**
 * Factory for the `/llms.mdx/<section>/[[...slug]]/route.ts` handler.
 * Each section re-uses this to serve raw markdown at a predictable URL
 * for the "Copy as Markdown" button.
 */
export function createLLMsRoute(source: Source) {
  async function GET(
    _req: Request,
    { params }: { params: Promise<{ slug?: string[]; lang?: string }> },
  ) {
    const resolvedParams = await params;
    const { slug } = resolvedParams;
    const locale = getPathLocale(resolvedParams);
    const page = source.getPage(slug?.slice(0, -1), locale);
    if (!page) notFound();

    return new Response(await getLLMText(page), {
      headers: { 'Content-Type': 'text/markdown' },
    });
  }

  function generateStaticParams() {
    const i18n = source._i18n;
    if (i18n) {
      return source.getPages(i18n.defaultLanguage).map((page: any) => ({
        slug: getPageMarkdownUrl(page, source).segments,
      }));
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return source.getPages().map((page: any) => ({
      slug: getPageMarkdownUrl(page, source).segments,
    }));
  }

  function generateLocalizedStaticParams() {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return source.getPages().map((page: any) => ({
      lang: page.locale,
      slug: getPageMarkdownUrl(page, source).segments,
    }));
  }

  return { GET, generateStaticParams, generateLocalizedStaticParams };
}
