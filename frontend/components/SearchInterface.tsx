'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { debounce } from 'lodash'

interface SearchResult {
  id: string
  content: string
  metadata: {
    type: 'text' | 'image' | 'code'
    filename: string
    page?: number
    language?: string
    chunk_index?: number
    total_chunks?: number
    has_ocr?: boolean
    image_index?: number
    author?: string
  }
  distance: number
}

interface SearchInterfaceProps {
  onResultSelect?: (result: SearchResult) => void
}

export default function SearchInterface({ onResultSelect }: SearchInterfaceProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Removed content type filters - search all content types
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null)
  const [contextResults, setContextResults] = useState<SearchResult[]>([])
  const [contextLoading, setContextLoading] = useState(false)
  const searchResultsRef = useRef<HTMLDivElement>(null)

  // Debounced search function
  const debouncedSearch = useCallback(
    debounce(async (searchQuery: string) => {
      if (!searchQuery.trim()) {
        setResults([])
        return
      }

      setLoading(true)
      setError(null)

      try {
        // Search all content types without filtering
        const response = await fetch(
          `http://localhost:8000/search?q=${encodeURIComponent(searchQuery)}&n_results=20`
        )
        
        if (!response.ok) {
          throw new Error('Search failed')
        }

        const data = await response.json()
        
        // Filter out page separator chunks and other low-quality content
        const filteredResults = (data.results || []).filter((result: SearchResult) => {
          const content = result.content.trim()
          
          // Skip very short content
          if (content.length < 30) return false
          
          // Skip chunks that are primarily page separators
          const lines = content.split('\n')
          const meaningfulLines = lines.filter(line => 
            !line.trim().match(/^---\s*Page\s+\d+\s*---\s*$/) && 
            line.trim().length > 0
          )
          const meaningfulContent = meaningfulLines.join('\n').trim()
          
          // Require substantial meaningful content
          if (meaningfulContent.length < 50) return false
          
          return true
        })
        
        setResults(filteredResults.slice(0, 10)) // Limit to top 10 results
        
        // Scroll to top of results
        if (searchResultsRef.current) {
          searchResultsRef.current.scrollTop = 0
        }
      } catch (err) {
        setError('Search failed. Please try again.')
        console.error('Search error:', err)
      } finally {
        setLoading(false)
      }
    }, 300),
    []
  )

  useEffect(() => {
    debouncedSearch(query)
  }, [query, debouncedSearch])


  const getContentTypeIcon = (type: string) => {
    switch (type) {
      case 'text': return '📝'
      case 'image': return '🖼️'
      case 'code': return '💻'
      default: return '📄'
    }
  }

  const getContentTypeClass = (type: string) => {
    switch (type) {
      case 'text': return 'content-type-text'
      case 'image': return 'content-type-image'
      case 'code': return 'content-type-code'
      default: return 'content-type-text'
    }
  }

  const formatRelevanceScore = (distance: number) => {
    // ChromaDB returns cosine distance (0-2), convert to similarity percentage
    // For cosine distance: 0 = identical, 2 = completely different
    const similarity = Math.max(0, (2 - distance) / 2)
    const relevance = Math.max(0, Math.min(100, similarity * 100))
    return Math.round(relevance)
  }

  const truncateContent = (content: string, maxLength: number = 150) => {
    if (content.length <= maxLength) return content
    return content.substring(0, maxLength) + '...'
  }

  const fetchContextForResult = async (result: SearchResult) => {
    setContextLoading(true)
    setSelectedResult(result)
    
    try {
      // Get context by fetching nearby chunks from the same document
      const response = await fetch(
        `http://localhost:8000/search?q=${encodeURIComponent(result.content)}&n_results=5&filename=${result.metadata.filename}`
      )
      
      if (!response.ok) {
        throw new Error('Failed to fetch context')
      }
      
      const data = await response.json()
      setContextResults(data.results || [])
    } catch (error) {
      console.error('Error fetching context:', error)
      setContextResults([])
    } finally {
      setContextLoading(false)
    }
  }

  const handleResultClick = (result: SearchResult) => {
    fetchContextForResult(result)
    onResultSelect?.(result)
  }

  const closeContextModal = () => {
    setSelectedResult(null)
    setContextResults([])
  }

  return (
    <div className="space-y-4">
      {/* Search Input */}
      <div className="relative">
        <label htmlFor="search-input" className="sr-only">
          Search across all documents
        </label>
        <input
          id="search-input"
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search across all documents..."
          className="w-full px-4 py-2 pl-10 pr-4 border border-gray-300 rounded-lg focus-ring"
          aria-describedby="search-help"
          role="searchbox"
          aria-label="Search documents"
        />
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <svg className="h-5 w-5 text-gray-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
          </svg>
        </div>
        <div id="search-help" className="sr-only">
          Search will look for content in all uploaded PDF documents including text, images, and code blocks
        </div>
      </div>


      {/* Search Results */}
      <div 
        ref={searchResultsRef}
        className="space-y-3 max-h-96 overflow-y-auto scrollbar-thin" 
        role="region" 
        aria-live="polite" 
        aria-label="Search results"
      >
        {loading && (
          <div className="text-center py-4" role="status" aria-live="polite">
            <div className="inline-flex items-center">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2" aria-hidden="true"></div>
              <span className="text-gray-600">Searching...</span>
            </div>
          </div>
        )}

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700" role="alert">
            {error}
          </div>
        )}

        {!loading && !error && query && results.length === 0 && (
          <div className="text-center py-4 text-gray-500" role="status">
            No results found for "{query}"
          </div>
        )}

        {results.length > 0 && (
          <div className="sr-only" aria-live="polite">
            Found {results.length} result{results.length === 1 ? '' : 's'} for "{query}"
          </div>
        )}

        {results.map((result, index) => (
          <div
            key={result.id}
            className="card card-hover cursor-pointer transition-all-fast focus-ring"
            onClick={() => handleResultClick(result)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                handleResultClick(result)
              }
            }}
            tabIndex={0}
            role="button"
            aria-label={`Select search result ${index + 1}: ${result.metadata.filename}, ${formatRelevanceScore(result.distance)}% match`}
          >
            <div className="flex items-start gap-3">
              <div className={`px-2 py-1 rounded text-xs font-medium ${getContentTypeClass(result.metadata.type)}`}>
                <span aria-hidden="true">{getContentTypeIcon(result.metadata.type)}</span> {result.metadata.type}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <div className="text-sm font-medium text-gray-900 truncate">
                    {result.metadata.filename}
                    {result.metadata.page && (
                      <span className="ml-2 text-gray-500">Page {result.metadata.page}</span>
                    )}
                  </div>
                  <div className="text-xs text-gray-500">
                    {formatRelevanceScore(result.distance)}% match
                  </div>
                </div>
                
                {result.metadata.author && (
                  <div className="text-xs text-gray-600 mb-1">
                    <span className="font-medium">By:</span> {result.metadata.author}
                  </div>
                )}
                
                <div className="text-sm text-gray-700 mb-2">
                  {result.metadata.type === 'code' ? (
                    <pre className="bg-gray-50 p-2 rounded text-xs overflow-x-auto">
                      <code>{truncateContent(result.content)}</code>
                    </pre>
                  ) : (
                    <p>{truncateContent(result.content)}</p>
                  )}
                </div>
                
                {result.metadata.language && (
                  <div className="text-xs text-gray-500">
                    Language: {result.metadata.language}
                  </div>
                )}
                
                {result.metadata.has_ocr && (
                  <div className="text-xs text-green-600">
                    <span aria-hidden="true">✓</span> OCR extracted text
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Context Modal */}
      {selectedResult && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <div className="flex items-center gap-3">
                <div className={`px-2 py-1 rounded text-xs font-medium ${getContentTypeClass(selectedResult.metadata.type)}`}>
                  <span aria-hidden="true">{getContentTypeIcon(selectedResult.metadata.type)}</span> {selectedResult.metadata.type}
                </div>
                <h2 className="text-lg font-semibold text-gray-900 truncate">
                  {selectedResult.metadata.filename}
                  {selectedResult.metadata.page && (
                    <span className="ml-2 text-gray-500">Page {selectedResult.metadata.page}</span>
                  )}
                </h2>
              </div>
              <button
                onClick={closeContextModal}
                className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"
                aria-label="Close context window"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-4 overflow-y-auto max-h-[calc(90vh-120px)]">
              {contextLoading ? (
                <div className="text-center py-8">
                  <div className="inline-flex items-center">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mr-3"></div>
                    <span className="text-gray-600">Loading context...</span>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Selected Result - Highlighted */}
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-2 h-2 bg-blue-600 rounded-full"></div>
                      <span className="text-sm font-medium text-blue-900">Selected Result</span>
                      <span className="text-xs text-blue-700">{formatRelevanceScore(selectedResult.distance)}% match</span>
                    </div>
                    <div className="text-sm text-gray-800">
                      {selectedResult.metadata.type === 'code' ? (
                        <pre className="bg-gray-800 text-green-400 p-3 rounded text-xs overflow-x-auto whitespace-pre-wrap">
                          <code>{selectedResult.content}</code>
                        </pre>
                      ) : (
                        <p className="whitespace-pre-wrap">{selectedResult.content}</p>
                      )}
                    </div>
                  </div>

                  {/* Context Results */}
                  {contextResults.length > 0 && (
                    <div>
                      <h3 className="text-sm font-medium text-gray-700 mb-3">Related Context</h3>
                      <div className="space-y-3">
                        {contextResults
                          .filter(result => result.id !== selectedResult.id)
                          .map((result, index) => (
                            <div key={result.id} className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                              <div className="flex items-center gap-2 mb-2">
                                <div className={`px-2 py-1 rounded text-xs font-medium ${getContentTypeClass(result.metadata.type)}`}>
                                  <span aria-hidden="true">{getContentTypeIcon(result.metadata.type)}</span> {result.metadata.type}
                                </div>
                                {result.metadata.page && (
                                  <span className="text-xs text-gray-500">Page {result.metadata.page}</span>
                                )}
                                <span className="text-xs text-gray-500">{formatRelevanceScore(result.distance)}% match</span>
                              </div>
                              <div className="text-sm text-gray-700">
                                {result.metadata.type === 'code' ? (
                                  <pre className="bg-gray-800 text-green-400 p-2 rounded text-xs overflow-x-auto whitespace-pre-wrap">
                                    <code>{result.content}</code>
                                  </pre>
                                ) : (
                                  <p className="whitespace-pre-wrap">{result.content}</p>
                                )}
                              </div>
                            </div>
                          ))}
                      </div>
                    </div>
                  )}

                  {contextResults.length === 0 && !contextLoading && (
                    <div className="text-center py-4 text-gray-500">
                      No additional context found for this result.
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="flex justify-end gap-3 p-4 border-t border-gray-200">
              <button
                onClick={closeContextModal}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}