'use client'

import React, { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import ChatInterface, { ChatInterfaceRef } from '@/components/ChatInterface'
import { API_URL } from '@/config/api'

export default function Home() {
  const [hasDocuments, setHasDocuments] = useState(false)
  const [isCheckingDocuments, setIsCheckingDocuments] = useState(true)
  const [documentCount, setDocumentCount] = useState(0)
  const [systemStatus, setSystemStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const chatInterfaceRef = useRef<ChatInterfaceRef>(null)
  const router = useRouter()

  // Check admin authentication - entire site requires admin login
  useEffect(() => {
    const adminToken = typeof window !== 'undefined' ? localStorage.getItem('adminToken') : null

    if (!adminToken) {
      router.push('/admin/login?redirect=/')
      return
    }
  }, [router])

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

  const handleLogout = () => {
    // Clear admin token and redirect to admin login
    if (typeof window !== 'undefined') {
      localStorage.removeItem('adminToken')
      localStorage.removeItem('tokenExpiry')
    }
    router.push('/admin/login')
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Header - MC Press Brand Colors */}
      <header className="bg-white shadow-sm border-b" style={{ borderColor: 'var(--border-primary)' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold" style={{ color: 'var(--mc-blue-darker)' }}>MC Press Chatbot</h1>
              <span className="ml-4 text-sm" style={{ color: 'var(--text-secondary)' }}>Demo Version</span>
            </div>

            {/* Navigation buttons */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => router.push('/history')}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                title="View conversation history"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="hidden sm:inline">History</span>
              </button>

              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                title="Logout"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </div>
        </div>

      </header>


      {/* Main Content - Simplified to single page */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-6">
          {/* Chat Section - Full Width */}
          <div>
              <div className="bg-white rounded-lg shadow-sm border p-6 h-full" style={{ borderColor: 'var(--border-primary)' }}>
                <h2 className="text-lg font-semibold mb-4 flex items-center" style={{ color: 'var(--text-primary)' }}>
                  <svg className="w-5 h-5 mr-2" style={{ color: 'var(--mc-green)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  AI Assistant
                </h2>
                
                {/* System Status Indicator - MC Press Colors */}
                {systemStatus === 'loading' && (
                  <div className="mb-4 p-4 rounded-xl border" style={{
                    borderColor: 'var(--color-info-border)',
                    backgroundColor: 'var(--color-info-bg)'
                  }}>
                    <div className="flex items-center gap-3">
                      <div className="w-6 h-6 relative">
                        <div className="w-6 h-6 border-4 rounded-full animate-spin" style={{
                          borderColor: 'var(--mc-blue-lighter)',
                          borderTopColor: 'var(--mc-blue)'
                        }}></div>
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>🚀 Initializing MC Press AI...</p>
                        <p className="text-xs" style={{ color: 'var(--color-info-text)' }}>Connecting to document library and preparing knowledge base</p>
                      </div>
                    </div>
                  </div>
                )}
                
                {systemStatus === 'ready' && hasDocuments && (
                  <div className="mb-4 p-4 rounded-xl border" style={{
                    borderColor: 'var(--color-success-border)',
                    backgroundColor: 'var(--color-success-bg)'
                  }}>
                    <div className="flex items-center gap-3">
                      <div className="w-6 h-6 rounded-full flex items-center justify-center" style={{
                        backgroundColor: 'var(--mc-green)'
                      }}>
                        <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>✨ System Ready!</p>
                        <p className="text-xs" style={{ color: 'var(--color-success-text)' }}>{documentCount.toLocaleString()} documents loaded and indexed • AI assistant active</p>
                      </div>
                    </div>
                  </div>
                )}
                
                {systemStatus === 'error' && (
                  <div className="mb-4 p-4 rounded-xl border" style={{
                    borderColor: 'var(--color-danger-border)',
                    backgroundColor: 'var(--color-danger-bg)'
                  }}>
                    <div className="flex items-center gap-3">
                      <div className="w-6 h-6 rounded-full flex items-center justify-center" style={{
                        backgroundColor: 'var(--mc-red)'
                      }}>
                        <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-semibold mb-1" style={{ color: 'var(--color-danger-text)' }}>⚠️ Connection Issue</p>
                        <p className="text-xs" style={{ color: 'var(--color-danger-text)' }}>Unable to load document library. Please refresh the page.</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Interactive Starter Prompts - MC Press Brand Colors */}
                {!isCheckingDocuments && hasDocuments && (
                  <div className="mb-6 p-4 bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl border-[var(--border-primary)]">
                    <div className="flex items-center gap-2 mb-3">
                      <svg className="w-4 h-4" style={{ color: 'var(--mc-blue)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                      <p className="text-sm font-semibold text-gray-700">Quick Start - Try these questions:</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => chatInterfaceRef.current?.setInputValue("How do I configure DB2 on IBM i?")}
                        className="group px-4 py-2 rounded-full text-xs font-medium transition-all transform hover:scale-105 hover:shadow-md focus:ring-2 focus:outline-none text-white"
                        style={{
                          backgroundColor: 'var(--mc-blue)'
                        }}
                        onMouseEnter={(e: React.MouseEvent<HTMLButtonElement>) => e.currentTarget.style.backgroundColor = 'var(--mc-blue-dark)'}
                        onMouseLeave={(e: React.MouseEvent<HTMLButtonElement>) => e.currentTarget.style.backgroundColor = 'var(--mc-blue)'}
                      >
                        <span className="group-hover:animate-pulse">💾</span> "How do I configure DB2 on IBM i?"
                      </button>
                      <button
                        onClick={() => chatInterfaceRef.current?.setInputValue("RPG programming best practices")}
                        className="group px-4 py-2 rounded-full text-xs font-medium transition-all transform hover:scale-105 hover:shadow-md focus:ring-2 focus:outline-none text-white"
                        style={{
                          backgroundColor: 'var(--mc-green)'
                        }}
                        onMouseEnter={(e: React.MouseEvent<HTMLButtonElement>) => e.currentTarget.style.backgroundColor = 'var(--mc-green-dark)'}
                        onMouseLeave={(e: React.MouseEvent<HTMLButtonElement>) => e.currentTarget.style.backgroundColor = 'var(--mc-green)'}
                      >
                        <span className="group-hover:animate-pulse">🔧</span> "RPG programming best practices"
                      </button>
                      <button
                        onClick={() => chatInterfaceRef.current?.setInputValue("AS/400 system administration")}
                        className="group px-4 py-2 rounded-full text-xs font-medium transition-all transform hover:scale-105 hover:shadow-md focus:ring-2 focus:outline-none text-white"
                        style={{
                          backgroundColor: 'var(--mc-gray)'
                        }}
                        onMouseEnter={(e: React.MouseEvent<HTMLButtonElement>) => e.currentTarget.style.backgroundColor = 'var(--mc-gray-dark)'}
                        onMouseLeave={(e: React.MouseEvent<HTMLButtonElement>) => e.currentTarget.style.backgroundColor = 'var(--mc-gray)'}
                      >
                        <span className="group-hover:animate-pulse">⚙️</span> "AS/400 system administration"
                      </button>
                      <button
                        onClick={() => chatInterfaceRef.current?.setInputValue("Show me code examples for JSON handling")}
                        className="group px-4 py-2 rounded-full text-xs font-medium transition-all transform hover:scale-105 hover:shadow-md focus:ring-2 focus:outline-none text-white"
                        style={{
                          backgroundColor: 'var(--mc-orange)'
                        }}
                        onMouseEnter={(e: React.MouseEvent<HTMLButtonElement>) => e.currentTarget.style.backgroundColor = 'var(--mc-orange-dark)'}
                        onMouseLeave={(e: React.MouseEvent<HTMLButtonElement>) => e.currentTarget.style.backgroundColor = 'var(--mc-orange)'}
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
      </main>

      {/* Footer - MC Press Brand Colors */}
      <footer className="bg-white border-t mt-auto" style={{ borderColor: 'var(--border-primary)' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-center text-sm" style={{ color: 'var(--text-secondary)' }}>
            MC Press Chatbot Demo - Powered by AI
          </p>
        </div>
      </footer>
    </div>
  )
}