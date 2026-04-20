'use client';

import { useState, useEffect, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [failedRules, setFailedRules] = useState<string[]>([]);
  const [needsPasswordSetup, setNeedsPasswordSetup] = useState(false);
  const [loading, setLoading] = useState(false);
  const [checkingSession, setCheckingSession] = useState(true);
  const [showSubscriptionPrompt, setShowSubscriptionPrompt] = useState(false);
  const [subscriptionSignupUrl, setSubscriptionSignupUrl] = useState('');
  const router = useRouter();

  const passwordRules = [
    'At least 8 characters',
    'At least one uppercase letter',
    'At least one lowercase letter',
    'At least one digit',
    'At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)',
  ];

  // On mount, check if user already has a valid session
  useEffect(() => {
    const checkSession = async () => {
      try {
        const res = await fetch('/api/auth/me');
        if (res.ok) {
          router.push('/');
          return;
        }
      } catch {
        // Not authenticated, show login form
      } finally {
        setCheckingSession(false);
      }
    };
    checkSession();
  }, [router]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setFailedRules([]);
    setLoading(true);

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (response.ok) {
        const data = await response.json();
        // Check if free-tier user has exhausted questions
        if (data.subscription_status === 'free') {
          try {
            const usageRes = await fetch('/api/auth/usage');
            if (usageRes.ok) {
              const usageData = await usageRes.json();
              if (usageData.allowed === false) {
                setSubscriptionSignupUrl(usageData.signup_url || '');
                setShowSubscriptionPrompt(true);
                setLoading(false);
                return;
              }
            }
          } catch {
            // Usage check failed — let them through
          }
        }
        router.push('/');
        router.refresh();
        return;
      }

      const data = await response.json();

      switch (response.status) {
        case 400:
          // Password validation failed — show specific rule failures
          if (data.failed_rules && Array.isArray(data.failed_rules)) {
            setFailedRules(data.failed_rules);
            setNeedsPasswordSetup(true);
          } else {
            setError(data.error || 'Invalid request. Please check your input.');
          }
          break;
        case 401:
          setError('Invalid email or password.');
          break;
        case 429:
          setError('Too many login attempts. Please try again later.');
          break;
        case 503:
          setError('Subscription service temporarily unavailable. Please try again later.');
          break;
        default:
          setError('An unexpected error occurred. Please try again.');
      }
    } catch {
      setError('Network error. Please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  };

  // Show nothing while checking existing session
  if (checkingSession) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-gray-100">
        <div className="flex items-center space-x-2 text-gray-500">
          <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span>Checking session...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-gray-100">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-2xl shadow-xl">
        <div className="text-center">
          {/* MC ChatMaster Logo */}
          <img
            src="/mc-chatmaster-logo.png"
            alt="MC ChatMaster - Instant AI-Powered IBM i Expertise"
            className="mx-auto h-24 w-auto"
          />
          <p className="mt-4 text-sm text-gray-600">
            Sign in or create a free account to get started
          </p>
        </div>

        {/* Subscription required — free questions exhausted */}
        {showSubscriptionPrompt ? (
          <div className="space-y-6">
            <div className="rounded-lg bg-amber-50 border border-amber-200 p-5 text-center space-y-3">
              <p className="text-sm font-medium text-amber-800">
                You've used all your free questions.
              </p>
              <p className="text-sm text-amber-700">
                Subscribe to MC ChatMaster for unlimited access to AI-powered IBM i expertise.
              </p>
            </div>
            <a
              href={subscriptionSignupUrl || '#'}
              target="_blank"
              rel="noopener noreferrer"
              className="block w-full text-center py-3 px-4 text-sm font-medium rounded-lg text-white transition-all hover:scale-[1.02]"
              style={{ backgroundColor: 'var(--mc-blue, #0066CC)' }}
            >
              Subscribe Now
            </a>
            <button
              onClick={() => {
                setShowSubscriptionPrompt(false);
                router.push('/');
                router.refresh();
              }}
              className="block w-full text-center py-2 text-sm text-gray-500 hover:text-gray-700 transition-colors"
            >
              Continue to site anyway
            </button>
          </div>
        ) : (
        <>

        {/* First-time setup welcome message */}
        {needsPasswordSetup && (
          <div className="rounded-lg bg-blue-50 border border-blue-200 p-4 space-y-3">
            <p className="text-sm font-medium text-blue-800">
              Welcome! Create a password to secure your account.
            </p>
            <ul className="text-xs text-blue-700 space-y-1 list-disc list-inside">
              {passwordRules.map((rule) => (
                <li key={rule}>{rule}</li>
              ))}
            </ul>
          </div>
        )}

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                autoFocus
                className="appearance-none relative block w-full px-4 py-3 border border-gray-300 rounded-lg placeholder-gray-400 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent sm:text-sm"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  className="appearance-none relative block w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg placeholder-gray-400 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent sm:text-sm"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? (
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
                    </svg>
                  ) : (
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  )}
                </button>
              </div>
              <div className="mt-1 text-right">
                <Link
                  href="/forgot-password"
                  className="text-sm text-blue-600 hover:text-blue-800"
                >
                  Forgot Password?
                </Link>
              </div>
            </div>
          </div>

          {/* Generic error messages (401, 429, 503, network errors) */}
          {error && (
            <div className="rounded-lg bg-red-50 border border-red-200 p-4">
              <div className="flex items-center">
                <svg className="h-5 w-5 text-red-400 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <span className="text-sm text-red-800">{error}</span>
              </div>
            </div>
          )}

          {/* Password validation failures (400 with failed_rules) */}
          {failedRules.length > 0 && (
            <div className="rounded-lg bg-red-50 border border-red-200 p-4">
              <div className="flex items-start">
                <svg className="h-5 w-5 text-red-400 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <div>
                  <p className="text-sm font-medium text-red-800">Password does not meet requirements:</p>
                  <ul className="mt-1 text-sm text-red-700 list-disc list-inside">
                    {failedRules.map((rule) => (
                      <li key={rule}>{rule}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white transition-all transform hover:scale-[1.02] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
            style={{ backgroundColor: 'var(--mc-blue, #0066CC)' }}
          >
            {loading ? (
              <span className="flex items-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {needsPasswordSetup ? 'Creating Password...' : 'Signing in...'}
              </span>
            ) : (
              needsPasswordSetup ? 'Create Password' : 'Sign In'
            )}
          </button>
        </form>

        <div className="text-center space-y-2">
          <p className="text-xs text-gray-500">
            First time here? Just enter your email and choose a password.
          </p>
          <p className="text-xs text-gray-400">
            No subscription? No problem — try MC ChatMaster free with a limited number of questions.
          </p>
        </div>
        </>
        )}
      </div>
    </div>
  );
}
