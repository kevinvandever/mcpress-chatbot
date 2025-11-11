'use client'

import { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import BookLink from './BookLink'
import CompactSources from './CompactSources'
import { API_URL } from '../config/api'

// Helper function to get user ID (matches conversationService.ts logic)
function getUserId(): string {
  if (typeof window === 'undefined') return 'guest'

  // Try to get user ID from localStorage
  const userId = localStorage.getItem('userId')
  if (userId) return userId

  // Try to decode from JWT token
  const token = localStorage.getItem('adminToken')
  if (token) {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      return payload.sub || payload.id || 'guest'
    } catch {
      return 'guest'
    }
  }

  return 'guest'
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: any[]
  timestamp: Date
}

interface Source {
  filename: string
  page: string | number
  type?: string
  distance?: number
  mc_press_url?: string
  content_preview?: string
  context?: string
}

interface ChatInterfaceProps {
  hasDocuments?: boolean
}

export interface ChatInterfaceRef {
  setInputValue: (value: string) => void
  focusInput: () => void
}

// Clean text function to fix PDF extraction artifacts
const cleanText = (text: string): string => {
  if (!text) return text
  
  // Comprehensive character mapping for PDF artifacts
  const charMap: { [key: string]: string } = {
    // Ligatures (Unicode private area - most common in PDFs)
    '\uFB00': 'ff', '\uFB01': 'fi', '\uFB02': 'fl', '\uFB03': 'ffi', '\uFB04': 'ffl',
    // Quotes and dashes  
    '\u2013': '-', '\u2014': '--', '\u2015': '--',
    '\u2018': "'", '\u2019': "'", '\u201A': "'", '\u201B': "'",
    '\u201C': '"', '\u201D': '"', '\u201E': '"', '\u201F': '"',
    // Other common artifacts
    '\u2026': '...', '\u00A0': ' ', '\u00AD': '', '\u200B': '',
    // Mathematical symbols that appear as artifacts
    '\u2212': '-', '\u00D7': 'x', '\u00F7': '/', '\u00B1': '+/-',
    // Currency and special symbols  
    '\u00A9': '(c)', '\u00AE': '(r)', '\u2122': '(tm)'
  }
  
  let cleaned = text
  for (const [old, replacement] of Object.entries(charMap)) {
    cleaned = cleaned.replace(new RegExp(old, 'g'), replacement)
  }
  
  return cleaned
}

const ChatInterface = forwardRef<ChatInterfaceRef, ChatInterfaceProps>(({ hasDocuments = false }, ref) => {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const [isReceivingContent, setIsReceivingContent] = useState(false)
  const [selectedBook, setSelectedBook] = useState<string | null>(null)
  const [bookSummary, setBookSummary] = useState<{[key: string]: {count: number, pages: Set<string>}}>({})
  const [sourcePreviewVisible, setSourcePreviewVisible] = useState<{[key: string]: boolean}>({})
  const [copiedText, setCopiedText] = useState<string | null>(null)
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([])
  const [expandedSources, setExpandedSources] = useState<{[key: string]: boolean}>({})
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  
  // Expose methods via ref
  useImperativeHandle(ref, () => ({
    setInputValue: (value: string) => {
      setInput(value)
      inputRef.current?.focus()
    },
    focusInput: () => {
      inputRef.current?.focus()
    }
  }))

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  // Check if user has scrolled up
  const handleScroll = () => {
    if (messagesContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = messagesContainerRef.current
      const isAtBottom = scrollTop + clientHeight >= scrollHeight - 50
      setAutoScroll(isAtBottom)
    }
  }

  useEffect(() => {
    if (autoScroll) {
      scrollToBottom()
    }
  }, [messages, autoScroll])

  const sendMessage = async () => {
    if (!input.trim() || isStreaming) {
      console.log('Blocked send:', { input: input.trim(), isStreaming })
      return
    }

    // Check if there are no documents
    if (!hasDocuments) {
      setMessages(prev => [...prev, 
        { 
          role: 'user', 
          content: input.trim(), 
          timestamp: new Date() 
        },
        { 
          role: 'assistant', 
          content: 'I\'d be happy to help! However, I need you to upload some PDF documents first so I can answer questions about their content. Please use the upload area in the left sidebar to add your PDF documents.',
          timestamp: new Date() 
        }
      ])
      setInput('')
      return
    }

    const userMessage = input.trim()
    setInput('')
    setMessages(prev => [...prev, { 
      role: 'user', 
      content: userMessage, 
      timestamp: new Date() 
    }])
    setIsStreaming(true)
    setIsReceivingContent(false)
    console.log('Sending message:', userMessage)

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
          conversation_id: 'default',
          user_id: getUserId()  // Use same user_id as conversation history
        }),
      })

      if (!response.ok) throw new Error('Failed to send message')

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      let assistantMessage = ''
      let sources: Source[] = []

      // Don't add empty assistant message yet - wait for first content

      if (reader) {
        try {
          while (true) {
            const { done, value } = await reader.read()
            if (done) break

            const chunk = decoder.decode(value)
            const lines = chunk.split('\n')

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const dataStr = line.slice(6).trim()
                if (dataStr === '[DONE]') {
                  break
                }
                
                try {
                  const data = JSON.parse(dataStr)
                  
                  if (data.type === 'content') {
                    assistantMessage += data.content
                    
                    // Hide typing indicator as soon as we receive first content
                    if (!isReceivingContent) {
                      setIsReceivingContent(true)
                    }
                    
                    setMessages(prev => {
                      const newMessages = [...prev]
                      const lastMessage = newMessages[newMessages.length - 1]
                      
                      // If this is the first content and no assistant message exists, create one
                      if (lastMessage?.role !== 'assistant' || !lastMessage) {
                        newMessages.push({
                          role: 'assistant',
                          content: assistantMessage,
                          sources: [],
                          timestamp: new Date()
                        })
                      } else {
                        // Update existing assistant message
                        lastMessage.content = assistantMessage
                      }
                      
                      return newMessages
                    })
                  } else if (data.type === 'done') {
                    sources = data.sources || []
                    setMessages(prev => {
                      const newMessages = [...prev]
                      if (newMessages.length > 0) {
                        newMessages[newMessages.length - 1].sources = sources
                      }
                      return newMessages
                    })
                    // Update book summary with new sources
                    updateBookSummary(sources)
                    // Generate smart suggestions based on sources
                    generateSmartSuggestions(sources)
                  }
                } catch (e) {
                  console.error('Error parsing SSE data:', e, 'Data:', dataStr)
                }
              }
            }
          }
        } catch (streamError) {
          console.error('Stream reading error:', streamError)
          throw streamError
        } finally {
          reader.releaseLock()
        }
      }
    } catch (error) {
      console.error('Error sending message:', error)
      let errorMessage = 'Sorry, I encountered an error. Please try again.'
      
      // Provide more specific error messages based on the error type
      if (error instanceof TypeError && error.message.includes('fetch')) {
        errorMessage = 'Unable to connect to the AI backend. Please check that the backend server is running.'
      } else if (error instanceof Error && error.message.includes('Failed to send message')) {
        errorMessage = 'The message could not be sent. Please check your connection and try again.'
      }
      
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: errorMessage,
        timestamp: new Date()
      }])
    } finally {
      setIsStreaming(false)
      setIsReceivingContent(false)
      setAutoScroll(true) // Reset auto-scroll when done
      inputRef.current?.focus()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedText(text.substring(0, 50) + '...')
      setTimeout(() => setCopiedText(null), 2000)
    } catch (err) {
      console.error('Failed to copy text: ', err)
    }
  }
  
  const getConfidenceLevel = (distance: number): {level: string, color: string, bgColor: string} => {
    const confidence = 1 - distance
    if (confidence >= 0.8) return { level: 'High', color: 'text-green-700', bgColor: 'bg-green-100' }
    if (confidence >= 0.6) return { level: 'Medium', color: 'text-yellow-700', bgColor: 'bg-yellow-100' }
    return { level: 'Low', color: 'text-red-700', bgColor: 'bg-red-100' }
  }
  
  const extractKeywords = (filename: string): string[] => {
    // Extract meaningful keywords from filename
    return filename.replace('.pdf', '').split(/[-_\s]/).filter(word => word.length > 2)
  }
  
  const toggleSourcePreview = (sourceId: string) => {
    setSourcePreviewVisible(prev => ({
      ...prev,
      [sourceId]: !prev[sourceId]
    }))
  }
  
  const generateSmartSuggestions = (sources: Source[]) => {
    const topics = new Set<string>()
    
    sources.forEach(source => {
      const keywords = extractKeywords(source.filename)
      keywords.slice(0, 2).forEach(keyword => {
        if (keyword.length > 3) {
          topics.add(`How does ${keyword} work?`)
          topics.add(`Best practices for ${keyword}`)
          topics.add(`Examples of ${keyword}`)
        }
      })
    })
    
    // Add some generic follow-ups
    topics.add("Can you show me code examples?")
    topics.add("What are the main concepts here?")
    topics.add("How do I implement this?")
    
    setSuggestedQuestions(Array.from(topics).slice(0, 4))
  }
  
  const generateContentPreview = (source: Source, userQuery: string): string => {
    // If we have actual content from the API, use it
    if (source.content_preview) {
      return source.content_preview
    }
    
    // Otherwise generate a meaningful preview based on context
    const filename = source.filename.replace('.pdf', '')
    const keywords = extractKeywords(filename)
    const mainTopic = keywords[0] || 'technical information'
    
    // Generate contextual previews based on content type and query
    const previews = [
      `This section covers ${mainTopic} implementation details, configuration options, and practical examples.`,
      `Contains step-by-step instructions for ${mainTopic} setup, troubleshooting tips, and best practices.`,
      `Explains ${mainTopic} concepts with code examples, use cases, and integration patterns.`,
      `Technical reference for ${mainTopic} including parameters, syntax, and common scenarios.`,
      `Comprehensive guide to ${mainTopic} covering fundamentals, advanced features, and real-world applications.`
    ]
    
    // Select preview based on content type
    if (source.type === 'code') {
      return `Code examples and implementation details for ${mainTopic}. Includes syntax, functions, and practical usage patterns.`
    } else if (source.type === 'image') {
      return `Visual diagrams and illustrations related to ${mainTopic}. Contains charts, screenshots, or technical drawings.`
    }
    
    // Use hash of filename + page to consistently select same preview
    const hash = (filename + source.page).split('').reduce((a, b) => {
      a = ((a << 5) - a) + b.charCodeAt(0)
      return a & a
    }, 0)
    
    return previews[Math.abs(hash) % previews.length]
  }

  const clearChat = () => {
    setMessages([])
    setIsStreaming(false)
    setAutoScroll(true)
    setBookSummary({})
    setSelectedBook(null)
  }

  const updateBookSummary = (sources: Source[]) => {
    const newSummary = { ...bookSummary }
    
    sources.forEach(source => {
      const filename = source.filename
      if (!newSummary[filename]) {
        newSummary[filename] = { count: 0, pages: new Set() }
      }
      newSummary[filename].count += 1
      if (source.page && source.page !== 'N/A') {
        newSummary[filename].pages.add(String(source.page))
      }
    })
    
    setBookSummary(newSummary)
  }

  const handleBookClick = (filename: string) => {
    setSelectedBook(selectedBook === filename ? null : filename)
  }

  const getBookDisplayName = (filename: string) => {
    return filename.replace('.pdf', '').replace(/[-_]/g, ' ')
  }

  const getBooksUsedSummary = () => {
    const books = Object.keys(bookSummary)
    if (books.length === 0) return null
    
    const totalSources = Object.values(bookSummary).reduce((sum, book) => sum + book.count, 0)
    
    return {
      books,
      totalBooks: books.length,
      totalSources,
      summary: books.length === 1 
        ? `Found in ${books[0].replace('.pdf', '')}`
        : `Found in ${books.length} books (${totalSources} sources)`
    }
  }

  const formatTimestamp = (timestamp: Date) => {
    return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className="flex-1 flex flex-col bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Messages Area */}
      <div 
        ref={messagesContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin relative"
      >
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-8 animate-chat-appear">
            {hasDocuments ? (
              <>
                <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-blue-100 to-blue-50 rounded-2xl flex items-center justify-center shadow-lg animate-float-subtle">
                  <svg className="w-10 h-10 text-mc-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </div>
                <p className="text-xl font-semibold text-gray-700">Ready to help! ✨</p>
                <p className="text-base mt-2 text-gray-600">Ask me anything about your MC Press books</p>
              </>
            ) : (
              <div className="max-w-lg">
                <div className="w-24 h-24 mx-auto mb-6 bg-mc-blue rounded-3xl flex items-center justify-center shadow-2xl animate-float-subtle">
                  <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                  </svg>
                </div>
                <h2 className="text-3xl font-bold text-mc-blue mb-3">Welcome to MC Press Chatbot</h2>
                <p className="text-gray-700 mb-6 text-lg">
                  Your AI assistant for MC Press technical documentation
                </p>
                <div className="bg-blue-50 border border-blue-200 p-6 rounded-2xl text-sm text-gray-800 shadow-lg">
                  <p className="font-semibold mb-4 text-base">✨ What I can help you with:</p>
                  <ul className="text-left space-y-3" role="list">
                    <li role="listitem" className="flex items-start gap-3 p-2 rounded-lg hover:bg-blue-100 transition-colors">
                      <span className="w-8 h-8 bg-mc-blue rounded-lg flex items-center justify-center flex-shrink-0">
                        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </span>
                      <span className="font-medium">Answer technical questions from documentation</span>
                    </li>
                    <li role="listitem" className="flex items-start gap-3 p-2 rounded-lg hover:bg-green-100 transition-colors">
                      <span className="w-8 h-8 bg-mc-green rounded-lg flex items-center justify-center flex-shrink-0">
                        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                      </span>
                      <span className="font-medium">Extract and analyze images with OCR</span>
                    </li>
                    <li role="listitem" className="flex items-start gap-3 p-2 rounded-lg hover:bg-orange-100 transition-colors">
                      <span className="w-8 h-8 bg-mc-orange rounded-lg flex items-center justify-center flex-shrink-0">
                        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                        </svg>
                      </span>
                      <span className="font-medium">Explain and debug code examples</span>
                    </li>
                    <li role="listitem" className="flex items-start gap-3 p-2 rounded-lg hover:bg-gray-100 transition-colors">
                      <span className="w-8 h-8 bg-mc-gray rounded-lg flex items-center justify-center flex-shrink-0">
                        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                      </span>
                      <span className="font-medium">Search across your entire library</span>
                    </li>
                  </ul>
                </div>
                <div className="mt-4 text-xs text-gray-500">
                  <p>Keyboard shortcuts: Ctrl+1 (Documents), Ctrl+2 (Search), Escape (Close menu)</p>
                </div>
              </div>
            )}
          </div>
        )}
        
        {messages.map((message, index) => (
          <div key={index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-chat-appear`}>
            <div className={`max-w-4xl ${message.role === 'user' ? 'ml-8' : 'mr-8'}`}>
              {/* Message Header */}
              <div className={`flex items-center gap-2 mb-2 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold shadow-md ${
                  message.role === 'user'
                    ? 'bg-mc-blue text-white'
                    : 'bg-gradient-to-r from-slate-600 to-slate-700 text-white'
                }`}>
                  {message.role === 'user' ? (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                  )}
                </div>
                <div className="flex flex-col">
                  <span className="text-sm font-medium text-gray-700">
                    {message.role === 'user' ? 'You' : 'MC Press AI'}
                  </span>
                  <span className="text-xs text-gray-500">
                    {formatTimestamp(message.timestamp)}
                  </span>
                </div>
              </div>

              {/* Message Content */}
              <div className={`rounded-xl px-4 py-3 shadow-md transition-all hover:shadow-lg ${
                message.role === 'user'
                  ? 'bg-mc-blue text-white'
                  : 'bg-white border border-gray-100 hover:border-gray-200'
              }`}>
                {message.role === 'assistant' ? (
                  <div className="prose prose-sm max-w-none">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        code({ node, className, children, ...props }: any) {
                          const inline = !className
                          const match = /language-(\w+)/.exec(className || '')
                          let language = match ? match[1] : 'text'
                          
                          // Don't show generic or text as language labels
                          let displayLanguage = ''
                          if (language && language !== 'generic' && language !== 'text') {
                            // Special formatting for IBM i languages
                            if (language === 'rpg') {
                              displayLanguage = 'RPG IV'
                            } else if (language === 'dds') {
                              displayLanguage = 'DDS'
                            } else if (language === 'cl') {
                              displayLanguage = 'CL'
                            } else {
                              displayLanguage = language.toUpperCase()
                            }
                          }
                          
                          return !inline && match ? (
                            <div className="code-block-wrapper my-4">
                              <div className="code-block-header">
                                {displayLanguage && <span className="font-semibold">{displayLanguage}</span>}
                                <button
                                  onClick={() => copyToClipboard(String(children))}
                                  className="text-gray-400 hover:text-white transition-colors p-1 rounded hover:bg-gray-700"
                                  title="Copy code"
                                >
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                  </svg>
                                </button>
                              </div>
                              <SyntaxHighlighter
                                style={vscDarkPlus}
                                language={language}
                                PreTag="div"
                                className="!mt-0 !rounded-t-none !bg-gray-900 !text-gray-100"
                                customStyle={{
                                  margin: 0,
                                  borderRadius: 0,
                                  background: '#111827',
                                  color: '#f9fafb',
                                  fontSize: '14px',
                                  lineHeight: '1.5'
                                }}
                                {...props}
                              >
                                {String(children).replace(/\n$/, '')}
                              </SyntaxHighlighter>
                            </div>
                          ) : (
                            <code className="inline-code" {...props}>
                              {children}
                            </code>
                          )
                        },
                        p({ children }) {
                          return <p className="text-gray-800 mb-2 last:mb-0">{children}</p>
                        },
                        ul({ children }) {
                          return <ul className="text-gray-800 space-y-1">{children}</ul>
                        },
                        ol({ children }) {
                          return <ol className="text-gray-800 space-y-1">{children}</ol>
                        },
                        h1({ children }) {
                          return <h1 className="text-xl font-bold text-gray-900 mb-2">{children}</h1>
                        },
                        h2({ children }) {
                          return <h2 className="text-lg font-semibold text-gray-900 mb-2">{children}</h2>
                        },
                        h3({ children }) {
                          return <h3 className="text-base font-semibold text-gray-900 mb-2">{children}</h3>
                        },
                      }}
                    >
                      {cleanText(message.content)}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <p className="whitespace-pre-wrap">{cleanText(message.content)}</p>
                )}
              </div>

              {/* 📚 COMPACT SOURCE CARDS - Much Less Scrolling! */}
              {message.sources && message.sources.length > 0 && (
                <CompactSources sources={message.sources} />
              )}
            </div>
          </div>
        ))}
        
        {/* Typing Indicator */}
        {isStreaming && !isReceivingContent && (
          <div className="flex justify-start animate-chat-appear">
            <div className="mr-12 max-w-4xl">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-8 h-8 rounded-xl bg-gradient-to-r from-slate-600 to-slate-700 flex items-center justify-center shadow-md animate-message-glow">
                  <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <div className="flex flex-col">
                  <span className="text-sm font-medium text-gray-700">MC Press AI</span>
                  <span className="text-xs text-mc-blue font-medium">thinking...</span>
                </div>
              </div>
              <div className="bg-gradient-to-r from-slate-50 to-gray-50 border border-slate-200 rounded-2xl px-6 py-4 shadow-lg">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 bg-mc-blue rounded-full animate-pulse-dot"></div>
                  <div className="w-3 h-3 bg-mc-blue rounded-full animate-pulse-dot-delay-1"></div>
                  <div className="w-3 h-3 bg-mc-blue rounded-full animate-pulse-dot-delay-2"></div>
                </div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
        
        {/* Scroll to bottom button */}
        {!autoScroll && (
          <button
            onClick={scrollToBottom}
            className="absolute bottom-4 right-4 bg-blue-600 text-white p-2 rounded-full shadow-lg hover:bg-blue-700 transition-colors"
            title="Scroll to bottom"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
          </button>
        )}

        {/* Clear chat button - repositioned to avoid conflicts */}
        {messages.length > 0 && !isStreaming && (
          <button
            onClick={clearChat}
            className="absolute top-4 left-4 bg-gray-400/80 hover:bg-red-500 text-white p-2 rounded-lg shadow-md hover:shadow-lg transition-all duration-200 backdrop-blur-sm"
            title="Clear chat history"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        )}
      </div>
      
      {/* Input Area */}
      <div className="border-t border-gray-200 p-6 bg-gradient-to-r from-white to-gray-50 relative">
        <div className="flex gap-4 items-stretch">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={hasDocuments ? "Ask me about your MC Press books..." : "Upload documents first to start chatting..."}
              className="w-full px-6 py-4 border-2 border-gray-200 rounded-2xl focus:border-mc-blue focus:ring-4 focus:ring-blue-100 transition-all text-lg placeholder-gray-400 shadow-sm hover:shadow-md resize-none min-h-[60px] max-h-[120px]"
              disabled={isStreaming}
              rows={1}
              style={{
                height: 'auto',
                minHeight: '60px',
                maxHeight: '120px',
              }}
              onInput={(e) => {
                const target = e.target as HTMLTextAreaElement;
                target.style.height = 'auto';
                target.style.height = Math.min(target.scrollHeight, 120) + 'px';
              }}
            />
            {input && (
              <button
                onClick={() => setInput('')}
                className="absolute right-3 top-4 text-gray-400 hover:text-gray-600 z-10 hover:bg-gray-100 rounded-full p-1"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
          <button
            onClick={sendMessage}
            disabled={!input.trim() || isStreaming}
            className="bg-mc-blue hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-2xl transition-all shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-3 text-base flex-shrink-0 self-end"
          >
            {isStreaming ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                <span>Thinking...</span>
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
                <span>Send</span>
              </>
            )}
          </button>
        </div>
        
        {/* Smart Suggestions - Disabled for now */}
        {false && suggestedQuestions.length > 0 && !isStreaming && (
          <div className="mt-4 animate-slide-in-up">
            <div className="flex items-center gap-2 mb-2">
              <svg className="w-4 h-4 text-mc-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <p className="text-sm font-medium text-gray-700">Continue the conversation:</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {suggestedQuestions.map((question, index) => (
                <button
                  key={index}
                  onClick={() => setInput(question)}
                  className="group px-3 py-2 bg-blue-50 hover:bg-blue-100 border border-blue-200 hover:border-blue-300 text-blue-700 rounded-lg text-xs font-medium transition-all hover:scale-105 hover:shadow-md focus:ring-2 focus:ring-blue-300 focus:outline-none"
                >
                  <span className="group-hover:animate-bounce-subtle">✨</span> {question}
                </button>
              ))}
            </div>
          </div>
        )}
        
      </div>
      
      {/* Keyboard Shortcuts Footer */}
      <div className="px-6 py-3 flex items-center justify-center gap-4 text-sm text-gray-500">
        <div className="flex items-center gap-2">
          <div className="px-2 py-1 bg-gray-100 rounded-md font-mono text-xs">Enter</div>
          <span>Send message</span>
        </div>
        <div className="w-1 h-1 bg-gray-300 rounded-full"></div>
        <div className="flex items-center gap-2">
          <div className="px-2 py-1 bg-gray-100 rounded-md font-mono text-xs">Shift + Enter</div>
          <span>Add new line</span>
        </div>
      </div>
    </div>
  )
})

ChatInterface.displayName = 'ChatInterface'

export default ChatInterface