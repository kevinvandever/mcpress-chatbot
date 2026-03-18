import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'https://mcpress-chatbot-production.up.railway.app';

export async function POST(request: Request) {
  try {
    const body = await request.json();

    // Proxy to Railway backend
    const backendResponse = await fetch(`${BACKEND_URL}/api/auth/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const data = await backendResponse.json();

    // Forward the response body and status code to the client
    return NextResponse.json(data, { status: backendResponse.status });
  } catch (error) {
    console.error('Reset password proxy error:', error);
    return NextResponse.json(
      { success: false, error: 'Server error' },
      { status: 500 }
    );
  }
}
