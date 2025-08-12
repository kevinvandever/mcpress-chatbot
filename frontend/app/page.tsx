'use client'

import { useState, useEffect, useRef } from 'react'
import ChatInterface, { ChatInterfaceRef } from '@/components/ChatInterface'
import SearchInterface from '@/components/SearchInterface'
import { API_URL } from '@/config/api'

export default function Home() {
  const [hasDocuments, setHasDocuments] = useState(false)
  const [isCheckingDocuments, setIsCheckingDocuments] = useState(true)
  const [documentCount, setDocumentCount] = useState(0)
  const [systemStatus, setSystemStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const chatInterfaceRef = useRef<ChatInterfaceRef>(null)
  
  // Check if documents are available
  useEffect(() => {
    const checkDocuments = async () => {
      setIsCheckingDocuments(true)
      setSystemStatus('loading')
      
      try {
        // Remove timeout - let it take as long as it needs
        const response = await fetch(`${API_URL}/documents`)
        if (response.ok) {
          const data = await response.json()
          // Handle nested response format: {documents: {documents: [...]}}
          let documents = data.documents || []
          if (documents.documents) {
            documents = documents.documents
          }
          const docCount = Array.isArray(documents) ? documents.length : 0
          setDocumentCount(docCount)
          setHasDocuments(docCount > 0)
          setSystemStatus('ready')
          console.log(`Found ${docCount} documents in the system`)
        } else {
          // Still set as ready but with no documents
          setHasDocuments(false)
          setSystemStatus('ready')
        }
      } catch (error) {
        console.error('Error checking documents:', error)
        setHasDocuments(false)
        // Don't show error immediately - could just be backend starting
        setSystemStatus('ready')
      } finally {
        setIsCheckingDocuments(false)
      }
    }
    
    checkDocuments()
    // Don't poll continuously - just check once on load
    // const interval = setInterval(checkDocuments, 10000) // Check every 10 seconds
    // return () => clearInterval(interval)
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
            
            {/* Removed navigation - single page app now */}

            {/* Removed mobile menu - no navigation needed */}
          </div>
        </div>

      </header>


      {/* Main Content - Simplified to single page */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-10 gap-6">
            {/* Search Section - 30% */}
            <div className="lg:col-span-3">
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                  <svg className="w-5 h-5 mr-2 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  Quick Search
                </h2>
                <SearchInterface />
              </div>
            </div>
            
            {/* Chat Section - 70% */}
            <div className="lg:col-span-7">
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 h-full">
                <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                  <svg className="w-5 h-5 mr-2 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  AI Assistant
                </h2>
                
                {/* System Status Indicator */}
                {systemStatus === 'loading' && (
                  <div className="mb-4 p-4 rounded-xl border border-blue-200 bg-gradient-to-r from-blue-50 to-indigo-50">
                    <div className="flex items-center gap-3">
                      <div className="w-6 h-6 relative">
                        <div className="w-6 h-6 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-semibold text-blue-900 mb-1">🚀 Initializing MC Press AI...</p>
                        <p className="text-xs text-blue-700">Connecting to document library and preparing knowledge base</p>
                      </div>
                    </div>
                  </div>
                )}
                
                {systemStatus === 'ready' && hasDocuments && (
                  <div className="mb-4 p-4 rounded-xl border border-green-200 bg-gradient-to-r from-green-50 to-emerald-50">
                    <div className="flex items-center gap-3">
                      <div className="w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
                        <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-semibold text-green-900 mb-1">✨ System Ready!</p>
                        <p className="text-xs text-green-700">{documentCount.toLocaleString()} documents loaded and indexed • AI assistant active</p>
                      </div>
                    </div>
                  </div>
                )}
                
                {systemStatus === 'error' && (
                  <div className="mb-4 p-4 rounded-xl border border-red-200 bg-gradient-to-r from-red-50 to-pink-50">
                    <div className="flex items-center gap-3">
                      <div className="w-6 h-6 bg-red-500 rounded-full flex items-center justify-center">
                        <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-semibold text-red-900 mb-1">⚠️ Connection Issue</p>
                        <p className="text-xs text-red-700">Unable to load document library. Please refresh the page.</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Interactive Starter Prompts */}
                {!isCheckingDocuments && hasDocuments && (
                  <div className="mb-6 p-4 bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl border border-gray-200">
                    <div className="flex items-center gap-2 mb-3">
                      <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                      <p className="text-sm font-semibold text-gray-700">Quick Start - Try these questions:</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => chatInterfaceRef.current?.setInputValue("How do I configure DB2 on IBM i?")}
                        className="group px-4 py-2 bg-gradient-to-r from-blue-100 to-blue-200 hover:from-blue-200 hover:to-blue-300 text-blue-800 rounded-full text-xs font-medium transition-all transform hover:scale-105 hover:shadow-md focus:ring-2 focus:ring-blue-300 focus:outline-none"
                      >
                        <span className="group-hover:animate-pulse">💾</span> "How do I configure DB2 on IBM i?"
                      </button>
                      <button
                        onClick={() => chatInterfaceRef.current?.setInputValue("RPG programming best practices")}
                        className="group px-4 py-2 bg-gradient-to-r from-green-100 to-green-200 hover:from-green-200 hover:to-green-300 text-green-800 rounded-full text-xs font-medium transition-all transform hover:scale-105 hover:shadow-md focus:ring-2 focus:ring-green-300 focus:outline-none"
                      >
                        <span className="group-hover:animate-pulse">🔧</span> "RPG programming best practices"
                      </button>
                      <button
                        onClick={() => chatInterfaceRef.current?.setInputValue("AS/400 system administration")}
                        className="group px-4 py-2 bg-gradient-to-r from-purple-100 to-purple-200 hover:from-purple-200 hover:to-purple-300 text-purple-800 rounded-full text-xs font-medium transition-all transform hover:scale-105 hover:shadow-md focus:ring-2 focus:ring-purple-300 focus:outline-none"
                      >
                        <span className="group-hover:animate-pulse">⚙️</span> "AS/400 system administration"
                      </button>
                      <button
                        onClick={() => chatInterfaceRef.current?.setInputValue("Show me code examples for JSON handling")}
                        className="group px-4 py-2 bg-gradient-to-r from-orange-100 to-orange-200 hover:from-orange-200 hover:to-orange-300 text-orange-800 rounded-full text-xs font-medium transition-all transform hover:scale-105 hover:shadow-md focus:ring-2 focus:ring-orange-300 focus:outline-none"
                      >
                        <span className="group-hover:animate-pulse">💻</span> "Show me code examples for JSON handling"
                      </button>
                    </div>
                  </div>
                )}
                
                <ChatInterface ref={chatInterfaceRef} hasDocuments={hasDocuments} />
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-center text-sm text-gray-500">
            MC Press Chatbot Demo - Powered by AI
          </p>
        </div>
      </footer>
    </div>
  )
}