import type { BaseLayoutProps } from "fumadocs-ui/layouts/shared";
import {
  BookOpen,
  Braces,
  FlaskConical,
  History,
} from "lucide-react";
import { appName, gitConfig } from "./shared";

// Nav items rendered in the middle column of the top nav, between the
// logo and the search bar. Exported so our custom header slot
// (`src/components/NavHeader`) can consume it; deliberately NOT
// passed via Fumadocs' `links` option, because that flow places text
// items on the far right of the header — we want the classic "Logo |
// Nav — — Search | Icons" layout (Tailwind / Next.js docs style) with
// the items aligned under the main content column.
//
export const navLinks = [
  {
    text: { en: "Docs", zh: "文档" },
    url: "/docs/cortex",
    activeBase: "/docs",
    icon: <BookOpen />,
  },
  {
    text: { en: "API Reference", zh: "API Reference" },
    url: "/api-reference",
    activeBase: "/api-reference",
    icon: <Braces />,
  },
  {
    text: { en: "Examples", zh: "样例" },
    url: "/examples",
    activeBase: "/examples",
    icon: <FlaskConical />,
  },
  {
    text: { en: "Changelog", zh: "变更" },
    url: "/changelog/cortex-2026",
    activeBase: "/changelog",
    icon: <History />,
  },
];

export function baseOptions(): BaseLayoutProps {
  return {
    nav: {
      title: (
        <span className="inline-flex items-center gap-2 font-semibold text-fd-foreground">
          <span
            aria-hidden="true"
            className="inline-flex size-6 items-center justify-center rounded-[4px] border border-fd-border bg-fd-muted text-[13px] font-semibold"
          >
            C
          </span>
          <span aria-label={appName}>cortex</span>
        </span>
      ),
      // NOTE: no `nav.children` here — the nav link strip is rendered
      // directly inside our custom header slot (`NavHeader`) so it
      // lands in the middle grid column, right under the main content.
      // Fumadocs would otherwise stash `children` next to `navTitle`
      // in the left cell, which is the wrong column.
    },
    githubUrl: `https://github.com/${gitConfig.user}/${gitConfig.repo}`,
    // `links` intentionally omitted — text items live in `navLinks`
    // (rendered by `NavHeader`); only the GitHub icon flows through
    // Fumadocs' `navItems` via `githubUrl`, and our header picks it
    // up from `useNotebookLayout().navItems`.
  };
}
