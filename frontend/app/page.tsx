'use client'

import { useState, useEffect } from 'react'
import ChatInterface from '@/components/ChatInterface'
import SearchInterface from '@/components/SearchInterface'
import { API_URL } from '@/config/api'

export default function Home() {
  const [hasDocuments, setHasDocuments] = useState(false)
  
  // Check if documents are available
  useEffect(() => {
    const checkDocuments = async () => {
      try {
        const response = await fetch(`${API_URL}/documents`)
        if (response.ok) {
          const data = await response.json()
          // Handle nested response format: {documents: {documents: [...]}}
          let documents = data.documents || []
          if (documents.documents) {
            documents = documents.documents
          }
          setHasDocuments(Array.isArray(documents) && documents.length > 0)
          console.log(`Found ${documents.length} documents in the system`)
        }
      } catch (error) {
        console.error('Error checking documents:', error)
        setHasDocuments(false)
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
                
                {/* Starter Prompts */}
                <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-600 mb-3">Try asking about:</p>
                  <div className="flex flex-wrap gap-2">
                    <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-xs cursor-pointer hover:bg-blue-200 transition-colors">
                      "How do I configure DB2 on IBM i?"
                    </span>
                    <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-xs cursor-pointer hover:bg-green-200 transition-colors">
                      "RPG programming best practices"
                    </span>
                    <span className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-xs cursor-pointer hover:bg-purple-200 transition-colors">
                      "AS/400 system administration"
                    </span>
                  </div>
                </div>
                
                <ChatInterface hasDocuments={hasDocuments} />
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