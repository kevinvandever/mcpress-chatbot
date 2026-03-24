'use client'

interface PaywallOverlayProps {
  signupUrl: string
  onSignIn: () => void
}

export default function PaywallOverlay({ signupUrl, onSignIn }: PaywallOverlayProps) {
  return (
    <div className="px-4 py-5 bg-gradient-to-r from-red-50 to-orange-50 border-t border-red-200">
      <div className="max-w-xl mx-auto text-center">
        <div className="w-12 h-12 mx-auto mb-3 rounded-full flex items-center justify-center" style={{ backgroundColor: '#990000' }}>
          <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
        </div>
        <p className="text-gray-700 text-sm mb-4">
          We hope you've enjoyed exploring MC ChatMaster! To continue asking questions, subscribe to get unlimited access.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <button
            onClick={() => window.open(signupUrl, '_blank')}
            className="px-6 py-2.5 text-white font-semibold rounded-xl shadow-md hover:shadow-lg transition-all text-sm"
            style={{ backgroundColor: '#990000' }}
            onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#7a0000' }}
            onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#990000' }}
          >
            Subscribe Now
          </button>
          <button
            onClick={onSignIn}
            className="text-sm text-blue-600 hover:text-blue-800 underline underline-offset-2 transition-colors"
          >
            Already subscribed? Sign In
          </button>
        </div>
      </div>
    </div>
  )
}
