import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  // Site-wide admin authentication - entire site requires admin login
  const isAdminLoginPage = request.nextUrl.pathname === '/admin/login';
  const isApiRoute = request.nextUrl.pathname.startsWith('/api');

  // Allow API routes and admin login page without authentication
  if (isApiRoute || isAdminLoginPage) {
    return NextResponse.next();
  }

  // Note: Middleware can't access localStorage, so we rely on client-side auth checks
  // and the axios interceptor to redirect if token is invalid.
  // The middleware just ensures the login page is accessible.

  // For now, allow all other routes through - client-side will handle auth
  // This prevents redirect loops since we can't check localStorage from middleware
  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};