export const defaultLocale = 'en';

export const locales = ['en', 'zh'] as const;

export type Locale = (typeof locales)[number];

export const localeItems = [
  { locale: 'zh', name: '中文' },
  { locale: 'en', name: 'English' },
] as const;

export const localeNames: Record<Locale, string> = {
  zh: '中文',
  en: 'English',
};

export const i18n = {
  languages: [...locales],
  defaultLanguage: defaultLocale,
  hideLocale: 'default-locale' as const,
};

export function isLocale(value: string | undefined): value is Locale {
  return locales.includes(value as Locale);
}

export function getLocaleFromPathname(pathname: string): Locale {
  const segment = pathname.split('/').filter(Boolean)[0];
  return isLocale(segment) ? segment : defaultLocale;
}

export function stripLocalePrefix(pathname: string): string {
  const parts = pathname.split('/').filter(Boolean);

  if (isLocale(parts[0])) {
    const stripped = `/${parts.slice(1).join('/')}`;
    return stripped === '/' ? '/' : stripped.replace(/\/$/, '') || '/';
  }

  return pathname || '/';
}

export function withLocalePrefix(pathname: string, locale: Locale): string {
  const stripped = stripLocalePrefix(pathname);
  if (locale === defaultLocale) return stripped;
  return `/${locale}${stripped === '/' ? '' : stripped}`;
}

export function getPathLocale(params?: { lang?: string }): Locale {
  return isLocale(params?.lang) ? params.lang : defaultLocale;
}
