import createMiddleware from 'next-intl/middleware';
import { NextRequest, NextResponse } from 'next/server';

const intlMiddleware = createMiddleware({
  locales: ['en', 'ar'],
  defaultLocale: 'ar',
  localePrefix: 'as-needed'
});

export default function middleware(request: NextRequest) {
  const url = request.nextUrl;
  const lang = url.searchParams.get('lang');
  if (lang && (lang === 'ar' || lang === 'en')) {
    const response = NextResponse.redirect(new URL(`/${lang}${url.pathname}`, request.url));
    response.cookies.set('NEXT_LOCALE', lang);
    return response;
  }
  return intlMiddleware(request);
}

export const config = {
  matcher: ['/((?!api|_next|.*\\..*).*)']
};
