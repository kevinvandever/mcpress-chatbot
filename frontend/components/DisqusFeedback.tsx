'use client'

import React, { useState, useRef, useCallback } from 'react'

const DISQUS_SHORTNAME = 'mc-chatmaster-disqus-com'
const DISQUS_PAGE_IDENTIFIER = 'mc-chatmaster-main'
const DISQUS_PAGE_URL = 'https://mc-chatmaster.netlify.app'

/** Timeout (ms) to detect Disqus render failures after script injection. */
const RENDER_TIMEOUT_MS = 10_000

export default function DisqusFeedback(): JSX.Element {
  const [isExpanded, setIsExpanded] = useState(false)
  const [loadError, setLoadError] = useState(false)
  const hasLoadedDisqus = useRef(false)

  const loadDisqus = useCallback(() => {
    if (hasLoadedDisqus.current) return
    hasLoadedDisqus.current = true

    // Set Disqus configuration before script injection
    ;(window as any).disqus_config = function (this: any) {
      this.page.url = DISQUS_PAGE_URL
      this.page.identifier = DISQUS_PAGE_IDENTIFIER
    }

    const script = document.createElement('script')
    script.src = `https://${DISQUS_SHORTNAME}.disqus.com/embed.js`
    script.async = true
    script.setAttribute('data-timestamp', String(+new Date()))

    script.onerror = () => {
      setLoadError(true)
    }

    document.body.appendChild(script)

    // Timeout fallback: if #disqus_thread stays empty, treat as failure
    setTimeout(() => {
      const container = document.getElementById('disqus_thread')
      if (container && container.children.length === 0) {
        setLoadError(true)
      }
    }, RENDER_TIMEOUT_MS)
  }, [])

  const handleToggle = useCallback(() => {
    setIsExpanded((prev) => {
      const next = !prev
      if (next && !hasLoadedDisqus.current) {
        loadDisqus()
      }
      return next
    })
  }, [loadDisqus])

  return (
    <div
      className="bg-white rounded-lg shadow-sm border"
      style={{ borderColor: 'var(--border-primary)' }}
    >
      <button
        type="button"
        onClick={handleToggle}
        aria-expanded={isExpanded}
        className="w-full flex items-center justify-between p-6 cursor-pointer select-none focus:outline-none focus:ring-2 focus:ring-offset-2 rounded-lg"
        style={{ focusRingColor: 'var(--mc-green)' } as React.CSSProperties}
      >
        <h2
          className="text-xl sm:text-2xl font-bold flex items-center"
          style={{ color: 'var(--text-primary)' }}
        >
          <svg
            className="w-6 h-6 mr-2 shrink-0"
            style={{ color: 'var(--mc-green)' }}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M17 8h2a2 2 0 012 2v6a2 2 0 01-2 2h-2v4l-4-4H9a2 2 0 01-2-2v-6a2 2 0 012-2h8zM7 8V6a2 2 0 012-2h8a2 2 0 012 2v6a2 2 0 01-2 2h-1"
            />
          </svg>
          Community Feedback
        </h2>

        {/* Chevron icon — rotates when expanded */}
        <svg
          className={`w-5 h-5 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
          style={{ color: 'var(--mc-green)' }}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Disqus thread container — hidden when collapsed */}
      <div
        id="disqus_thread"
        aria-label="Community feedback comments"
        className={isExpanded ? 'px-6 pb-6' : 'hidden'}
      >
        {loadError && (
          <p className="text-sm text-gray-500 py-4">
            Comments could not be loaded. Please check your connection or ad blocker settings.
          </p>
        )}
      </div>
    </div>
  )
}
