'use client'

import React from 'react'

interface BookLinkProps {
  url?: string | null
  title?: string
  className?: string
  children?: React.ReactNode
}

export default function BookLink({ url, title, className = '', children }: BookLinkProps) {
  // Don't render anything if no URL is provided
  if (!url || url.trim() === '') {
    return null
  }

  const defaultContent = (
    <span className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 transition-colors">
      <span className="text-sm">View on MC Press</span>
      <svg 
        className="w-3 h-3" 
        fill="none" 
        stroke="currentColor" 
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path 
          strokeLinecap="round" 
          strokeLinejoin="round" 
          strokeWidth={2} 
          d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" 
        />
      </svg>
    </span>
  )

  return (
    <a
      href={url.trim()}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex items-center hover:underline focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 rounded ${className}`}
      title={title || `View "${title || 'this book'}" on MC Press website`}
      aria-label={`Open MC Press page for ${title || 'this book'} in new tab`}
    >
      {children || defaultContent}
    </a>
  )
}