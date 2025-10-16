import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  // Check if user is authenticated (demo password protection)
  const authCookie = request.cookies.get('demo_auth');
  const isLoginPage = request.nextUrl.pathname === '/login';
  const isApiRoute = request.nextUrl.pathname.startsWith('/api');
  const isAdminRoute = request.nextUrl.pathname.startsWith('/admin');
  const isCodeAnalysisRoute = request.nextUrl.pathname.startsWith('/code-analysis');

  // Allow API routes, login page, admin routes, and code-analysis routes without demo auth
  // (admin routes and code-analysis have their own authentication via axios interceptor)
  if (isApiRoute || isLoginPage || isAdminRoute || isCodeAnalysisRoute) {
    return NextResponse.next();
  }

  // Redirect to login if not authenticated
  if (!authCookie || authCookie.value !== 'authenticated') {
    const loginUrl = new URL('/login', request.url);
    return NextResponse.redirect(loginUrl);
  }

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