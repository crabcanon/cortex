"use client";

import * as Popover from "@radix-ui/react-popover";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";
import { buttonVariants } from "fumadocs-ui/components/ui/button";
import { twMerge } from "tailwind-merge";
import {
  getNavLinkText,
  isNavLinkActive,
  type NavLink,
} from "@/src/layouts/NavLinks";
import { getLocaleFromPathname, withLocalePrefix } from "@/lib/i18n";
import styles from "./NavMenu.module.scss";

export interface NavMenuProps {
  items: NavLink[];
}

const NavMenu: React.FC<NavMenuProps> = ({ items }) => {
  const pathname = usePathname();
  const locale = getLocaleFromPathname(pathname);

  return (
    <Popover.Root>
      <Popover.Trigger
        aria-label="Open navigation menu"
        className={twMerge(
          buttonVariants({ size: "icon-sm", color: "secondary" }),
          "text-fd-muted-foreground rounded-none",
          styles.trigger,
        )}
      >
        <Menu />
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align="end"
          sideOffset={8}
          collisionPadding={8}
          className={styles.content}
        >
          <ul className={styles.list}>
            {items.map((item) => {
              const active = isNavLinkActive(pathname, item);
              return (
                <li key={item.url}>
                  <Popover.Close asChild>
                    <Link
                      href={withLocalePrefix(item.url, locale)}
                      data-active={active}
                      className={styles.item}
                    >
                      <span className={styles.icon}>{item.icon}</span>
                      <span>{getNavLinkText(item, locale)}</span>
                    </Link>
                  </Popover.Close>
                </li>
              );
            })}
          </ul>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
};


export default NavMenu;
