'use client'

import { useState, useEffect } from 'react'
import ChatInterface from '@/components/ChatInterface'
import DocumentList from '@/components/DocumentList'
import SearchInterface from '@/components/SearchInterface'
import axios from 'axios'
import { API_URL } from '../config/api'

export default function Home() {
  const [hasDocuments, setHasDocuments] = useState(true) // Always true for demo
  const [activeTab, setActiveTab] = useState<'documents' | 'search'>('search')
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [bookCount, setBookCount] = useState(113)
  const [isLoading, setIsLoading] = useState(true)

  // Check actual document count on load
  useEffect(() => {
    const checkDocuments = async () => {
      try {
        const response = await axios.get(`${API_URL}/api/stats`)
        setBookCount(response.data.books || 113)
        setIsLoading(false)
      } catch (error) {
        console.error('Error checking documents:', error)
        setBookCount(113) // Default to expected count
        setIsLoading(false)
      }
    }
    checkDocuments()
  }, [])

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-900">MC Press Chatbot</h1>
              <span className="ml-4 text-sm text-gray-500">Demo Version</span>
            </div>
            
            {/* Desktop Navigation */}
            <nav className="hidden sm:flex space-x-1">
              <button
                onClick={() => setActiveTab('search')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === 'search'
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                Search & Chat
              </button>
              <button
                onClick={() => setActiveTab('documents')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === 'documents'
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                Browse Books
              </button>
            </nav>

            {/* Mobile menu button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="sm:hidden p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100"
            >
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <div className="sm:hidden border-t border-gray-200">
            <div className="px-2 pt-2 pb-3 space-y-1">
              <button
                onClick={() => {
                  setActiveTab('search')
                  setMobileMenuOpen(false)
                }}
                className={`block w-full text-left px-3 py-2 rounded-md text-base font-medium ${
                  activeTab === 'search'
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                Search & Chat
              </button>
              <button
                onClick={() => {
                  setActiveTab('documents')
                  setMobileMenuOpen(false)
                }}
                className={`block w-full text-left px-3 py-2 rounded-md text-base font-medium ${
                  activeTab === 'documents'
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                Browse Books
              </button>
            </div>
          </div>
        )}
      </header>

      {/* Info Banner */}
      <div className="bg-blue-50 border-b border-blue-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <svg className="h-5 w-5 text-blue-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <span className="text-sm text-blue-800">
                {isLoading ? (
                  "Loading knowledge base..."
                ) : (
                  <>
                    <strong>{bookCount} MC Press technical books</strong> pre-loaded and indexed. 
                    Ask questions about IBM i, AS/400, DB2, RPG, and more!
                  </>
                )}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-6">
          {/* Tab Content */}
          {activeTab === 'search' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Search Knowledge Base</h2>
                <SearchInterface />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Chat with AI Assistant</h2>
                <ChatInterface />
              </div>
            </div>
          )}

          {activeTab === 'documents' && (
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Browse Available Books</h2>
              <DocumentList refreshTrigger={0} onDocumentCountChange={() => {}} />
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-center text-sm text-gray-500">
            MC Press Chatbot Demo - Powered by AI • {bookCount} Technical Books
          </p>
        </div>
      </footer>
    </div>
  )
}