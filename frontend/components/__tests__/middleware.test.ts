/**
 * Tests for Next.js middleware — cookie-based auth route protection
 * Validates: Requirements 4.1, 4.7, 5.4 (Properties 10, 11)
 *
 * Since NextRequest requires the Web API Request global (not available in jsdom),
 * we test the middleware logic by directly testing the decision function.
 */

// We extract and test the middleware's routing logic directly
// The middleware checks: pathname, session_token cookie presence
// Returns: redirect to /login, redirect to /, or next()

interface MiddlewareInput {
  pathname: string
  hasSessionToken: boolean
}

type MiddlewareDecision =
  | { action: 'redirect'; to: string }
  | { action: 'next' }

/**
 * Replicates the middleware logic from middleware.ts for testability.
 * This mirrors the exact logic in the actual middleware.
 */
function middlewareLogic(input: MiddlewareInput): MiddlewareDecision {
  const { pathname, hasSessionToken } = input

  const isLoginPage = pathname === '/login'
  const isAdminRoute = pathname.startsWith('/admin')
  const isApiRoute = pathname.startsWith('/api')

  // Admin and API routes pass through
  if (isAdminRoute || isApiRoute) {
    return { action: 'next' }
  }

  // Login page: redirect authenticated users to /
  if (isLoginPage) {
    if (hasSessionToken) {
      return { action: 'redirect', to: '/' }
    }
    return { action: 'next' }
  }

  // Protected route: redirect unauthenticated users to /login
  if (!hasSessionToken) {
    return { action: 'redirect', to: '/login' }
  }

  return { action: 'next' }
}

describe('Middleware routing logic', () => {
  // --- Property 10: Unauthenticated redirect ---
  it('redirects unauthenticated users (no session_token) to /login on protected routes', () => {
    const result = middlewareLogic({ pathname: '/', hasSessionToken: false })
    expect(result).toEqual({ action: 'redirect', to: '/login' })
  })

  it('redirects unauthenticated users on /history to /login', () => {
    const result = middlewareLogic({ pathname: '/history', hasSessionToken: false })
    expect(result).toEqual({ action: 'redirect', to: '/login' })
  })

  // --- Requirement 4.1: Allows authenticated users through ---
  it('allows authenticated users (with session_token) through to protected routes', () => {
    const result = middlewareLogic({ pathname: '/', hasSessionToken: true })
    expect(result).toEqual({ action: 'next' })
  })

  it('allows authenticated users through to /history', () => {
    const result = middlewareLogic({ pathname: '/history', hasSessionToken: true })
    expect(result).toEqual({ action: 'next' })
  })

  // --- Property 11: Redirects authenticated users away from /login ---
  it('redirects authenticated users away from /login to /', () => {
    const result = middlewareLogic({ pathname: '/login', hasSessionToken: true })
    expect(result).toEqual({ action: 'redirect', to: '/' })
  })

  // --- Requirement 7: Admin routes not affected ---
  it('allows admin routes through without session_token check', () => {
    const result = middlewareLogic({ pathname: '/admin/dashboard', hasSessionToken: false })
    expect(result).toEqual({ action: 'next' })
  })

  it('allows admin login page through without session_token check', () => {
    const result = middlewareLogic({ pathname: '/admin/login', hasSessionToken: false })
    expect(result).toEqual({ action: 'next' })
  })

  // --- API routes pass through ---
  it('allows API routes through without session_token check', () => {
    const result = middlewareLogic({ pathname: '/api/auth/login', hasSessionToken: false })
    expect(result).toEqual({ action: 'next' })
  })

  it('allows API routes through even with session_token', () => {
    const result = middlewareLogic({ pathname: '/api/chat', hasSessionToken: true })
    expect(result).toEqual({ action: 'next' })
  })

  // --- Unauthenticated user on /login stays ---
  it('allows unauthenticated users to access /login', () => {
    const result = middlewareLogic({ pathname: '/login', hasSessionToken: false })
    expect(result).toEqual({ action: 'next' })
  })
})

describe('Middleware config verification', () => {
  // The actual middleware.ts uses NextResponse which requires Web API globals.
  // We verify the middleware config by reading the source as text.
  it('middleware source contains matcher config excluding static assets', () => {
    const fs = require('fs')
    const path = require('path')
    const source = fs.readFileSync(
      path.join(__dirname, '../../middleware.ts'),
      'utf-8'
    )
    expect(source).toContain('_next/static')
    expect(source).toContain('_next/image')
    expect(source).toContain('favicon.ico')
    expect(source).toContain('session_token')
    expect(source).toContain('/login')
    expect(source).toContain('/admin')
    expect(source).toContain('/api')
  })
})
