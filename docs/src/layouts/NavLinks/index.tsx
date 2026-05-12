"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import {
  getLocaleFromPathname,
  stripLocalePrefix,
  withLocalePrefix,
  type Locale,
} from "@/lib/i18n";

export type NavLink = {
  text: string | Record<Locale, string>;
  url: string;
  activeBase?: string;
  match?: "nested-url" | "exact";
  icon?: ReactNode;
};

export interface NavLinksProps {
  items: NavLink[];
}

export const navLinksListClassName = "flex items-center gap-3";

export const navLinkClassName =
  "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[12px] text-fd-muted-foreground transition-colors hover:text-fd-accent-foreground [&_svg]:size-3.5 [&_svg]:shrink-0";

export function isNavLinkActive(pathname: string, item: NavLink) {
  const normalizedPathname = stripLocalePrefix(pathname);
  const matchUrl = item.activeBase ?? item.url;
  const mode = item.match ?? "nested-url";
  if (mode === "exact") return normalizedPathname === matchUrl;
  return (
    normalizedPathname === matchUrl ||
    normalizedPathname.startsWith(`${matchUrl}/`)
  );
}

export function getNavLinkText(item: NavLink, locale: Locale) {
  if (typeof item.text === "string") return item.text;
  return item.text[locale] ?? item.text.en;
}

type NavLinkItemProps = {
  item: NavLink;
  pathname: string;
};

export const NavLinkItem: React.FC<NavLinkItemProps> = ({ item, pathname }) => {
  const active = isNavLinkActive(pathname, item);
  const locale = getLocaleFromPathname(pathname);

  return (
    <li>
      <Link
        href={withLocalePrefix(item.url, locale)}
        data-active={active}
        className={navLinkClassName}
      >
        {item.icon}
        {getNavLinkText(item, locale)}
      </Link>
    </li>
  );
};

const NavLinks: React.FC<NavLinksProps> = ({ items }) => {
  const pathname = usePathname();

  return (
    <ul className={navLinksListClassName}>
      {items.map((item) => (
        <NavLinkItem key={item.url} item={item} pathname={pathname} />
      ))}
    </ul>
  );
};


export default NavLinks;
