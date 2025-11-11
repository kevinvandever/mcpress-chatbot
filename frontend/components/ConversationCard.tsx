import React from 'react'
import type { Conversation } from '@/services/conversationService'

interface ConversationCardProps {
  conversation: Conversation
  isSelected: boolean
  onSelect: () => void
}

export default function ConversationCard({
  conversation,
  isSelected,
  onSelect,
}: ConversationCardProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffInMs = now.getTime() - date.getTime()
    const diffInHours = diffInMs / (1000 * 60 * 60)
    const diffInDays = diffInMs / (1000 * 60 * 60 * 24)

    if (diffInHours < 24) {
      if (diffInHours < 1) {
        const minutes = Math.floor(diffInMs / (1000 * 60))
        return `${minutes}m ago`
      }
      return `${Math.floor(diffInHours)}h ago`
    } else if (diffInDays < 7) {
      return `${Math.floor(diffInDays)}d ago`
    } else {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    }
  }

  return (
    <div
      onClick={onSelect}
      className={`p-4 rounded-lg border cursor-pointer transition-all ${
        isSelected
          ? 'bg-blue-50 border-blue-500 shadow-sm'
          : 'bg-white border-gray-200 hover:border-gray-300 hover:shadow-sm'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          {/* Title */}
          <h3 className={`font-medium text-sm truncate ${
            isSelected ? 'text-blue-900' : 'text-gray-900'
          }`}>
            {conversation.title}
          </h3>

          {/* Summary */}
          {conversation.summary && (
            <p className="text-xs text-gray-500 mt-1 line-clamp-2">
              {conversation.summary}
            </p>
          )}

          {/* Meta Info */}
          <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
            <span>{conversation.message_count} messages</span>
            <span>•</span>
            <span>{formatDate(conversation.last_message_at)}</span>
          </div>

          {/* Tags */}
          {conversation.tags && conversation.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {conversation.tags.slice(0, 3).map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700"
                >
                  {tag}
                </span>
              ))}
              {conversation.tags.length > 3 && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium text-gray-500">
                  +{conversation.tags.length - 3}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Icons */}
        <div className="flex flex-col items-end gap-1">
          {conversation.is_favorite && (
            <svg className="w-4 h-4 text-yellow-500 fill-current" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
            </svg>
          )}
          {conversation.is_archived && (
            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
            </svg>
          )}
        </div>
      </div>
    </div>
  )
}
