import React, { useState, useEffect } from 'react'
import type { ConversationFilters } from '@/services/conversationService'

interface ConversationSearchProps {
  onSearch: (query: string) => void
  onFilterChange: (filters: ConversationFilters) => void
  currentFilters: ConversationFilters
}

export default function ConversationSearch({
  onSearch,
  onFilterChange,
  currentFilters,
}: ConversationSearchProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [localFilters, setLocalFilters] = useState<ConversationFilters>(currentFilters)

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      onSearch(searchQuery)
    }, 500)

    return () => clearTimeout(timer)
  }, [searchQuery])

  const handleFilterChange = (key: keyof ConversationFilters, value: any) => {
    const newFilters = { ...localFilters, [key]: value }
    setLocalFilters(newFilters)
    onFilterChange(newFilters)
  }

  const handleClearFilters = () => {
    const emptyFilters: ConversationFilters = {}
    setLocalFilters(emptyFilters)
    onFilterChange(emptyFilters)
    setSearchQuery('')
  }

  const activeFilterCount = Object.keys(localFilters).filter(
    (key) => localFilters[key as keyof ConversationFilters] !== undefined
  ).length

  return (
    <div className="space-y-3">
      {/* Search Input */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search conversations..."
          className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 text-sm"
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery('')}
            className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Filter Toggle Button */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center gap-2 text-sm text-gray-700 hover:text-gray-900"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
          </svg>
          <span>Filters</span>
          {activeFilterCount > 0 && (
            <span className="inline-flex items-center justify-center w-5 h-5 text-xs font-medium text-white bg-blue-600 rounded-full">
              {activeFilterCount}
            </span>
          )}
        </button>

        {activeFilterCount > 0 && (
          <button
            onClick={handleClearFilters}
            className="text-xs text-blue-600 hover:text-blue-700"
          >
            Clear all
          </button>
        )}
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="bg-gray-50 rounded-lg p-4 space-y-4 border border-gray-200">
          {/* Status Filters */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">Status</label>
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={localFilters.is_favorite || false}
                  onChange={(e) => handleFilterChange('is_favorite', e.target.checked || undefined)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="ml-2 text-sm text-gray-700">Favorites only</span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={localFilters.is_archived === false}
                  onChange={(e) => handleFilterChange('is_archived', e.target.checked ? false : undefined)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="ml-2 text-sm text-gray-700">Hide archived</span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={localFilters.is_archived === true}
                  onChange={(e) => handleFilterChange('is_archived', e.target.checked ? true : undefined)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="ml-2 text-sm text-gray-700">Archived only</span>
              </label>
            </div>
          </div>

          {/* Date Range */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">Date Range</label>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-gray-600 mb-1">From</label>
                <input
                  type="date"
                  value={localFilters.date_from || ''}
                  onChange={(e) => handleFilterChange('date_from', e.target.value || undefined)}
                  className="block w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">To</label>
                <input
                  type="date"
                  value={localFilters.date_to || ''}
                  onChange={(e) => handleFilterChange('date_to', e.target.value || undefined)}
                  className="block w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Quick Date Filters */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">Quick Filters</label>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => {
                  const today = new Date().toISOString().split('T')[0]
                  handleFilterChange('date_from', today)
                  handleFilterChange('date_to', today)
                }}
                className="px-3 py-1 text-xs bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Today
              </button>
              <button
                onClick={() => {
                  const weekAgo = new Date()
                  weekAgo.setDate(weekAgo.getDate() - 7)
                  handleFilterChange('date_from', weekAgo.toISOString().split('T')[0])
                  handleFilterChange('date_to', undefined)
                }}
                className="px-3 py-1 text-xs bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Last 7 days
              </button>
              <button
                onClick={() => {
                  const monthAgo = new Date()
                  monthAgo.setMonth(monthAgo.getMonth() - 1)
                  handleFilterChange('date_from', monthAgo.toISOString().split('T')[0])
                  handleFilterChange('date_to', undefined)
                }}
                className="px-3 py-1 text-xs bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Last 30 days
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
