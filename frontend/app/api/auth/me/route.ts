import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const BACKEND_URL = process.env.VITE_API_URL || 'https://mcpress-chatbot-production.up.railway.app';

export async function GET() {
  try {
    const cookieStore = await cookies();
    const sessionToken = cookieStore.get('session_token')?.value;

    if (!sessionToken) {
      return NextResponse.json(
        { detail: 'Invalid or expired token' },
        { status: 401 }
      );
    }

    // Proxy to Railway backend, forwarding the session_token cookie
    const backendResponse = await fetch(`${BACKEND_URL}/api/auth/me`, {
      method: 'GET',
      headers: {
        'Cookie': `session_token=${sessionToken}`,
      },
    });

    const data = await backendResponse.json();

    return NextResponse.json(data, { status: backendResponse.status });
  } catch (error) {
    console.error('Auth me proxy error:', error);
    return NextResponse.json(
      { detail: 'Server error' },
      { status: 500 }
    );
  }
}
