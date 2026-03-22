'use client'

interface RemainingQuestionsBannerProps {
  questionsUsed: number
  questionsLimit: number
}

export default function RemainingQuestionsBanner({ questionsUsed, questionsLimit }: RemainingQuestionsBannerProps) {
  const remaining = questionsLimit - questionsUsed
  const isLastQuestion = remaining === 1

  if (remaining <= 0) return null

  if (isLastQuestion) {
    return (
      <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-sm">
        <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="font-medium">Last free question!</span>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 text-sm">
      <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span>{remaining} of {questionsLimit} free questions remaining</span>
    </div>
  )
}
