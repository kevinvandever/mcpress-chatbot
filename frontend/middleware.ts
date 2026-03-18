import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const sessionToken = request.cookies.get('session_token')?.value;

  const isLoginPage = pathname === '/login';
  const isPublicAuthPage = pathname === '/forgot-password' || pathname === '/reset-password';
  const isAdminRoute = pathname.startsWith('/admin');
  const isApiRoute = pathname.startsWith('/api');

  // Allow admin routes through — they use existing client-side adminToken check
  if (isAdminRoute || isApiRoute) {
    return NextResponse.next();
  }

  // Allow public auth pages (forgot-password, reset-password) without session
  if (isPublicAuthPage) {
    return NextResponse.next();
  }

  // If user is on /login and already has a session_token, redirect to /
  if (isLoginPage) {
    if (sessionToken) {
      return NextResponse.redirect(new URL('/', request.url));
    }
    return NextResponse.next();
  }

  // Protected route: if no session_token cookie, redirect to /login
  if (!sessionToken) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  // Add no-cache headers to prevent back button showing stale pages after logout
  const response = NextResponse.next();
  response.headers.set('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');
  response.headers.set('Pragma', 'no-cache');
  response.headers.set('Expires', '0');
  return response;
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
