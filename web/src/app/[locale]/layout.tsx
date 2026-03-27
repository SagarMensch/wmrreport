import { NextIntlClientProvider } from 'next-intl';
import { getMessages, getTranslations } from 'next-intl/server';
import { notFound } from 'next/navigation';
import { routing } from '@/i18n/routing';
import '../globals.css';

export default async function LocaleLayout({
  children,
  params
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  
  if (!routing.locales.includes(locale as any)) {
    notFound();
  }
 
  const messages = await getMessages();
  
  const isArabic = locale === 'ar';
  
  return (
    <html lang={locale} dir={isArabic ? 'rtl' : 'ltr'} suppressHydrationWarning>
      <head>
        <title>BASIR - AL TASNIM</title>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link href="https://fonts.googleapis.com/css2?family=Amiri:ital,wght@0,400;0,700;1,400;1,700&family=Cinzel:wght@600&family=Cinzel+Decorative:wght@400;700&family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;0,700;1,300;1,400;1,500;1,600;1,700&family=Figtree:ital,wght@0,300..900;1,300..900&display=swap" rel="stylesheet" />
      </head>
      <body className="antialiased min-h-screen mashrabiya-bg text-text-primary bg-void" suppressHydrationWarning>
        <NextIntlClientProvider locale={locale} messages={messages}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
