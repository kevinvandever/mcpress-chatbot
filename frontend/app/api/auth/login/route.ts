import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

export async function POST(request: Request) {
  try {
    const { password } = await request.json();

    // Get demo password from environment variable
    const DEMO_PASSWORD = process.env.DEMO_PASSWORD || 'mcpress2024';

    // Debug logging (remove after testing)
    console.log('Password attempt length:', password?.length);
    console.log('Expected password length:', DEMO_PASSWORD?.length);
    console.log('Env var set?', !!process.env.DEMO_PASSWORD);

    // Simple password check
    if (password === DEMO_PASSWORD) {
      // Set HTTP-only cookie (more secure than localStorage)
      const cookieStore = await cookies();
      cookieStore.set('demo_auth', 'authenticated', {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        maxAge: 60 * 60 * 24 * 7, // 7 days
        path: '/',
      });

      return NextResponse.json({ success: true });
    } else {
      return NextResponse.json(
        { success: false, error: 'Invalid password' },
        { status: 401 }
      );
    }
  } catch (error) {
    return NextResponse.json(
      { success: false, error: 'Server error' },
      { status: 500 }
    );
  }
}
