import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const BACKEND_URL = process.env.VITE_API_URL || 'https://mcpress-chatbot-production.up.railway.app';

export async function POST() {
  try {
    const cookieStore = await cookies();
    const sessionToken = cookieStore.get('session_token')?.value;

    if (!sessionToken) {
      return NextResponse.json(
        { success: false, error: 'No session token provided' },
        { status: 401 }
      );
    }

    // Proxy to Railway backend, forwarding the session_token cookie
    const backendResponse = await fetch(`${BACKEND_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Cookie': `session_token=${sessionToken}`,
      },
    });

    const data = await backendResponse.json();

    // If refresh succeeded and backend returned a new token, update the cookie
    if (backendResponse.ok && data.token) {
      cookieStore.set('session_token', data.token, {
        httpOnly: true,
        secure: true,
        sameSite: 'lax',
        path: '/',
        maxAge: 3600,
      });
    }

    return NextResponse.json(data, { status: backendResponse.status });
  } catch (error) {
    console.error('Refresh proxy error:', error);
    return NextResponse.json(
      { success: false, error: 'Server error' },
      { status: 500 }
    );
  }
}
