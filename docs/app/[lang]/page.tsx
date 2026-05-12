import { redirect } from 'next/navigation';
import { defaultLocale, getPathLocale } from '@/lib/i18n';

export default async function LocaleHome({
  params,
}: {
  params: Promise<{ lang?: string }>;
}) {
  const locale = getPathLocale(await params);
  redirect(locale === defaultLocale ? '/docs/cortex' : `/${locale}/docs/cortex`);
}
