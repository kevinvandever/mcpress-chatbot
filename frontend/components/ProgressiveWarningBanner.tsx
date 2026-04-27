'use client'

import { getWarningStage } from '../utils/warningStage'
import { trackEvent } from '../utils/analytics'

interface ProgressiveWarningBannerProps {
  questionsUsed: number
  questionsLimit: number
  isPQL: boolean
  signupUrl: string
  onUpgradeClick: () => void
  onSignIn: () => void
}

export default function ProgressiveWarningBanner({
  questionsUsed,
  questionsLimit,
  isPQL,
  signupUrl,
  onUpgradeClick,
  onSignIn,
}: ProgressiveWarningBannerProps) {
  const stage = getWarningStage(questionsUsed, questionsLimit)

  // silent and hardGate are not rendered by this component
  if (stage === 'silent' || stage === 'hardGate') return null

  const remaining = questionsLimit - questionsUsed

  const handleUpgradeClick = () => {
    onUpgradeClick()
    trackEvent('upgrade_click', { stage, isPQL })
    window.open(signupUrl, '_blank')
  }

  if (stage === 'soft') {
    return (
      <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 text-sm">
        <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span>
          You&apos;ve used {questionsUsed} of your {questionsLimit} free MC ChatMaster questions. You still have {remaining} left to explore the MC Press knowledge base.
        </span>
      </div>
    )
  }

  if (stage === 'stronger') {
    return (
      <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-sm">
        <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="font-medium">
          You have 1 free question remaining. Upgrade anytime for unlimited source-backed IBM i answers.
        </span>
      </div>
    )
  }

  // stage === 'upgrade'
  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-md p-5">
      <div className="text-center">
        <div className="w-12 h-12 mx-auto mb-3 rounded-full flex items-center justify-center" style={{ backgroundColor: '#990000' }}>
          <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>

        {isPQL ? (
          <>
            <p className="text-gray-700 text-sm mb-2">
              Looks like you&apos;re working through a real IBM i issue. Unlock unlimited access and keep going without interruption.
            </p>
            <p className="text-gray-700 text-sm mb-2">
              Continue with unlimited access to MC ChatMaster for $19.95/month. Get instant, source-linked answers from 113+ MC Press books and 6,300+ technical articles.
            </p>
          </>
        ) : (
          <p className="text-gray-700 text-sm mb-2">
            You&apos;ve reached your {questionsLimit} free questions. Continue with unlimited access to MC ChatMaster for $19.95/month. Get instant, source-linked answers from 113+ MC Press books and 6,300+ technical articles.
          </p>
        )}

        <p className="text-gray-500 text-xs mb-4">Cancel anytime.</p>

        <button
          onClick={handleUpgradeClick}
          className="px-6 py-2.5 text-white font-semibold rounded-xl shadow-md hover:shadow-lg transition-all text-sm"
          style={{ backgroundColor: '#990000' }}
          onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#7a0000' }}
          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#990000' }}
        >
          Start Unlimited Access — $19.95/month
        </button>

        <button
          onClick={onSignIn}
          className="text-sm text-blue-600 hover:text-blue-800 underline underline-offset-2 transition-colors mt-3"
        >
          Already subscribed? Sign In
        </button>
      </div>
    </div>
  )
}
