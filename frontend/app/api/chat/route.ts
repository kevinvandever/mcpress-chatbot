import { cookies } from 'next/headers';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'https://mcpress-chatbot-production.up.railway.app';

export async function POST(request: Request) {
  try {
    const cookieStore = await cookies();
    const sessionToken = cookieStore.get('session_token')?.value;

    if (!sessionToken) {
      return new Response(JSON.stringify({ error: 'Authentication required' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const body = await request.json();

    const backendResponse = await fetch(`${BACKEND_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Cookie': `session_token=${sessionToken}`,
      },
      body: JSON.stringify(body),
    });

    // If not OK and not streaming, return the error as JSON
    if (!backendResponse.ok && backendResponse.headers.get('content-type')?.includes('application/json')) {
      const data = await backendResponse.json();
      return new Response(JSON.stringify(data), {
        status: backendResponse.status,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Stream the SSE response through
    if (!backendResponse.body) {
      return new Response(JSON.stringify({ error: 'No response body' }), {
        status: 502,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(backendResponse.body, {
      status: backendResponse.status,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });
  } catch (error) {
    console.error('Chat proxy error:', error);
    return new Response(JSON.stringify({ error: 'Server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
