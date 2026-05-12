import { isLocale } from './i18n';

export const appName = 'Cortex';

/**
 * Canonical public origin for the site. Single source of truth for
 * every absolute URL we emit (sitemap, robots, JSON-LD, `metadataBase`,
 * OG/image URLs, etc.) so a domain change only needs one edit.
 */
export const siteUrl = 'https://cortex.example.com';

/**
 * Site title used as the default `<title>` on routes that don't set
 * their own, and as the suffix in the root layout's title template
 * (`%s | {siteTitle}`). Kept verbatim from the old Docusaurus
 * `config.title` for SERP continuity.
 */
export const siteTitle =
  'Cortex - Vendor-neutral AI Data and Knowledge API Platform';

/**
 * Short meta-description used on the homepage and as the fallback for
 * pages without a frontmatter `description:` and no extractable body
 * paragraph.
 */
export const siteDescription =
  'Cortex unifies parsing, object storage, knowledge graphs, evaluation, and synthetic data workflows for AI-native applications.';

export const docsRoute = '/docs';
export const docsImageRoute = '/og/docs';

/**
 * Raw-markdown API route prefix for any section. We host a Next.js
 * route handler at `/llms.mdx/<section>/<slug>/content.md` for every
 * section that wants the "Copy as Markdown" button.
 *
 * Pass either a section name (`"docs"`) or a source's `baseUrl`
 * (`"/guides"`) — both work.
 */
export function contentRouteFor(sectionOrBaseUrl: string) {
  const parts = sectionOrBaseUrl.replace(/^\/+/, '').split('/').filter(Boolean);
  const locale = isLocale(parts[0]) ? parts.shift() : undefined;
  const section = parts[0];
  return `/llms.mdx/${locale ? `${locale}/` : ''}${section}`;
}

/** Back-compat alias. */
export const docsContentRoute = contentRouteFor('docs');

export const gitConfig = {
  user: 'crabcanon',
  repo: 'cortex',
  branch: 'main',
};

/** Community Discord invite — used by the `<DiscordButton>` CTA and
 *  referenced from the Kapa disclaimer copy. Single source of truth so
 *  rotating the invite is a one-line change. */
export const discordUrl = 'https://discord.gg/a3K9c8GRGt';

/**
 * Kapa.ai Ask-AI config. Values mirror what the old Docusaurus site
 * shipped (`old_deepeval_docs/docusaurus.config.ts`) but re-mapped to
 * the *current* Kapa widget API — several attribute names were
 * renamed in the 2024 refresh (see
 * https://docs.kapa.ai/integrations/website-widget/configuration/behavior
 * and `.../component-styles`). `websiteId` is the public Kapa project
 * identifier; safe to ship in client bundles.
 *
 * The widget is loaded with `data-launcher-button-hidden="true"` in
 * `app/layout.tsx` so Kapa's default floating launcher never renders;
 * every click on an element with class `triggerClass` opens the modal
 * via `data-modal-override-open-class`. `<AskAIButton>` applies that
 * class, so any button rendered through it doubles as a Kapa trigger
 * with no JS handler of our own.
 */
export const kapaConfig = {
  websiteId: 'a3177869-c654-4b86-9c92-e4b4416f66e0',
  projectName: 'Cortex',
  // Required by Kapa. Used as the modal accent / brand color.
  projectColor: '#ffffff',
  projectLogo:
    'https://pbs.twimg.com/profile_images/1888060560161574912/qbw1-_2g_400x400.png',
  modalTitle: 'Ask Cortex',
  chatDisclaimer:
    "All the following results are AI generated. If you can't find the solution you're looking for, check the Cortex documentation or project repository.",
  exampleQuestions:
    'How do I parse a URL?, How do I create a knowledge dataset?, How do I run an evaluation job?',
  uncertainAnswerCallout:
    'It may be better to confirm this answer against the Cortex API reference and source specs.',
  /**
   * Any element that carries this class opens the Kapa modal on click.
   * Stored as a bare class name (no leading dot) because Kapa's
   * `data-modal-override-open-class` expects the class name, not a
   * CSS selector.
   */
  triggerClass: 'ask-ai-trigger',
} as const;
