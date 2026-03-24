import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'https://mcpress-chatbot-production.up.railway.app';

export async function GET() {
  try {
    const cookieStore = await cookies();
    const sessionToken = cookieStore.get('session_token')?.value;

    if (!sessionToken) {
      return NextResponse.json({ error: 'Authentication required' }, { status: 401 });
    }

    const backendResponse = await fetch(`${BACKEND_URL}/api/auth/usage`, {
      method: 'GET',
      headers: {
        'Cookie': `session_token=${sessionToken}`,
      },
    });

    const data = await backendResponse.json();
    return NextResponse.json(data, { status: backendResponse.status });
  } catch (error) {
    console.error('Usage proxy error:', error);
    return NextResponse.json({ error: 'Server error' }, { status: 500 });
  }
}
