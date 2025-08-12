'use client'

import { useState } from 'react'

interface Source {
  filename: string
  page: string | number
  distance?: number
  author?: string
  mc_press_url?: string
}

interface CompactSourcesProps {
  sources: Source[]
}

export default function CompactSources({ sources }: CompactSourcesProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  
  // Group sources by filename and preserve metadata
  const groupedSources = sources.reduce((acc, source) => {
    const filename = source.filename.replace('.pdf', '')
    if (!acc[filename]) {
      acc[filename] = {
        pages: [],
        author: source.author || 'Unknown Author',
        mc_press_url: source.mc_press_url || ''
      }
    }
    acc[filename].pages.push(source.page)
    return acc
  }, {} as Record<string, { pages: (string | number)[], author: string, mc_press_url: string }>)
  
  const sourceKeys = Object.keys(groupedSources)
  const displayCount = isExpanded ? sourceKeys.length : Math.min(2, sourceKeys.length)
  
  return (
    <div className="mt-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
      <div className="flex items-center gap-1 mb-2">
        <svg className="w-3 h-3 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
        </svg>
        <span className="text-xs font-semibold text-gray-700">References</span>
      </div>
      
      <div className="space-y-2">
        {sourceKeys.slice(0, displayCount).map(filename => {
          const sourceData = groupedSources[filename]
          const uniquePages = [...new Set(sourceData.pages)].sort((a, b) => {
            const pageA = typeof a === 'number' ? a : parseInt(a as string) || 0
            const pageB = typeof b === 'number' ? b : parseInt(b as string) || 0
            return pageA - pageB
          })
          
          return (
            <div key={filename} className="bg-white p-2 rounded border border-gray-100">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-xs text-gray-900 truncate" title={filename}>
                    {filename}
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    by {sourceData.author}
                    {uniquePages.length > 0 && uniquePages[0] !== 'N/A' && (
                      <span className="ml-1">
                        • p. {uniquePages.slice(0, 3).join(', ')}
                        {uniquePages.length > 3 && `, +${uniquePages.length - 3} more`}
                      </span>
                    )}
                  </div>
                </div>
                {sourceData.mc_press_url && (
                  <a
                    href={sourceData.mc_press_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-shrink-0 text-xs bg-blue-600 hover:bg-blue-700 text-white px-2 py-1 rounded transition-colors"
                    title="Purchase from MC Press"
                  >
                    Buy
                  </a>
                )}
                {!sourceData.mc_press_url && (
                  <button
                    disabled
                    className="flex-shrink-0 text-xs bg-gray-200 text-gray-400 px-2 py-1 rounded cursor-not-allowed"
                    title="Purchase link not available"
                  >
                    Buy
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
      
      {sourceKeys.length > 2 && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="mt-2 text-xs text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1"
        >
          {isExpanded ? (
            <>
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
              </svg>
              Show less
            </>
          ) : (
            <>
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
              Show {sourceKeys.length - 2} more book{sourceKeys.length - 2 !== 1 ? 's' : ''}
            </>
          )}
        </button>
      )}
    </div>
  )
}