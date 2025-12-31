'use client'

import { useState, useEffect, useCallback } from 'react'

interface BackToTopButtonProps {
  /** Scroll threshold in pixels before button appears */
  threshold?: number
  /** Custom className for additional styling */
  className?: string
}

/**
 * BackToTopButton - A floating button that appears when users scroll down
 * and smoothly scrolls to the top of the page when clicked.
 * 
 * Follows MC Press design system and accessibility standards.
 */
export default function BackToTopButton({ 
  threshold = 300,
  className = ''
}: BackToTopButtonProps) {
  const [isVisible, setIsVisible] = useState(false)

  // Handle scroll position detection - checks all scrollable elements
  const handleScroll = useCallback(() => {
    // Check window scroll
    const windowScrollTop = window.pageYOffset || document.documentElement.scrollTop
    
    // Also check for any scrollable containers
    const scrollableContainers = document.querySelectorAll('.scrollbar-thin, [class*="overflow-y-auto"], [class*="overflow-auto"]')
    let maxScrollTop = windowScrollTop
    
    scrollableContainers.forEach((container) => {
      if (container.scrollTop > maxScrollTop) {
        maxScrollTop = container.scrollTop
      }
    })
    
    setIsVisible(maxScrollTop > threshold)
  }, [threshold])

  // Set up scroll listener using capture phase to catch all scroll events
  useEffect(() => {
    // Check initial scroll position
    handleScroll()
    
    // Use capture phase to catch scroll events on any element
    document.addEventListener('scroll', handleScroll, { capture: true, passive: true })
    window.addEventListener('scroll', handleScroll, { passive: true })
    
    return () => {
      document.removeEventListener('scroll', handleScroll, { capture: true })
      window.removeEventListener('scroll', handleScroll)
    }
  }, [handleScroll])

  // Smooth scroll to top functionality - scrolls all scrollable elements
  const scrollToTop = () => {
    // Scroll the window
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    })
    
    // Also scroll any scrollable containers
    const scrollableContainers = document.querySelectorAll('.scrollbar-thin, [class*="overflow-y-auto"], [class*="overflow-auto"]')
    scrollableContainers.forEach((container) => {
      container.scrollTo({
        top: 0,
        behavior: 'smooth'
      })
    })
  }

  // Don't render if not visible
  if (!isVisible) {
    return null
  }

  return (
    <button
      type="button"
      onClick={(e) => {
        e.preventDefault()
        e.stopPropagation()
        scrollToTop()
      }}
      className={`
        fixed bottom-6 right-6 z-[9999]
        w-14 h-14 rounded-full
        flex items-center justify-center
        shadow-xl hover:shadow-2xl
        transition-all duration-300 ease-in-out
        transform hover:scale-110 active:scale-95
        focus:outline-none focus:ring-4 focus:ring-offset-2
        cursor-pointer
        ${className}
      `}
      style={{
        backgroundColor: 'var(--mc-blue, #878DBC)',
        color: 'white',
        '--tw-ring-color': 'var(--mc-blue-light, #A5AACF)',
      } as React.CSSProperties}
      aria-label="Scroll to top of page"
      title="Back to top"
      tabIndex={0}
    >
      {/* Up Arrow Icon */}
      <svg 
        className="w-7 h-7" 
        fill="none" 
        stroke="currentColor" 
        viewBox="0 0 24 24"
        aria-hidden="true"
        style={{ pointerEvents: 'none' }}
      >
        <path 
          strokeLinecap="round" 
          strokeLinejoin="round" 
          strokeWidth={2.5} 
          d="M5 10l7-7m0 0l7 7m-7-7v18" 
        />
      </svg>
      
      {/* Screen reader text */}
      <span className="sr-only">Back to top</span>
    </button>
  )
}
