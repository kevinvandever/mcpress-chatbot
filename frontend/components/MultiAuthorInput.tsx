'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'
import { API_URL } from '../config/api'

// =====================================================
// Types and Interfaces
// =====================================================

interface Author {
  id?: number
  name: string
  site_url?: string
  order: number
}

interface AuthorSearchResult {
  id: number
  name: string
  site_url?: string
  document_count?: number
}

interface MultiAuthorInputProps {
  authors: Author[]
  onChange: (authors: Author[]) => void
  disabled?: boolean
  className?: string
  placeholder?: string
  maxAuthors?: number
}

interface AuthorItemProps {
  author: Author
  index: number
  onUpdate: (index: number, author: Author) => void
  onRemove: (index: number) => void
  onMoveUp: (index: number) => void
  onMoveDown: (index: number) => void
  canRemove: boolean
  canMoveUp: boolean
  canMoveDown: boolean
  disabled?: boolean
}

// =====================================================
// Author Item Component
// =====================================================

function AuthorItem({
  author,
  index,
  onUpdate,
  onRemove,
  onMoveUp,
  onMoveDown,
  canRemove,
  canMoveUp,
  canMoveDown,
  disabled = false
}: AuthorItemProps) {
  const [isEditingUrl, setIsEditingUrl] = useState(false)
  const [urlValue, setUrlValue] = useState(author.site_url || '')
  const [isDragging, setIsDragging] = useState(false)
  const urlInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    setUrlValue(author.site_url || '')
  }, [author.site_url])

  useEffect(() => {
    if (isEditingUrl && urlInputRef.current) {
      urlInputRef.current.focus()
      urlInputRef.current.select()
    }
  }, [isEditingUrl])

  const validateUrl = (url: string): boolean => {
    if (!url.trim()) return true // Empty URL is valid
    
    try {
      const urlObj = new URL(url)
      return urlObj.protocol === 'http:' || urlObj.protocol === 'https:'
    } catch {
      return false
    }
  }

  const handleUrlSave = () => {
    const trimmedUrl = urlValue.trim()
    
    if (trimmedUrl && !validateUrl(trimmedUrl)) {
      alert('Please enter a valid URL (must start with http:// or https://)')
      return
    }

    onUpdate(index, {
      ...author,
      site_url: trimmedUrl || undefined
    })
    setIsEditingUrl(false)
  }

  const handleUrlCancel = () => {
    setUrlValue(author.site_url || '')
    setIsEditingUrl(false)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleUrlSave()
    } else if (e.key === 'Escape') {
      handleUrlCancel()
    }
  }

  const handleDragStart = (e: React.DragEvent) => {
    if (disabled) return
    
    setIsDragging(true)
    e.dataTransfer.setData('text/plain', index.toString())
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDragEnd = () => {
    setIsDragging(false)
  }

  return (
    <div
      className={`
        group relative bg-white border rounded-lg p-3 transition-all duration-200
        ${isDragging ? 'opacity-50 scale-95' : ''}
        ${disabled ? 'bg-gray-50 border-gray-200' : 'border-gray-300 hover:border-blue-400 hover:shadow-sm'}
      `}
      draggable={!disabled}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      {/* Drag Handle */}
      {!disabled && (
        <div className="absolute left-1 top-1/2 transform -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity cursor-grab active:cursor-grabbing">
          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8h16M4 16h16" />
          </svg>
        </div>
      )}

      <div className="flex items-start gap-3 ml-6">
        {/* Author Order Badge */}
        <div className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xs font-medium">
          {index + 1}
        </div>

        {/* Author Info */}
        <div className="flex-1 min-w-0">
          {/* Author Name */}
          <div className="flex items-center gap-2 mb-2">
            <span className="font-medium text-gray-900 truncate">{author.name}</span>
            {author.id && (
              <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                ID: {author.id}
              </span>
            )}
          </div>

          {/* Author URL */}
          <div className="text-sm">
            {isEditingUrl ? (
              <div className="flex items-center gap-2">
                <input
                  ref={urlInputRef}
                  type="url"
                  value={urlValue}
                  onChange={(e) => setUrlValue(e.target.value)}
                  onKeyDown={handleKeyPress}
                  onBlur={handleUrlSave}
                  placeholder="https://author-website.com"
                  className="flex-1 px-2 py-1 text-xs border border-blue-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <button
                  onClick={handleUrlSave}
                  className="text-green-600 hover:text-green-800 p-1"
                  title="Save URL"
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </button>
                <button
                  onClick={handleUrlCancel}
                  className="text-red-600 hover:text-red-800 p-1"
                  title="Cancel"
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                {author.site_url ? (
                  <a
                    href={author.site_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-800 text-xs truncate max-w-48"
                    title={author.site_url}
                  >
                    {author.site_url}
                  </a>
                ) : (
                  <span className="text-gray-400 text-xs">No website</span>
                )}
                {!disabled && (
                  <button
                    onClick={() => setIsEditingUrl(true)}
                    className="text-gray-400 hover:text-blue-600 p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                    title="Edit website URL"
                  >
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        {!disabled && (
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            {/* Move Up */}
            <button
              onClick={() => onMoveUp(index)}
              disabled={!canMoveUp}
              className="p-1 text-gray-400 hover:text-blue-600 disabled:opacity-30 disabled:cursor-not-allowed"
              title="Move up"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
              </svg>
            </button>

            {/* Move Down */}
            <button
              onClick={() => onMoveDown(index)}
              disabled={!canMoveDown}
              className="p-1 text-gray-400 hover:text-blue-600 disabled:opacity-30 disabled:cursor-not-allowed"
              title="Move down"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {/* Remove */}
            <button
              onClick={() => onRemove(index)}
              disabled={!canRemove}
              className="p-1 text-gray-400 hover:text-red-600 disabled:opacity-30 disabled:cursor-not-allowed"
              title={canRemove ? "Remove author" : "Cannot remove last author"}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// =====================================================
// Main MultiAuthorInput Component
// =====================================================

export default function MultiAuthorInput({
  authors,
  onChange,
  disabled = false,
  className = '',
  placeholder = 'Search for authors...',
  maxAuthors = 10
}: MultiAuthorInputProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<AuthorSearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [showDropdown, setShowDropdown] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const [dragOverIndex, setDragOverIndex] = useState(-1)

  const searchInputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Debounced search
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([])
      setShowDropdown(false)
      return
    }

    const timeoutId = setTimeout(async () => {
      await performSearch(searchQuery)
    }, 300)

    return () => clearTimeout(timeoutId)
  }, [searchQuery])

  // Click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setShowDropdown(false)
        setSelectedIndex(-1)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const performSearch = async (query: string) => {
    if (!query.trim()) return

    setIsSearching(true)
    try {
      const response = await axios.get(`${API_URL}/api/authors/search`, {
        params: { q: query, limit: 10 }
      })
      
      // Filter out authors already in the list
      const existingNames = new Set(authors.map(a => a.name.toLowerCase()))
      const filteredResults = response.data.filter(
        (result: AuthorSearchResult) => !existingNames.has(result.name.toLowerCase())
      )
      
      setSearchResults(filteredResults)
      setShowDropdown(filteredResults.length > 0)
      setSelectedIndex(-1)
    } catch (error) {
      console.error('Author search failed:', error)
      setSearchResults([])
      setShowDropdown(false)
    } finally {
      setIsSearching(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showDropdown) return

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex(prev => 
          prev < searchResults.length - 1 ? prev + 1 : prev
        )
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex(prev => prev > 0 ? prev - 1 : -1)
        break
      case 'Enter':
        e.preventDefault()
        if (selectedIndex >= 0 && selectedIndex < searchResults.length) {
          addAuthor(searchResults[selectedIndex])
        } else if (searchQuery.trim()) {
          addNewAuthor(searchQuery.trim())
        }
        break
      case 'Escape':
        setShowDropdown(false)
        setSelectedIndex(-1)
        break
    }
  }

  const addAuthor = (searchResult: AuthorSearchResult) => {
    if (authors.length >= maxAuthors) {
      alert(`Maximum ${maxAuthors} authors allowed`)
      return
    }

    const newAuthor: Author = {
      id: searchResult.id,
      name: searchResult.name,
      site_url: searchResult.site_url,
      order: authors.length
    }

    onChange([...authors, newAuthor])
    setSearchQuery('')
    setShowDropdown(false)
    setSelectedIndex(-1)
  }

  const addNewAuthor = (name: string) => {
    if (authors.length >= maxAuthors) {
      alert(`Maximum ${maxAuthors} authors allowed`)
      return
    }

    // Check if author already exists
    if (authors.some(a => a.name.toLowerCase() === name.toLowerCase())) {
      alert('This author is already in the list')
      return
    }

    const newAuthor: Author = {
      name: name,
      order: authors.length
    }

    onChange([...authors, newAuthor])
    setSearchQuery('')
    setShowDropdown(false)
    setSelectedIndex(-1)
  }

  const updateAuthor = (index: number, updatedAuthor: Author) => {
    const newAuthors = [...authors]
    newAuthors[index] = { ...updatedAuthor, order: index }
    onChange(newAuthors)
  }

  const removeAuthor = (index: number) => {
    if (authors.length <= 1) {
      alert('Documents must have at least one author')
      return
    }

    const newAuthors = authors.filter((_, i) => i !== index)
    // Update order values
    const reorderedAuthors = newAuthors.map((author, i) => ({
      ...author,
      order: i
    }))
    onChange(reorderedAuthors)
  }

  const moveAuthor = (fromIndex: number, toIndex: number) => {
    if (fromIndex === toIndex) return

    const newAuthors = [...authors]
    const [movedAuthor] = newAuthors.splice(fromIndex, 1)
    newAuthors.splice(toIndex, 0, movedAuthor)

    // Update order values
    const reorderedAuthors = newAuthors.map((author, i) => ({
      ...author,
      order: i
    }))
    onChange(reorderedAuthors)
  }

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragOverIndex(index)
  }

  const handleDrop = (e: React.DragEvent, dropIndex: number) => {
    e.preventDefault()
    const dragIndex = parseInt(e.dataTransfer.getData('text/plain'))
    
    if (dragIndex !== dropIndex) {
      moveAuthor(dragIndex, dropIndex)
    }
    
    setDragOverIndex(-1)
  }

  const handleDragLeave = () => {
    setDragOverIndex(-1)
  }

  return (
    <div ref={containerRef} className={`space-y-4 ${className}`}>
      {/* Search Input */}
      <div className="relative">
        <div className="relative">
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => searchQuery && setShowDropdown(searchResults.length > 0)}
            disabled={disabled || authors.length >= maxAuthors}
            placeholder={
              authors.length >= maxAuthors 
                ? `Maximum ${maxAuthors} authors reached`
                : placeholder
            }
            className={`
              w-full px-3 py-2 pr-10 border rounded-lg transition-colors
              ${disabled || authors.length >= maxAuthors
                ? 'bg-gray-100 border-gray-200 cursor-not-allowed'
                : 'border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
              }
            `}
          />
          
          {/* Search Icon */}
          <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
            {isSearching ? (
              <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            )}
          </div>
        </div>

        {/* Search Dropdown */}
        {showDropdown && searchResults.length > 0 && (
          <div
            ref={dropdownRef}
            className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto"
          >
            {searchResults.map((result, index) => (
              <button
                key={result.id}
                onClick={() => addAuthor(result)}
                className={`
                  w-full px-3 py-2 text-left hover:bg-blue-50 transition-colors
                  ${index === selectedIndex ? 'bg-blue-50' : ''}
                  ${index === 0 ? 'rounded-t-lg' : ''}
                  ${index === searchResults.length - 1 ? 'rounded-b-lg' : ''}
                `}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-gray-900">{result.name}</div>
                    {result.site_url && (
                      <div className="text-xs text-blue-600 truncate max-w-48">
                        {result.site_url}
                      </div>
                    )}
                  </div>
                  {result.document_count !== undefined && (
                    <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                      {result.document_count} docs
                    </span>
                  )}
                </div>
              </button>
            ))}
            
            {/* Add New Author Option */}
            {searchQuery.trim() && !searchResults.some(r => r.name.toLowerCase() === searchQuery.toLowerCase()) && (
              <button
                onClick={() => addNewAuthor(searchQuery.trim())}
                className="w-full px-3 py-2 text-left hover:bg-green-50 border-t border-gray-200 transition-colors rounded-b-lg"
              >
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                  <span className="text-green-700 font-medium">
                    Add new author: "{searchQuery.trim()}"
                  </span>
                </div>
              </button>
            )}
          </div>
        )}
      </div>

      {/* Authors List */}
      {authors.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-700">
              Authors ({authors.length})
            </label>
            {authors.length > 1 && !disabled && (
              <span className="text-xs text-gray-500">
                Drag to reorder
              </span>
            )}
          </div>

          <div className="space-y-2">
            {authors.map((author, index) => (
              <div
                key={`${author.name}-${index}`}
                onDragOver={(e) => handleDragOver(e, index)}
                onDrop={(e) => handleDrop(e, index)}
                onDragLeave={handleDragLeave}
                className={`
                  transition-all duration-200
                  ${dragOverIndex === index ? 'border-t-2 border-blue-500 pt-2' : ''}
                `}
              >
                <AuthorItem
                  author={author}
                  index={index}
                  onUpdate={updateAuthor}
                  onRemove={removeAuthor}
                  onMoveUp={(i) => moveAuthor(i, i - 1)}
                  onMoveDown={(i) => moveAuthor(i, i + 1)}
                  canRemove={authors.length > 1}
                  canMoveUp={index > 0}
                  canMoveDown={index < authors.length - 1}
                  disabled={disabled}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {authors.length === 0 && (
        <div className="text-center py-8 border-2 border-dashed border-gray-300 rounded-lg">
          <svg className="w-8 h-8 text-gray-400 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
          <p className="text-gray-500 text-sm">No authors added yet</p>
          <p className="text-gray-400 text-xs mt-1">Search and add authors above</p>
        </div>
      )}

      {/* Help Text */}
      <div className="text-xs text-gray-500 space-y-1">
        <p>• Type to search existing authors or add new ones</p>
        <p>• Use drag handles or arrow buttons to reorder</p>
        <p>• Click website links to edit author URLs</p>
        <p>• Documents must have at least one author</p>
      </div>
    </div>
  )
}