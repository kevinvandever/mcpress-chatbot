'use client'

import { useState, useEffect } from 'react'

// =====================================================
// Types and Interfaces
// =====================================================

export type DocumentType = 'book' | 'article'

interface DocumentTypeSelectorProps {
  documentType: DocumentType
  mcPressUrl?: string
  articleUrl?: string
  onChange: (data: {
    documentType: DocumentType
    mcPressUrl?: string
    articleUrl?: string
  }) => void
  disabled?: boolean
  className?: string
  showLabels?: boolean
}

// =====================================================
// URL Validation Utility
// =====================================================

const validateUrl = (url: string): boolean => {
  if (!url.trim()) return true // Empty URL is valid
  
  try {
    const urlObj = new URL(url)
    return urlObj.protocol === 'http:' || urlObj.protocol === 'https:'
  } catch {
    return false
  }
}

// =====================================================
// DocumentTypeSelector Component
// =====================================================

export default function DocumentTypeSelector({
  documentType,
  mcPressUrl = '',
  articleUrl = '',
  onChange,
  disabled = false,
  className = '',
  showLabels = true
}: DocumentTypeSelectorProps) {
  const [localMcPressUrl, setLocalMcPressUrl] = useState(mcPressUrl)
  const [localArticleUrl, setLocalArticleUrl] = useState(articleUrl)
  const [mcPressUrlError, setMcPressUrlError] = useState('')
  const [articleUrlError, setArticleUrlError] = useState('')

  // Sync with external changes
  useEffect(() => {
    setLocalMcPressUrl(mcPressUrl)
  }, [mcPressUrl])

  useEffect(() => {
    setLocalArticleUrl(articleUrl)
  }, [articleUrl])

  const handleDocumentTypeChange = (newType: DocumentType) => {
    if (disabled) return

    // Clear URL errors when switching types
    setMcPressUrlError('')
    setArticleUrlError('')

    onChange({
      documentType: newType,
      mcPressUrl: newType === 'book' ? localMcPressUrl : undefined,
      articleUrl: newType === 'article' ? localArticleUrl : undefined
    })
  }

  const handleMcPressUrlChange = (url: string) => {
    setLocalMcPressUrl(url)
    
    // Validate URL
    if (url.trim() && !validateUrl(url)) {
      setMcPressUrlError('Please enter a valid URL (must start with http:// or https://)')
    } else {
      setMcPressUrlError('')
    }

    onChange({
      documentType,
      mcPressUrl: url,
      articleUrl: documentType === 'article' ? localArticleUrl : undefined
    })
  }

  const handleArticleUrlChange = (url: string) => {
    setLocalArticleUrl(url)
    
    // Validate URL
    if (url.trim() && !validateUrl(url)) {
      setArticleUrlError('Please enter a valid URL (must start with http:// or https://)')
    } else {
      setArticleUrlError('')
    }

    onChange({
      documentType,
      mcPressUrl: documentType === 'book' ? localMcPressUrl : undefined,
      articleUrl: url
    })
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Document Type Selection */}
      <div>
        {showLabels && (
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Document Type
          </label>
        )}
        
        <div className="flex gap-6">
          {/* Book Option */}
          <label className={`
            flex items-center cursor-pointer p-3 rounded-lg border-2 transition-all duration-200
            ${documentType === 'book' 
              ? 'border-mc-blue bg-blue-50 text-mc-blue-darker' 
              : 'border-gray-200 hover:border-gray-300 text-gray-700'
            }
            ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
          `}>
            <input
              type="radio"
              name="documentType"
              value="book"
              checked={documentType === 'book'}
              onChange={(e) => handleDocumentTypeChange(e.target.value as DocumentType)}
              disabled={disabled}
              className="sr-only"
            />
            
            <div className="flex items-center gap-3">
              {/* Book Icon */}
              <div className={`
                w-8 h-8 rounded-lg flex items-center justify-center transition-colors
                ${documentType === 'book' 
                  ? 'bg-mc-blue text-white' 
                  : 'bg-gray-100 text-gray-500'
                }
              `}>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
              </div>
              
              <div>
                <div className="font-medium">Book</div>
                <div className="text-xs text-gray-500">Published book with purchase link</div>
              </div>
            </div>
            
            {/* Selection Indicator */}
            {documentType === 'book' && (
              <div className="ml-auto">
                <div className="w-5 h-5 bg-mc-blue rounded-full flex items-center justify-center">
                  <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              </div>
            )}
          </label>

          {/* Article Option */}
          <label className={`
            flex items-center cursor-pointer p-3 rounded-lg border-2 transition-all duration-200
            ${documentType === 'article' 
              ? 'border-mc-blue bg-blue-50 text-mc-blue-darker' 
              : 'border-gray-200 hover:border-gray-300 text-gray-700'
            }
            ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
          `}>
            <input
              type="radio"
              name="documentType"
              value="article"
              checked={documentType === 'article'}
              onChange={(e) => handleDocumentTypeChange(e.target.value as DocumentType)}
              disabled={disabled}
              className="sr-only"
            />
            
            <div className="flex items-center gap-3">
              {/* Article Icon */}
              <div className={`
                w-8 h-8 rounded-lg flex items-center justify-center transition-colors
                ${documentType === 'article' 
                  ? 'bg-mc-blue text-white' 
                  : 'bg-gray-100 text-gray-500'
                }
              `}>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              
              <div>
                <div className="font-medium">Article</div>
                <div className="text-xs text-gray-500">Online article with direct link</div>
              </div>
            </div>
            
            {/* Selection Indicator */}
            {documentType === 'article' && (
              <div className="ml-auto">
                <div className="w-5 h-5 bg-mc-blue rounded-full flex items-center justify-center">
                  <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              </div>
            )}
          </label>
        </div>
      </div>

      {/* URL Fields */}
      <div className="space-y-4">
        {/* MC Press URL Field (for books) */}
        {documentType === 'book' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              MC Press Purchase URL
              <span className="text-gray-500 font-normal ml-1">(optional)</span>
            </label>
            <div className="relative">
              <input
                type="url"
                value={localMcPressUrl}
                onChange={(e) => handleMcPressUrlChange(e.target.value)}
                disabled={disabled}
                placeholder="https://mcpress.com/book-title"
                className={`
                  w-full px-3 py-2 pr-10 border rounded-lg transition-colors
                  ${mcPressUrlError 
                    ? 'border-red-300 focus:ring-red-500 focus:border-red-500' 
                    : disabled
                    ? 'bg-gray-100 border-gray-200 cursor-not-allowed'
                    : 'border-gray-300 focus:ring-2 focus:ring-mc-blue focus:border-mc-blue'
                  }
                `}
              />
              
              {/* URL Icon */}
              <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                <svg className={`w-4 h-4 ${mcPressUrlError ? 'text-red-400' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                </svg>
              </div>
            </div>
            
            {mcPressUrlError && (
              <p className="mt-1 text-sm text-red-600 flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {mcPressUrlError}
              </p>
            )}
            
            <p className="mt-1 text-xs text-gray-500">
              Link to purchase this book from MC Press
            </p>
          </div>
        )}

        {/* Article URL Field (for articles) */}
        {documentType === 'article' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Article URL
              <span className="text-gray-500 font-normal ml-1">(optional)</span>
            </label>
            <div className="relative">
              <input
                type="url"
                value={localArticleUrl}
                onChange={(e) => handleArticleUrlChange(e.target.value)}
                disabled={disabled}
                placeholder="https://example.com/article-title"
                className={`
                  w-full px-3 py-2 pr-10 border rounded-lg transition-colors
                  ${articleUrlError 
                    ? 'border-red-300 focus:ring-red-500 focus:border-red-500' 
                    : disabled
                    ? 'bg-gray-100 border-gray-200 cursor-not-allowed'
                    : 'border-gray-300 focus:ring-2 focus:ring-mc-blue focus:border-mc-blue'
                  }
                `}
              />
              
              {/* URL Icon */}
              <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                <svg className={`w-4 h-4 ${articleUrlError ? 'text-red-400' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                </svg>
              </div>
            </div>
            
            {articleUrlError && (
              <p className="mt-1 text-sm text-red-600 flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {articleUrlError}
              </p>
            )}
            
            <p className="mt-1 text-xs text-gray-500">
              Direct link to the online article
            </p>
          </div>
        )}
      </div>

      {/* Help Text */}
      <div className="text-xs text-gray-500 bg-gray-50 p-3 rounded-lg">
        <div className="flex items-start gap-2">
          <svg className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="space-y-1">
            <p><strong>Books:</strong> Published works available for purchase, typically with MC Press purchase links</p>
            <p><strong>Articles:</strong> Online content with direct web links to the full article</p>
            <p>URLs must start with http:// or https:// and are optional for both document types</p>
          </div>
        </div>
      </div>
    </div>
  )
}