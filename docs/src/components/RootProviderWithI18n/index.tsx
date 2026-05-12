"use client";

import { type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { RootProvider } from "fumadocs-ui/provider/next";
import {
  getLocaleFromPathname,
  localeItems,
  localeNames,
  withLocalePrefix,
  type Locale,
} from "@/lib/i18n";

const disabledSearchHotKey = [
  {
    key: "__disabled__",
    display: null,
  },
];

const translations: Record<Locale, Record<string, string>> = {
  en: {},
  zh: {
    search: "搜索文档",
    searchNoResult: "未找到结果",
    toc: "本页目录",
    tocNoHeadings: "暂无标题",
    lastUpdate: "最后更新",
    chooseLanguage: "选择语言",
    nextPage: "下一页",
    previousPage: "上一页",
    chooseTheme: "选择主题",
    editOnGithub: "在 GitHub 上编辑",
  },
};

type RootProviderWithI18nProps = {
  children: ReactNode;
};

const RootProviderWithI18n: React.FC<RootProviderWithI18nProps> = ({
  children,
}) => {
  const pathname = usePathname() || "/";
  const router = useRouter();
  const locale = getLocaleFromPathname(pathname);

  return (
    <RootProvider
      search={{ hotKey: disabledSearchHotKey }}
      i18n={{
        locale,
        locales: localeItems.map((item) => ({
          locale: item.locale,
          name: localeNames[item.locale],
        })),
        translations: translations[locale],
        onLocaleChange: (nextLocale) => {
          router.push(withLocalePrefix(pathname, nextLocale as Locale));
        },
      }}
    >
      {children}
    </RootProvider>
  );
};

export default RootProviderWithI18n;
