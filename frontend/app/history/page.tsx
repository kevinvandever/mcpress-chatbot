'use client'

import React, { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import ConversationList from '@/components/ConversationList'
import ConversationDetail from '@/components/ConversationDetail'
import ConversationSearch from '@/components/ConversationSearch'
import { listConversations, searchConversations, getConversationStats } from '@/services/conversationService'
import type { Conversation, ConversationFilters, ConversationStats } from '@/services/conversationService'

export default function HistoryPage() {
  const router = useRouter()
  const searchParams = useSearchParams()

  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [stats, setStats] = useState<ConversationStats | null>(null)

  // Pagination
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalConversations, setTotalConversations] = useState(0)
  const perPage = 20

  // Filters
  const [filters, setFilters] = useState<ConversationFilters>({})
  const [searchQuery, setSearchQuery] = useState('')

  // Check authentication
  useEffect(() => {
    const adminToken = typeof window !== 'undefined' ? localStorage.getItem('adminToken') : null
    if (!adminToken) {
      router.push('/admin/login?redirect=/history')
      return
    }
  }, [router])

  // Load stats on mount
  useEffect(() => {
    loadStats()
  }, [])

  // Load conversations when filters/search change
  useEffect(() => {
    loadConversations()
  }, [currentPage, filters, searchQuery])

  // Handle conversation selection from URL
  useEffect(() => {
    const convId = searchParams.get('id')
    if (convId) {
      setSelectedConversationId(convId)
    }
  }, [searchParams])

  const loadStats = async () => {
    try {
      const statsData = await getConversationStats()
      setStats(statsData)
    } catch (err) {
      console.error('Failed to load stats:', err)
    }
  }

  const loadConversations = async () => {
    setIsLoading(true)
    setError(null)

    try {
      let response
      if (searchQuery.trim()) {
        response = await searchConversations(searchQuery, currentPage, perPage)
      } else {
        response = await listConversations(filters, currentPage, perPage)
      }

      setConversations(response.conversations)
      setTotalPages(response.total_pages)
      setTotalConversations(response.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversations')
      setConversations([])
    } finally {
      setIsLoading(false)
    }
  }

  const handleConversationSelect = (conversationId: string) => {
    setSelectedConversationId(conversationId)
    // Update URL
    window.history.pushState({}, '', `/history?id=${conversationId}`)
  }

  const handleConversationClose = () => {
    setSelectedConversationId(null)
    // Update URL
    window.history.pushState({}, '', '/history')
  }

  const handleConversationUpdate = () => {
    // Reload conversations after update
    loadConversations()
    loadStats()
  }

  const handleConversationDelete = () => {
    // Close detail view and reload list
    setSelectedConversationId(null)
    window.history.pushState({}, '', '/history')
    loadConversations()
    loadStats()
  }

  const handleSearch = (query: string) => {
    setSearchQuery(query)
    setCurrentPage(1) // Reset to first page
  }

  const handleFilterChange = (newFilters: ConversationFilters) => {
    setFilters(newFilters)
    setCurrentPage(1) // Reset to first page
  }

  const handlePageChange = (page: number) => {
    setCurrentPage(page)
  }

  const handleBackToChat = () => {
    router.push('/')
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b" style={{ borderColor: 'var(--border-primary)' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-4">
              <button
                onClick={handleBackToChat}
                className="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                <span className="hidden sm:inline">Back to Chat</span>
              </button>
              <h1 className="text-2xl font-bold" style={{ color: 'var(--mc-blue-darker)' }}>
                Conversation History
              </h1>
            </div>

            {/* Stats Summary */}
            {stats && (
              <div className="hidden md:flex items-center gap-6 text-sm text-gray-600">
                <div>
                  <span className="font-medium">{stats.total_conversations}</span> conversations
                </div>
                <div>
                  <span className="font-medium">{stats.total_messages}</span> messages
                </div>
                {stats.favorite_count > 0 && (
                  <div>
                    <span className="font-medium">{stats.favorite_count}</span> favorites
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Conversation List Sidebar */}
        <div className={`${selectedConversationId ? 'hidden lg:block' : 'block'} w-full lg:w-96 bg-white border-r overflow-y-auto`}>
          <div className="p-4 space-y-4">
            {/* Search and Filters */}
            <ConversationSearch
              onSearch={handleSearch}
              onFilterChange={handleFilterChange}
              currentFilters={filters}
            />

            {/* Conversation List */}
            {error && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {error}
              </div>
            )}

            <ConversationList
              conversations={conversations}
              selectedId={selectedConversationId}
              onSelect={handleConversationSelect}
              isLoading={isLoading}
              currentPage={currentPage}
              totalPages={totalPages}
              totalConversations={totalConversations}
              onPageChange={handlePageChange}
            />
          </div>
        </div>

        {/* Conversation Detail View */}
        <div className={`${selectedConversationId ? 'block' : 'hidden lg:flex'} flex-1 lg:flex flex-col items-center justify-center bg-gray-50`}>
          {selectedConversationId ? (
            <ConversationDetail
              conversationId={selectedConversationId}
              onClose={handleConversationClose}
              onUpdate={handleConversationUpdate}
              onDelete={handleConversationDelete}
            />
          ) : (
            <div className="text-center p-8">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              <h3 className="mt-2 text-sm font-medium text-gray-900">No conversation selected</h3>
              <p className="mt-1 text-sm text-gray-500">Select a conversation from the list to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
