'use client'

import { useState } from 'react'
import { trackEvent } from '../utils/analytics'

interface NewsletterCapturePromptProps {
  userEmail: string
  questionsUsed: number
  onDismiss: () => void
  onSignup: (email: string) => void
}

export default function NewsletterCapturePrompt({
  userEmail,
  questionsUsed,
  onDismiss,
  onSignup,
}: NewsletterCapturePromptProps) {
  const [email, setEmail] = useState(userEmail || '')

  const handleDismiss = () => {
    onDismiss()
    trackEvent('newsletter_dismissed', { questionsUsed })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) return
    onSignup(email.trim())
    trackEvent('newsletter_signup', { questionsUsed })
  }

  return (
    <div className="relative rounded-xl border border-gray-200 bg-white shadow-sm p-4">
      <button
        onClick={handleDismiss}
        className="absolute top-2 right-2 text-gray-400 hover:text-gray-600 transition-colors"
        aria-label="Dismiss newsletter prompt"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      <div className="pr-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-1">
          Join the MC Press Newsletter
        </h3>
        <p className="text-xs text-gray-600 mb-3">
          Get IBM i tips, new book announcements, and technical insights delivered to your inbox.
        </p>

        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
          <button
            type="submit"
            className="px-4 py-1.5 text-sm font-medium text-white rounded-lg transition-colors"
            style={{ backgroundColor: '#990000' }}
            onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#7a0000' }}
            onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#990000' }}
          >
            Subscribe
          </button>
        </form>
      </div>
    </div>
  )
}
