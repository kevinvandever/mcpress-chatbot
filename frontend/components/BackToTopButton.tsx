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
 * 
 * This component uses event capturing to detect scroll events on any
 * scrollable element on the page, making it work with various layout patterns.
 */
export default function BackToTopButton({ 
  threshold = 300,
  className = ''
}: BackToTopButtonProps) {
  const [isVisible, setIsVisible] = useState(false)
  const [isScrolling, setIsScrolling] = useState(false)

  // Handle scroll position detection - checks all scrollable elements
  const handleScroll = useCallback((event?: Event) => {
    // Check window scroll
    const windowScrollTop = window.pageYOffset || document.documentElement.scrollTop
    
    // Check if the event target is a scrollable element
    let elementScrollTop = 0
    if (event?.target && event.target instanceof Element) {
      elementScrollTop = (event.target as Element).scrollTop || 0
    }
    
    // Also check for any scrollable containers with the scrollbar-thin class
    const scrollableContainers = document.querySelectorAll('.scrollbar-thin, [class*="overflow-y-auto"], [class*="overflow-auto"]')
    let maxScrollTop = Math.max(windowScrollTop, elementScrollTop)
    
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
  const scrollToTop = useCallback(() => {
    setIsScrolling(true)
    
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
    
    // Reset scrolling state after animation completes
    setTimeout(() => {
      setIsScrolling(false)
    }, 500)
  }, [])

  // Handle keyboard navigation
  const handleKeyDown = useCallback((event: React.KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      scrollToTop()
    }
  }, [scrollToTop])

  // Don't render if not visible
  if (!isVisible) {
    return null
  }

  return (
    <button
      onClick={scrollToTop}
      onKeyDown={handleKeyDown}
      className={`
        fixed bottom-6 right-6 z-50
        w-12 h-12 rounded-full
        flex items-center justify-center
        shadow-lg hover:shadow-xl
        transition-all duration-300 ease-in-out
        transform hover:scale-110
        focus:outline-none focus:ring-4 focus:ring-offset-2
        disabled:opacity-50 disabled:cursor-not-allowed
        ${isScrolling ? 'animate-pulse' : ''}
        ${className}
      `}
      style={{
        backgroundColor: 'var(--mc-blue)',
        color: 'white',
        // Focus ring uses MC Press blue
        '--tw-ring-color': 'var(--mc-blue-light)',
      } as React.CSSProperties}
      aria-label="Scroll to top of page"
      title="Back to top"
      disabled={isScrolling}
      tabIndex={0}
      role="button"
    >
      {/* Up Arrow Icon */}
      <svg 
        className="w-6 h-6" 
        fill="none" 
        stroke="currentColor" 
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path 
          strokeLinecap="round" 
          strokeLinejoin="round" 
          strokeWidth={2} 
          d="M5 10l7-7m0 0l7 7m-7-7v18" 
        />
      </svg>
      
      {/* Screen reader text */}
      <span className="sr-only">Back to top</span>
    </button>
  )
}
