'use client'

import { useState, useEffect } from 'react'
import FileUpload from '@/components/FileUpload'
import BatchUpload from '@/components/BatchUpload'
import ChatInterface from '@/components/ChatInterface'
import DocumentList from '@/components/DocumentList'
import SearchInterface from '@/components/SearchInterface'
import axios from 'axios'

export default function Home() {
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([])
  const [hasDocuments, setHasDocuments] = useState(false)
  const [refreshDocuments, setRefreshDocuments] = useState(0)
  const [activeTab, setActiveTab] = useState<'documents' | 'search' | 'batch'>('search')
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [isAdmin, setIsAdmin] = useState(false)
  const [adminPassword, setAdminPassword] = useState('')
  const [showAdminLogin, setShowAdminLogin] = useState(false)

  // Initialize document state on page load
  useEffect(() => {
    const checkInitialDocuments = async () => {
      try {
        const response = await axios.get('http://localhost:8000/documents')
        const documents = response.data.documents || []
        setHasDocuments(documents.length > 0)
      } catch (error) {
        console.error('Error checking initial documents:', error)
        setHasDocuments(false)
      }
    }
    checkInitialDocuments()
  }, [])

  const handleUploadSuccess = (filename: string) => {
    setUploadedFiles([...uploadedFiles, filename])
    setRefreshDocuments(prev => prev + 1)
    setHasDocuments(true)
  }

  const handleDocumentChange = (documentCount: number) => {
    setHasDocuments(documentCount > 0)
  }

  const handleSearchResultSelect = (result: any) => {
    // TODO: Implement search result selection (e.g., start chat with context)
    console.log('Selected search result:', result)
  }

  // Keyboard navigation handlers
  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Toggle mobile menu with Escape key
    if (e.key === 'Escape' && mobileMenuOpen) {
      setMobileMenuOpen(false)
    }
    
    // Switch tabs with keyboard shortcuts
    if (e.key === '1' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      setActiveTab('documents')
    } else if (e.key === '2' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      setActiveTab('search')
    }
  }

  // Focus management
  const handleTabChange = (tab: 'documents' | 'search' | 'batch') => {
    setActiveTab(tab)
    // Announce tab change to screen readers
    const announcement = `Switched to ${tab} tab`
    const ariaLive = document.getElementById('tab-announcement')
    if (ariaLive) {
      ariaLive.textContent = announcement
    }
  }

  return (
    <div className="h-screen flex flex-col bg-gradient-to-br from-gray-50 via-white to-gray-100" onKeyDown={handleKeyDown}>
      {/* Screen reader announcements */}
      <div id="tab-announcement" aria-live="polite" aria-atomic="true" className="sr-only"></div>
      
      {/* Skip to main content link */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 z-50 bg-blue-600 text-white px-4 py-2 rounded-md focus-ring"
      >
        Skip to main content
      </a>
      
      {/* Header */}
      <header className="mc-gradient border-b border-gray-700 px-4 py-4 sm:px-6 shadow-lg" role="banner">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 bg-white/10 backdrop-blur rounded-xl flex items-center justify-center border border-white/20" aria-hidden="true">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                  MC Press Chatbot
                  <span className="text-sm bg-orange-500 px-2 py-1 rounded-full font-normal">AI</span>
                </h1>
                <p className="text-sm text-gray-200 hidden sm:block">Technical documentation assistant for developers</p>
              </div>
            </div>
          </div>
          
          {/* Mobile menu button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-3 rounded-xl text-white/80 hover:text-white hover:bg-white/10 transition-colors backdrop-blur"
            aria-expanded={mobileMenuOpen}
            aria-controls="mobile-menu"
            aria-label={mobileMenuOpen ? 'Close mobile menu' : 'Open mobile menu'}
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={mobileMenuOpen ? "M6 18L18 6M6 6l12 12" : "M4 6h16M4 12h16M4 18h16"} />
            </svg>
          </button>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <aside 
          id="mobile-menu"
          className={`${
            mobileMenuOpen ? 'block' : 'hidden'
          } md:block w-full md:w-80 bg-gradient-to-b from-slate-800 to-slate-900 border-r border-slate-600 flex flex-col shadow-xl`}
          role="complementary"
          aria-label="Document management sidebar"
        >
          
          {/* Upload Section - Admin Only */}
          {isAdmin ? (
            <section className="p-5 border-b border-slate-600">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                  <svg className="w-5 h-5 text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  Upload Documents
                </h2>
                <button
                  onClick={() => setIsAdmin(false)}
                  className="text-xs text-gray-300 hover:text-white bg-slate-700 hover:bg-slate-600 px-2 py-1 rounded transition-colors"
                  title="Sign out from admin"
                >
                  Sign out
                </button>
              </div>
              <FileUpload onUploadSuccess={handleUploadSuccess} />
            </section>
          ) : (
            <section className="p-5 border-b border-slate-600">
              <div className="text-center">
                <div className="w-14 h-14 mx-auto mb-4 bg-slate-700/50 backdrop-blur rounded-xl flex items-center justify-center border border-slate-600">
                  <svg className="w-7 h-7 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
                <p className="text-sm text-gray-300 mb-4">Admin access required for uploads</p>
                {!showAdminLogin ? (
                  <button
                    onClick={() => setShowAdminLogin(true)}
                    className="text-orange-400 hover:text-orange-300 text-sm font-medium transition-colors"
                  >
                    Admin Login
                  </button>
                ) : (
                  <div className="space-y-3">
                    <input
                      type="password"
                      value={adminPassword}
                      onChange={(e) => setAdminPassword(e.target.value)}
                      placeholder="Admin password"
                      className="w-full px-3 py-2 text-sm bg-slate-700/50 border border-slate-600 rounded-md text-white placeholder-gray-400 focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          if (adminPassword === 'mcpress123') {
                            setIsAdmin(true)
                            setShowAdminLogin(false)
                            setAdminPassword('')
                          } else {
                            alert('Invalid password')
                            setAdminPassword('')
                          }
                        }
                      }}
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={() => {
                          if (adminPassword === 'mcpress123') {
                            setIsAdmin(true)
                            setShowAdminLogin(false)
                            setAdminPassword('')
                          } else {
                            alert('Invalid password')
                            setAdminPassword('')
                          }
                        }}
                        className="flex-1 px-3 py-2 text-sm bg-orange-600 text-white rounded-md hover:bg-orange-700 transition-colors"
                      >
                        Login
                      </button>
                      <button
                        onClick={() => {
                          setShowAdminLogin(false)
                          setAdminPassword('')
                        }}
                        className="flex-1 px-3 py-2 text-sm bg-slate-600 text-gray-200 rounded-md hover:bg-slate-500 transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Tab Navigation */}
          <nav className="flex bg-slate-700/50 border-b border-slate-600" role="tablist" aria-label="Document navigation">
            <button
              onClick={() => handleTabChange('documents')}
              className={`${isAdmin ? 'flex-1' : 'w-1/2'} sidebar-tab ${
                activeTab === 'documents'
                  ? 'sidebar-tab-active'
                  : 'sidebar-tab-inactive'
              }`}
              role="tab"
              aria-selected={activeTab === 'documents'}
              aria-controls="documents-panel"
              id="documents-tab"
              tabIndex={activeTab === 'documents' ? 0 : -1}
            >
              <span className="flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Documents
              </span>
            </button>
            {isAdmin && (
              <button
                onClick={() => handleTabChange('batch')}
                className={`flex-1 sidebar-tab ${
                  activeTab === 'batch'
                    ? 'sidebar-tab-active'
                    : 'sidebar-tab-inactive'
                }`}
                role="tab"
                aria-selected={activeTab === 'batch'}
                aria-controls="batch-panel"
                id="batch-tab"
                tabIndex={activeTab === 'batch' ? 0 : -1}
              >
                <span className="flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                  Batch Upload
                </span>
              </button>
            )}
            <button
              onClick={() => handleTabChange('search')}
              className={`${isAdmin ? 'flex-1' : 'w-1/2'} sidebar-tab ${
                activeTab === 'search'
                  ? 'sidebar-tab-active'
                  : 'sidebar-tab-inactive'
              }`}
              role="tab"
              aria-selected={activeTab === 'search'}
              aria-controls="search-panel"
              id="search-tab"
              tabIndex={activeTab === 'search' ? 0 : -1}
            >
              <span className="flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                Search
              </span>
            </button>
          </nav>

          {/* Tab Content */}
          <div className="flex-1 overflow-hidden bg-gradient-to-b from-white to-gray-50">
            {activeTab === 'documents' && (
              <div 
                id="documents-panel"
                className="p-5 h-full overflow-y-auto scrollbar-thin"
                role="tabpanel"
                aria-labelledby="documents-tab"
                tabIndex={0}
              >
                <DocumentList key={refreshDocuments} onDocumentChange={handleDocumentChange} />
              </div>
            )}
            {activeTab === 'batch' && isAdmin && (
              <div 
                id="batch-panel"
                className="p-5 h-full overflow-y-auto scrollbar-thin"
                role="tabpanel"
                aria-labelledby="batch-tab"
                tabIndex={0}
              >
                <BatchUpload onUploadComplete={() => {
                  setRefreshDocuments(prev => prev + 1)
                  setHasDocuments(true)
                }} />
              </div>
            )}
            {activeTab === 'search' && (
              <div 
                id="search-panel"
                className="p-5 h-full overflow-y-auto scrollbar-thin"
                role="tabpanel"
                aria-labelledby="search-tab"
                tabIndex={0}
              >
                <SearchInterface onResultSelect={handleSearchResultSelect} />
              </div>
            )}
          </div>
        </aside>

        {/* Main Content */}
        <main id="main-content" className="flex-1 flex flex-col min-w-0" role="main">
          {/* Chat Interface - Always Available */}
          <ChatInterface hasDocuments={hasDocuments} />
        </main>
      </div>
    </div>
  )
}