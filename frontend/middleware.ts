import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const sessionToken = request.cookies.get('session_token')?.value;

  // Routes excluded from customer auth checks:
  // - /login (customer login page — handled separately below)
  // - /admin/* (admin pages use their own client-side localStorage auth)
  // - /api/* (API routes handle their own auth via backend JWT verification)
  const isLoginPage = pathname === '/login';
  const isAdminRoute = pathname.startsWith('/admin');
  const isApiRoute = pathname.startsWith('/api');

  // Allow admin routes through — they use existing client-side adminToken check
  if (isAdminRoute || isApiRoute) {
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

  // session_token exists — allow through (backend validates JWT on API calls)
  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder assets (svg, png, jpg, jpeg, gif, webp)
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
