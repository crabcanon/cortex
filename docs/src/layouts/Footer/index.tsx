import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { gitConfig } from "@/lib/shared";
import type { Locale } from "@/lib/i18n";
import styles from "./Footer.module.scss";

type LocalizedText = Record<Locale, string>;

type FooterLink = {
  label: LocalizedText;
  href: string;
};

type FooterColumn = {
  heading: LocalizedText;
  links: FooterLink[];
};

const COLUMNS: FooterColumn[] = [
  {
    heading: { en: "Documentation", zh: "文档" },
    links: [
      { label: { en: "Overview", zh: "概览" }, href: "/docs/cortex" },
      {
        label: { en: "Architecture", zh: "架构" },
        href: "/docs/cortex-architecture",
      },
      {
        label: { en: "Deployment", zh: "部署" },
        href: "/docs/cortex-deployment",
      },
    ],
  },
  {
    heading: { en: "API", zh: "API" },
    links: [
      {
        label: { en: "Reference Overview", zh: "参考概览" },
        href: "/api-reference",
      },
      {
        label: { en: "OpenAPI Surface", zh: "OpenAPI 接口" },
        href: "/api-reference/cortex-api",
      },
      {
        label: { en: "Changelog", zh: "变更记录" },
        href: "/changelog/cortex-2026",
      },
    ],
  },
  {
    heading: { en: "Examples", zh: "样例" },
    links: [
      { label: { en: "Example Index", zh: "样例索引" }, href: "/examples" },
      {
        label: { en: "Parse + Knowledge", zh: "解析 + 知识" },
        href: "/examples/parse-and-knowledge",
      },
      {
        label: { en: "Evaluation + Synthesis", zh: "评测 + 合成" },
        href: "/examples/evaluation-and-synthesis",
      },
    ],
  },
];

const FOOTER_COPY: Record<
  Locale,
  {
    tagline: string;
    star: string;
    copyright: string;
  }
> = {
  en: {
    tagline:
      "Vendor-neutral AI data and knowledge API platform for parsing, storage, knowledge graphs, evaluation, and synthesis.",
    star: "Star us on GitHub",
    copyright: "Apache 2.0 licensed.",
  },
  zh: {
    tagline:
      "面向 AI 原生应用的中立数据与知识 API 平台，覆盖解析、存储、知识图谱、评测与合成。",
    star: "在 GitHub 上收藏",
    copyright: "Apache 2.0 开源许可。",
  },
};

const isExternal = (href: string) => /^https?:\/\//i.test(href);

const text = (value: LocalizedText, locale: Locale) => value[locale];

const localHref = (href: string, locale: Locale) => {
  if (locale !== "zh" || isExternal(href)) return href;
  return href === "/" ? "/zh" : `/zh${href}`;
};

const GithubMark = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="currentColor"
    aria-hidden="true"
  >
    <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
  </svg>
);

const FooterLinkItem = ({
  link,
  locale,
}: {
  link: FooterLink;
  locale: Locale;
}) => {
  const external = isExternal(link.href);
  const href = localHref(link.href, locale);
  const content = (
    <>
      {text(link.label, locale)}
      {external ? (
        <ExternalLink className={styles.externalIcon} aria-hidden="true" />
      ) : null}
    </>
  );

  return (
    <li>
      {external ? (
        <a href={href} target="_blank" rel="noopener noreferrer">
          {content}
        </a>
      ) : (
        <Link href={href}>{content}</Link>
      )}
    </li>
  );
};

const Footer = ({ locale = "en" }: { locale?: Locale }) => {
  const copy = FOOTER_COPY[locale];

  return (
    <footer className={styles.footer}>
      <div className={styles.shell}>
        <div className={styles.inner}>
          <div className={styles.brand}>
            <span className={styles.logo}>cortex</span>
            <p className={styles.tagline}>{copy.tagline}</p>
            <a
              className={styles.starButton}
              href={`https://github.com/${gitConfig.user}/${gitConfig.repo}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              <GithubMark className={styles.starIcon} />
              <span>{copy.star}</span>
            </a>
            <span>
              &copy; {new Date().getFullYear()} Cortex. {copy.copyright}
            </span>
          </div>

          <nav className={styles.columns} aria-label="Footer">
            {COLUMNS.map((column) => (
              <div key={column.heading.en} className={styles.column}>
                <h4 className={styles.heading}>
                  {text(column.heading, locale)}
                </h4>
                <ul className={styles.list}>
                  {column.links.map((link) => (
                    <FooterLinkItem
                      key={link.label.en}
                      link={link}
                      locale={locale}
                    />
                  ))}
                </ul>
              </div>
            ))}
          </nav>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
