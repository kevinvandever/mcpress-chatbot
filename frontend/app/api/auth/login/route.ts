import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const BACKEND_URL = process.env.VITE_API_URL || 'https://mcpress-chatbot-production.up.railway.app';

export async function POST(request: Request) {
  try {
    const body = await request.json();

    // Proxy to Railway backend
    const backendResponse = await fetch(`${BACKEND_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const data = await backendResponse.json();

    // If login succeeded and backend returned a token, set it as an HTTP-only cookie
    if (backendResponse.ok && data.token) {
      const cookieStore = await cookies();
      cookieStore.set('session_token', data.token, {
        httpOnly: true,
        secure: true,
        sameSite: 'lax',
        path: '/',
        maxAge: 3600, // 1 hour
      });
    }

    // Forward the response body and status code to the client
    return NextResponse.json(data, { status: backendResponse.status });
  } catch (error) {
    console.error('Login proxy error:', error);
    return NextResponse.json(
      { success: false, error: 'Server error' },
      { status: 500 }
    );
  }
}
