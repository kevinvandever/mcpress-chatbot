import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'

// Mock next/navigation
const mockPush = jest.fn()
const mockRefresh = jest.fn()
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    refresh: mockRefresh,
  }),
}))

import LoginPage from '../../app/login/page'

// Helper: create a fetch mock that routes by URL
function setupFetchMock(routes: Record<string, { status: number; body?: any; ok?: boolean }>) {
  global.fetch = jest.fn((url: string) => {
    const route = Object.entries(routes).find(([key]) => url.includes(key))
    if (route) {
      const [, resp] = route
      return Promise.resolve({
        ok: resp.ok ?? (resp.status >= 200 && resp.status < 300),
        status: resp.status,
        json: () => Promise.resolve(resp.body ?? {}),
      })
    }
    return Promise.resolve({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ error: 'Not found' }),
    })
  }) as jest.Mock
}

async function renderAndWaitForForm() {
  render(<LoginPage />)
  await waitFor(() => {
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument()
  })
}

async function fillAndSubmitForm(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/email address/i), 'test@example.com')
  await user.type(screen.getByLabelText(/password/i), 'password123')
  await user.click(screen.getByRole('button', { name: /sign in/i }))
}

describe('LoginPage', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  afterEach(() => {
    jest.restoreAllMocks()
  })

  // --- Requirement 1.1: Login page renders email and password fields ---
  it('renders email and password input fields', async () => {
    setupFetchMock({ '/api/auth/me': { status: 401 } })
    await renderAndWaitForForm()

    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  // --- Requirement 1.5: Shows "Invalid email or password" on 401 ---
  it('shows "Invalid email or password" on 401 response', async () => {
    const user = userEvent.setup()
    setupFetchMock({
      '/api/auth/me': { status: 401 },
      '/api/auth/login': { status: 401, body: { success: false, error: 'Invalid email or password' } },
    })

    await renderAndWaitForForm()
    await fillAndSubmitForm(user)

    await waitFor(() => {
      expect(screen.getByText('Invalid email or password')).toBeInTheDocument()
    })
  })

  // --- Requirement 10.1, 10.2: Shows subscription message with "Subscribe Now" on 403 ---
  it('shows subscription-required message with "Subscribe Now" button on 403 response', async () => {
    const user = userEvent.setup()
    setupFetchMock({
      '/api/auth/me': { status: 401 },
      '/api/auth/login': {
        status: 403,
        body: {
          success: false,
          error: 'Your subscription has expired',
          subscription_status: 'expired',
          redirect_url: 'https://mcpress.com/subscribe',
        },
      },
    })

    await renderAndWaitForForm()
    await fillAndSubmitForm(user)

    await waitFor(() => {
      expect(screen.getByText('Your subscription has expired')).toBeInTheDocument()
    })
    const subscribeBtn = screen.getByText('Subscribe Now')
    expect(subscribeBtn).toBeInTheDocument()
    expect(subscribeBtn.closest('a')).toHaveAttribute('href', 'https://mcpress.com/subscribe')
    expect(subscribeBtn.closest('a')).toHaveAttribute('target', '_blank')
  })

  // --- Requirement 10.3: Shows correct status-specific messages ---
  it.each([
    ['expired', 'Your subscription has expired'],
    ['paused', 'Your subscription is paused'],
    ['cancelled', 'Your subscription has been cancelled'],
    ['not_found', 'No subscription found'],
  ])('shows correct message for %s subscription status', async (status, expectedMessage) => {
    const user = userEvent.setup()
    setupFetchMock({
      '/api/auth/me': { status: 401 },
      '/api/auth/login': {
        status: 403,
        body: {
          success: false,
          error: expectedMessage,
          subscription_status: status,
          redirect_url: 'https://mcpress.com/subscribe',
        },
      },
    })

    await renderAndWaitForForm()
    await fillAndSubmitForm(user)

    await waitFor(() => {
      expect(screen.getByText(expectedMessage)).toBeInTheDocument()
    })
  })

  // --- Requirement 10.2: "Subscribe Now" links to redirect_url, opens in new tab ---
  it('"Subscribe Now" button links to redirect_url and opens in new tab', async () => {
    const user = userEvent.setup()
    const redirectUrl = 'https://mcpress.com/subscribe-now'
    setupFetchMock({
      '/api/auth/me': { status: 401 },
      '/api/auth/login': {
        status: 403,
        body: {
          success: false,
          error: 'No subscription found',
          subscription_status: 'not_found',
          redirect_url: redirectUrl,
        },
      },
    })

    await renderAndWaitForForm()
    await fillAndSubmitForm(user)

    await waitFor(() => {
      expect(screen.getByText('Subscribe Now')).toBeInTheDocument()
    })

    const link = screen.getByText('Subscribe Now').closest('a')
    expect(link).toHaveAttribute('href', redirectUrl)
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'))
  })

  // --- Requirement 6.2: Shows rate limit message on 429 ---
  it('shows rate limit message on 429 response', async () => {
    const user = userEvent.setup()
    setupFetchMock({
      '/api/auth/me': { status: 401 },
      '/api/auth/login': {
        status: 429,
        body: { success: false, error: 'Too many login attempts. Please try again later.' },
      },
    })

    await renderAndWaitForForm()
    await fillAndSubmitForm(user)

    await waitFor(() => {
      expect(screen.getByText('Too many login attempts. Please try again later.')).toBeInTheDocument()
    })
  })

  // --- Requirement 9.1: Shows service unavailable message on 503 ---
  it('shows service unavailable message on 503 response', async () => {
    const user = userEvent.setup()
    setupFetchMock({
      '/api/auth/me': { status: 401 },
      '/api/auth/login': {
        status: 503,
        body: { success: false, error: 'Subscription service temporarily unavailable' },
      },
    })

    await renderAndWaitForForm()
    await fillAndSubmitForm(user)

    await waitFor(() => {
      expect(
        screen.getByText('Subscription service temporarily unavailable. Please try again later.')
      ).toBeInTheDocument()
    })
  })

  // --- Requirement 4.5: Shows loading spinner during API call ---
  it('shows loading spinner during API call', async () => {
    const user = userEvent.setup()

    // /api/auth/me returns 401 immediately, /api/auth/login hangs
    let resolveLogin!: (value: any) => void
    const loginPromise = new Promise((resolve) => { resolveLogin = resolve })

    global.fetch = jest.fn((url: string) => {
      if (typeof url === 'string' && url.includes('/api/auth/me')) {
        return Promise.resolve({
          ok: false,
          status: 401,
          json: () => Promise.resolve({}),
        })
      }
      return loginPromise
    }) as jest.Mock

    await renderAndWaitForForm()
    await fillAndSubmitForm(user)

    // While loading, the button should show "Signing in..."
    await waitFor(() => {
      expect(screen.getByText('Signing in...')).toBeInTheDocument()
    })

    // Resolve the login to clean up
    await act(async () => {
      resolveLogin({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ error: 'Invalid email or password' }),
      })
    })
  })

  // --- Requirement 4.7, Property 11: Redirects when user has valid session ---
  it('redirects to / when user already has valid session via /api/auth/me returning 200', async () => {
    setupFetchMock({
      '/api/auth/me': {
        status: 200,
        ok: true,
        body: { email: 'user@example.com', subscription_status: 'active' },
      },
    })

    render(<LoginPage />)

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/')
    })
  })

  // --- Requirement 4.2: Successful login redirects to / ---
  it('redirects to / on successful login', async () => {
    const user = userEvent.setup()
    setupFetchMock({
      '/api/auth/me': { status: 401 },
      '/api/auth/login': {
        status: 200,
        ok: true,
        body: { success: true, email: 'user@example.com', subscription_status: 'active' },
      },
    })

    await renderAndWaitForForm()
    await fillAndSubmitForm(user)

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/')
    })
  })
})
