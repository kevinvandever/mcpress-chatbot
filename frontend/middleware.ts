import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  // Check if the request is for an admin route (except login)
  if (request.nextUrl.pathname.startsWith('/admin') && 
      !request.nextUrl.pathname.startsWith('/admin/login')) {
    
    // Check for auth token in cookies (we'll need to update the auth to use cookies for SSR)
    // For now, this is a placeholder - actual auth check happens client-side
    // In production, you'd want to verify the JWT here or use cookies
    
    // This middleware mainly serves to show the pattern
    // The actual protection happens in the AdminLayout component
  }

  return NextResponse.next();
}

export const config = {
  matcher: '/admin/:path*',
};