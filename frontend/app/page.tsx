'use client'

import React, { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import ChatInterface, { ChatInterfaceRef } from '@/components/ChatInterface'
import BackToTopButton from '@/components/BackToTopButton'
import { API_URL } from '@/config/api'
import { useAuthRefresh } from '@/hooks/useAuthRefresh'

export default function Home() {
  const [isInitializing, setIsInitializing] = useState(true)
  const [hasDocuments, setHasDocuments] = useState(false)
  const [isCheckingDocuments, setIsCheckingDocuments] = useState(true)
  const [bookCount, setBookCount] = useState(0)
  const [articleCount, setArticleCount] = useState(0)
  const [systemStatus, setSystemStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [userEmail, setUserEmail] = useState<string | null>(null)
  const chatInterfaceRef = useRef<ChatInterfaceRef>(null)
  const router = useRouter()

  // Silent token refresh — schedules refresh ~5 min before JWT expiry
  useAuthRefresh()

  // Fetch user info from cookie-based session — redirect if session is invalid (handles back-button after logout)
  useEffect(() => {
    const fetchUserInfo = async () => {
      try {
        const res = await fetch('/api/auth/me')
        if (res.ok) {
          const data = await res.json()
          setUserEmail(data.email || null)
        } else {
          // Session invalid or expired — redirect to login
          router.replace('/login')
        }
      } catch {
        router.replace('/login')
      }
    }
    fetchUserInfo()
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
          if (Array.isArray(documents)) {
            setBookCount(documents.filter((d: any) => d.document_type === 'book').length)
            setArticleCount(documents.filter((d: any) => d.document_type === 'article').length)
          }
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
        setIsInitializing(false)
      }
    }
    
    checkDocuments()
    // Don't poll continuously - just check once on load
    // const interval = setInterval(checkDocuments, 10000) // Check every 10 seconds
    // return () => clearInterval(interval)
  }, [])

  const handleLogout = async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' })
    } catch {
      // Continue with redirect even if the API call fails
    }
    router.push('/login')
    router.refresh()
  }

  if (isInitializing) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <img src="/mc-chatmaster-logo.png" alt="MC ChatMaster" className="h-12 w-auto mx-auto mb-4" />
          <div className="w-8 h-8 border-4 rounded-full animate-spin mx-auto"
            style={{ borderColor: 'var(--mc-blue-lighter)', borderTopColor: 'var(--mc-blue)' }} />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 overflow-x-hidden">
      {/* Header - MC Press Brand Colors */}
      <header className="header-bg-ovals bg-white shadow-sm border-b" style={{ borderColor: 'var(--border-primary)' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="flex justify-between items-center py-3">
            {/* Logo + Tagline */}
            <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3 min-w-0">
              {/* Logo image + Wordmark */}
              <div className="flex items-center gap-2 shrink-0">
                <img
                  src="/mc-chatmaster-logo.png"
                  alt="MC ChatMaster"
                  className="h-9 sm:h-10 w-auto"
                />
                <span className="text-lg sm:text-xl font-bold text-black tracking-tight">MC</span>
                <span className="text-lg sm:text-xl font-bold mx-0.5" style={{ color: '#EF9537' }}>|</span>
                <span className="text-lg sm:text-xl font-bold" style={{ color: '#990000' }}>CHAT</span>
                <span className="text-lg sm:text-xl font-bold text-black tracking-tight">MASTER</span>
              </div>
              {/* Tagline + Sub-line + Powered note */}
              <div className="flex flex-col min-w-0">
                <span className="text-xs sm:text-sm font-medium text-gray-700 leading-tight truncate">
                  <span className="hidden sm:inline">Instant AI-Powered IBM i Expertise</span>
                  <span className="sm:hidden">AI-Powered IBM i Expertise</span>
                </span>
                <span className="text-[10px] sm:text-xs text-gray-500 leading-tight">Your 24/7 Knowledge Assistant</span>
                <a
                  href="https://mc-store.com/products/mc-chatmaster"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[10px] sm:text-xs hover:underline leading-tight"
                  style={{ color: '#990000' }}
                >
                  Powered by MC Press Knowledge
                </a>
              </div>
            </div>

            {/* Navigation buttons */}
            <div className="flex items-center gap-2 shrink-0">
              {userEmail && (
                <span className="text-sm text-gray-500 hidden sm:inline mr-2">{userEmail}</span>
              )}
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
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 md:py-10 main-bg-ovals">
        <div className="space-y-6 relative z-10">
          {/* Chat Section - Full Width */}
          <div>
              <div className="bg-white rounded-lg shadow-sm border p-6 h-full" style={{ borderColor: 'var(--border-primary)' }}>
                <div className="mb-4">
                  <h2 className="text-xl sm:text-2xl font-bold flex items-center pb-2" style={{ color: 'var(--text-primary)' }}>
                    <svg className="w-6 h-6 mr-2 shrink-0" style={{ color: 'var(--mc-green)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                    MC ChatMaster – Your IBM i Expertise Companion
                  </h2>
                  <div style={{ height: '3px', background: 'linear-gradient(to right, #EF9537, #990000)', borderRadius: '2px', maxWidth: '320px' }} />
                </div>
                
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
                  <div
                    className="mb-4 p-4 rounded-xl border status-bar-tooltip"
                    data-tooltip="Knowledge base auto-updates with every new MC Press publication"
                    style={{
                      borderColor: 'var(--color-success-border)',
                      backgroundColor: 'var(--color-success-bg)'
                    }}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-6 h-6 rounded-full flex items-center justify-center" style={{
                        backgroundColor: 'var(--mc-green)'
                      }}>
                        <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-semibold mb-1 break-words" style={{ color: 'var(--text-primary)' }}>🚀 MC ChatMaster Primed & Continuously Updating!</p>
                        <p className="text-xs break-words" style={{ color: 'var(--color-success-text)' }}>📚 {bookCount} Books & {articleCount}+ Articles Loaded – Fresh Insights Added as MC Press Publishes</p>
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
                      <p className="text-sm font-semibold text-gray-700">Instant Mastery Insights: Try These Expert IBM i &amp; RPG Questions</p>
                    </div>
                    <div className="flex flex-col sm:flex-wrap sm:flex-row gap-2">
                      {/* Interleaved colors for visual rhythm */}
                      <button
                        onClick={() => chatInterfaceRef.current?.setInputValue("How do I modernize legacy RPG code to free-format RPG?")}
                        className="group px-4 py-2 rounded-full text-xs font-medium transition-all transform hover:scale-105 hover:shadow-md focus:ring-2 focus:outline-none text-white"
                        style={{ backgroundColor: '#EF9537' }}
                        onMouseEnter={(e: React.MouseEvent<HTMLButtonElement>) => e.currentTarget.style.backgroundColor = '#d4802e'}
                        onMouseLeave={(e: React.MouseEvent<HTMLButtonElement>) => e.currentTarget.style.backgroundColor = '#EF9537'}
                      >
                        <span className="group-hover:animate-pulse">🔄</span> Modernize Legacy RPG to Free-Format
                      </button>
                      <button
                        onClick={() => chatInterfaceRef.current?.setInputValue("What are the best practices for RPG programming on IBM i?")}
                        className="group px-4 py-2 rounded-full text-xs font-medium transition-all transform hover:scale-105 hover:shadow-md focus:ring-2 focus:outline-none text-white bg-purple-600 hover:bg-purple-700"
                      >
                        <span className="group-hover:animate-pulse">🔧</span> Optimize Your RPG Skills
                      </button>
                      <button
                        onClick={() => chatInterfaceRef.current?.setInputValue("What are the key IBM i system administration tasks and best practices?")}
                        className="group px-4 py-2 rounded-full text-xs font-medium transition-all transform hover:scale-105 hover:shadow-md focus:ring-2 focus:outline-none text-white"
                        style={{ backgroundColor: '#A1A88B' }}
                        onMouseEnter={(e: React.MouseEvent<HTMLButtonElement>) => e.currentTarget.style.backgroundColor = '#8a9175'}
                        onMouseLeave={(e: React.MouseEvent<HTMLButtonElement>) => e.currentTarget.style.backgroundColor = '#A1A88B'}
                      >
                        <span className="group-hover:animate-pulse">⚙️</span> Ace IBM i System Admin
                      </button>
                      <button
                        onClick={() => chatInterfaceRef.current?.setInputValue("How do I configure DB2 on IBM i for optimal performance?")}
                        className="group px-4 py-2 rounded-full text-xs font-medium transition-all transform hover:scale-105 hover:shadow-md focus:ring-2 focus:outline-none text-white"
                        style={{ backgroundColor: '#990000' }}
                        onMouseEnter={(e: React.MouseEvent<HTMLButtonElement>) => e.currentTarget.style.backgroundColor = '#7a0000'}
                        onMouseLeave={(e: React.MouseEvent<HTMLButtonElement>) => e.currentTarget.style.backgroundColor = '#990000'}
                      >
                        <span className="group-hover:animate-pulse">💾</span> Master DB2 Config on IBM i
                      </button>
                      <button
                        onClick={() => chatInterfaceRef.current?.setInputValue("How do I set up high availability with PowerHA on IBM i?")}
                        className="group px-4 py-2 rounded-full text-xs font-medium transition-all transform hover:scale-105 hover:shadow-md focus:ring-2 focus:outline-none text-white bg-purple-600 hover:bg-purple-700"
                      >
                        <span className="group-hover:animate-pulse">🛡️</span> High Availability with PowerHA Essentials
                      </button>
                      <button
                        onClick={() => chatInterfaceRef.current?.setInputValue("How do I secure my IBM i environment and protect against threats?")}
                        className="group px-4 py-2 rounded-full text-xs font-medium transition-all transform hover:scale-105 hover:shadow-md focus:ring-2 focus:outline-none text-white"
                        style={{ backgroundColor: '#A1A88B' }}
                        onMouseEnter={(e: React.MouseEvent<HTMLButtonElement>) => e.currentTarget.style.backgroundColor = '#8a9175'}
                        onMouseLeave={(e: React.MouseEvent<HTMLButtonElement>) => e.currentTarget.style.backgroundColor = '#A1A88B'}
                      >
                        <span className="group-hover:animate-pulse">🔒</span> Secure Your IBM i Environment
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
      <footer className="footer-bg-ovals bg-white border-t mt-auto" style={{ borderColor: 'var(--border-primary)' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 relative z-10">
          <p className="text-center text-sm" style={{ color: 'var(--text-secondary)' }}>
            MC ChatMaster: Instant AI-Powered IBM i Expertise – Powered by{' '}
            <a
              href="https://mcpressonline.com"
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-gray-900"
              style={{ color: 'var(--text-secondary)' }}
            >
              MC Press Online
            </a>
          </p>
          <p className="text-center text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
            <a
              href="https://mcpressonline.com"
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-gray-900"
              style={{ color: 'var(--text-secondary)' }}
            >
              mcpressonline.com
            </a>
            {' • '}
            <a
              href="https://mc-store.com"
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-gray-900"
              style={{ color: 'var(--text-secondary)' }}
            >
              mc-store.com
            </a>
          </p>
          <p className="text-center text-xs mt-2" style={{ color: 'var(--text-secondary)' }}>
            Private • Secure • Continuously Updated Knowledge Base
          </p>
        </div>
      </footer>

      {/* Back to Top Button - Floating navigation */}
      <BackToTopButton threshold={300} />
    </div>
  )
}