'use client'

import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import BookLink from './BookLink'
import { API_URL } from '../config/api'

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
}

interface ChatInterfaceProps {
  hasDocuments?: boolean
}

export default function ChatInterface({ hasDocuments = false }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const [isReceivingContent, setIsReceivingContent] = useState(false)
  const [selectedBook, setSelectedBook] = useState<string | null>(null)
  const [bookSummary, setBookSummary] = useState<{[key: string]: {count: number, pages: Set<string>}}>({})
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

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
          conversation_id: 'default'
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
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date()
      }])
    } finally {
      setIsStreaming(false)
      setIsReceivingContent(false)
      setAutoScroll(true) // Reset auto-scroll when done
      inputRef.current?.focus()
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
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
    <div className="flex-1 flex flex-col h-full bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Messages Area */}
      <div 
        ref={messagesContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-6 space-y-8 scrollbar-thin relative"
      >
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-16 animate-chat-appear">
            {hasDocuments ? (
              <>
                <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-indigo-100 to-purple-100 rounded-2xl flex items-center justify-center shadow-lg animate-float-subtle">
                  <svg className="w-10 h-10 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </div>
                <p className="text-xl font-semibold text-gray-700">Ready to help! ✨</p>
                <p className="text-base mt-2 text-gray-600">Ask me anything about your MC Press books</p>
              </>
            ) : (
              <div className="max-w-lg">
                <div className="w-24 h-24 mx-auto mb-6 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-3xl flex items-center justify-center shadow-2xl animate-float-subtle">
                  <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                  </svg>
                </div>
                <h2 className="text-3xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent mb-3">Welcome to MC Press Chatbot</h2>
                <p className="text-gray-700 mb-6 text-lg">
                  Your AI assistant for MC Press technical documentation
                </p>
                <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 p-6 rounded-2xl text-sm text-blue-900 shadow-lg">
                  <p className="font-semibold mb-4 text-base">✨ What I can help you with:</p>
                  <ul className="text-left space-y-3" role="list">
                    <li role="listitem" className="flex items-start gap-3 p-2 rounded-lg hover:bg-blue-100 transition-colors">
                      <span className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center flex-shrink-0">
                        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </span>
                      <span className="font-medium">Answer technical questions from documentation</span>
                    </li>
                    <li role="listitem" className="flex items-start gap-3 p-2 rounded-lg hover:bg-green-100 transition-colors">
                      <span className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center flex-shrink-0">
                        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                      </span>
                      <span className="font-medium">Extract and analyze images with OCR</span>
                    </li>
                    <li role="listitem" className="flex items-start gap-3 p-2 rounded-lg hover:bg-purple-100 transition-colors">
                      <span className="w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center flex-shrink-0">
                        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                        </svg>
                      </span>
                      <span className="font-medium">Explain and debug code examples</span>
                    </li>
                    <li role="listitem" className="flex items-start gap-3 p-2 rounded-lg hover:bg-indigo-100 transition-colors">
                      <span className="w-8 h-8 bg-indigo-500 rounded-lg flex items-center justify-center flex-shrink-0">
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
            <div className={`max-w-4xl ${message.role === 'user' ? 'ml-12' : 'mr-12'}`}>
              {/* Message Header */}
              <div className={`flex items-center gap-3 mb-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold shadow-md ${
                  message.role === 'user' 
                    ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white' 
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
              <div className={`rounded-2xl px-6 py-4 shadow-lg transition-all hover:shadow-xl ${
                message.role === 'user'
                  ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white'
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
                          const language = match ? match[1] : 'text'
                          
                          return !inline && match ? (
                            <div className="code-block-wrapper my-4">
                              <div className="code-block-header">
                                <span className="font-semibold">{language.toUpperCase()}</span>
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
                      {message.content}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <p className="whitespace-pre-wrap">{message.content}</p>
                )}
              </div>

              {/* Enhanced Interactive Sources */}
              {message.sources && message.sources.length > 0 && (
                <div className="mt-4">
                  {/* Source Summary Header */}
                  <div className="flex items-center gap-2 mb-3">
                    <div className="flex items-center gap-2 bg-gradient-to-r from-indigo-50 to-purple-50 px-3 py-2 rounded-xl border border-indigo-200">
                      <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                      </svg>
                      <span className="text-sm font-semibold text-indigo-700">
                        {(() => {
                          const uniqueBooks = Array.from(new Set(message.sources.map(s => s.filename)))
                          return uniqueBooks.length === 1 
                            ? `Found in: ${getBookDisplayName(uniqueBooks[0])}`
                            : `Found in ${uniqueBooks.length} books (${message.sources.length} sources)`
                        })()}
                      </span>
                    </div>
                  </div>

                  {/* Interactive Book List */}
                  <div className="space-y-2">
                    {(() => {
                      const bookGroups = message.sources.reduce((groups, source) => {
                        const filename = source.filename
                        if (!groups[filename]) {
                          groups[filename] = []
                        }
                        groups[filename].push(source)
                        return groups
                      }, {} as Record<string, Source[]>)

                      return Object.entries(bookGroups).map(([filename, bookSources]: [string, Source[]]) => (
                        <div key={filename} className="border border-gray-200 rounded-xl overflow-hidden">
                          {/* Clickable Book Header */}
                          <button
                            onClick={() => handleBookClick(filename)}
                            className="w-full flex items-center justify-between p-3 bg-white hover:bg-gray-50 transition-colors group"
                          >
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center flex-shrink-0">
                                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                                </svg>
                              </div>
                              <div className="text-left flex-1 min-w-0">
                                <h3 className="font-semibold text-gray-900 group-hover:text-indigo-600 transition-colors truncate">
                                  {getBookDisplayName(filename)}
                                </h3>
                                <div className="flex items-center gap-2 flex-wrap">
                                  <p className="text-sm text-gray-500">
                                    {bookSources.length} source{bookSources.length !== 1 ? 's' : ''} • 
                                    {(() => {
                                      const pages = [...new Set(bookSources.map(s => s.page).filter(p => p && p !== 'N/A'))]
                                      return pages.length > 0 ? ` Pages ${pages.join(', ')}` : ' Various pages'
                                    })()}
                                  </p>
                                  <BookLink 
                                    url={bookSources[0]?.mc_press_url} 
                                    title={getBookDisplayName(filename)}
                                    className="text-xs"
                                  />
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-1 rounded-full font-medium">
                                {bookSources.length}
                              </span>
                              <svg
                                className={`w-4 h-4 text-gray-400 transition-transform ${
                                  selectedBook === filename ? 'rotate-90' : ''
                                }`}
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                              >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                              </svg>
                            </div>
                          </button>

                          {/* Expandable Source Details */}
                          {selectedBook === filename && (
                            <div className="border-t border-gray-100 bg-gray-50/50 p-3">
                              <div className="space-y-2">
                                <div className="flex items-center justify-between mb-2">
                                  <span className="text-xs font-medium text-gray-700">Source Details:</span>
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      // TODO: Add "Filter future chats to this book" functionality
                                      alert('Feature coming soon: Filter future conversations to this book')
                                    }}
                                    className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
                                  >
                                    Focus on this book →
                                  </button>
                                </div>
                                {bookSources.map((source, i) => (
                                  <div key={i} className="flex items-center gap-2 text-xs text-gray-600 p-2 bg-white rounded-lg">
                                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                                      source.type === 'image' ? 'bg-green-100 text-green-700' :
                                      source.type === 'code' ? 'bg-purple-100 text-purple-700' :
                                      'bg-blue-100 text-blue-700'
                                    }`}>
                                      {source.type === 'image' ? '🖼️' : source.type === 'code' ? '💻' : '📝'} {source.type}
                                    </span>
                                    {source.page && source.page !== 'N/A' && (
                                      <span className="text-gray-500">Page {source.page}</span>
                                    )}
                                    {source.distance && (
                                      <span className="text-gray-500">
                                        {Math.round((1 - source.distance) * 100)}% match
                                      </span>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ))
                    })()}
                  </div>

                  {/* Conversation Context Actions */}
                  {Object.keys(bookSummary).length > 0 && (
                    <div className="mt-4 p-3 bg-blue-50 rounded-xl border border-blue-200">
                      <div className="flex items-start gap-3">
                        <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                          <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        </div>
                        <div className="flex-1">
                          <p className="text-sm text-blue-900 font-medium mb-1">
                            💡 Discovered {Object.keys(bookSummary).length} relevant book{Object.keys(bookSummary).length !== 1 ? 's' : ''}
                          </p>
                          <p className="text-xs text-blue-700 mb-2">
                            These books contain information related to your questions. Click above to explore sources or ask more specific questions about these topics.
                          </p>
                          <div className="flex flex-wrap gap-1">
                            {Object.keys(bookSummary).slice(0, 3).map(filename => (
                              <button
                                key={filename}
                                onClick={() => {
                                  setInput(`Tell me more about ${getBookDisplayName(filename)}`)
                                }}
                                className="text-xs bg-blue-100 hover:bg-blue-200 text-blue-700 px-2 py-1 rounded-md transition-colors"
                              >
                                Explore {getBookDisplayName(filename).split(' ').slice(0, 2).join(' ')}...
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
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
                  <span className="text-xs text-indigo-600 font-medium">thinking...</span>
                </div>
              </div>
              <div className="bg-gradient-to-r from-slate-50 to-gray-50 border border-slate-200 rounded-2xl px-6 py-4 shadow-lg">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-full animate-pulse-dot"></div>
                  <div className="w-3 h-3 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-full animate-pulse-dot-delay-1"></div>
                  <div className="w-3 h-3 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-full animate-pulse-dot-delay-2"></div>
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

        {/* Clear chat button */}
        {messages.length > 0 && (
          <button
            onClick={clearChat}
            className="absolute top-4 right-4 bg-gray-500 text-white p-2 rounded-full shadow-lg hover:bg-gray-600 transition-colors"
            title="Clear chat"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        )}
      </div>
      
      {/* Input Area */}
      <div className="border-t border-gray-200 p-6 bg-gradient-to-r from-white to-gray-50">
        <div className="flex gap-4">
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={hasDocuments ? "Ask me about your MC Press books..." : "Upload documents first to start chatting..."}
              className="w-full px-6 py-4 border-2 border-gray-200 rounded-2xl focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 transition-all text-lg placeholder-gray-400 shadow-sm hover:shadow-md"
              disabled={isStreaming}
            />
            {input && (
              <button
                onClick={() => setInput('')}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
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
            className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-semibold py-4 px-8 rounded-2xl transition-all shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-3 text-lg"
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
        
        <div className="mt-4 flex items-center justify-center gap-4 text-sm text-gray-500">
          <div className="flex items-center gap-2">
            <div className="px-2 py-1 bg-gray-100 rounded-md font-mono text-xs">Enter</div>
            <span>Send message</span>
          </div>
          <div className="w-1 h-1 bg-gray-300 rounded-full"></div>
          <div className="flex items-center gap-2">
            <div className="px-2 py-1 bg-gray-100 rounded-md font-mono text-xs">Shift + Enter</div>
            <span>New line</span>
          </div>
        </div>
      </div>
    </div>
  )
}