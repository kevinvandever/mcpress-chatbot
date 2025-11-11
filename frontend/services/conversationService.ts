import { API_URL } from '@/config/api'
import { getOrCreateGuestId } from '@/utils/guestAuth'

// Types matching backend models
export interface Conversation {
  id: string
  user_id: string
  title: string
  summary?: string
  tags: string[]
  is_favorite: boolean
  is_archived: boolean
  message_count: number
  created_at: string
  updated_at: string
  last_message_at: string
}

export interface Message {
  id: string
  conversation_id: string
  role: 'user' | 'assistant'
  content: string
  metadata?: Record<string, any>
  tokens_used?: number
  created_at: string
}

export interface ConversationListResponse {
  conversations: Conversation[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

export interface ConversationDetailResponse {
  conversation: Conversation
  messages: Message[]
}

export interface ConversationStats {
  total_conversations: number
  total_messages: number
  favorite_count: number
  archived_count: number
  most_used_tags: string[]
  conversations_this_week: number
  conversations_this_month: number
}

export interface ConversationFilters {
  is_archived?: boolean
  is_favorite?: boolean
  tags?: string[]
  date_from?: string
  date_to?: string
}

// Get auth token from localStorage
function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('adminToken')
}

// Note: Using getOrCreateGuestId() from guestAuth.ts for user ID
// This ensures consistent user ID across chat and history features

// Build fetch options with auth
function buildFetchOptions(method: string = 'GET', body?: any): RequestInit {
  const options: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
  }

  const token = getAuthToken()
  if (token) {
    options.headers = {
      ...options.headers,
      'Authorization': `Bearer ${token}`,
    }
  }

  if (body) {
    options.body = JSON.stringify(body)
  }

  return options
}

/**
 * List conversations with optional filters and pagination
 */
export async function listConversations(
  filters: ConversationFilters = {},
  page: number = 1,
  per_page: number = 20
): Promise<ConversationListResponse> {
  const userId = getOrCreateGuestId()

  const params = new URLSearchParams({
    user_id: userId,
    page: page.toString(),
    per_page: per_page.toString(),
  })

  if (filters.is_archived !== undefined) {
    params.append('is_archived', filters.is_archived.toString())
  }
  if (filters.is_favorite) {
    params.append('is_favorite', 'true')
  }
  if (filters.tags && filters.tags.length > 0) {
    params.append('tags', filters.tags.join(','))
  }
  if (filters.date_from) {
    params.append('date_from', filters.date_from)
  }
  if (filters.date_to) {
    params.append('date_to', filters.date_to)
  }

  const response = await fetch(
    `${API_URL}/api/conversations?${params.toString()}`,
    buildFetchOptions()
  )

  if (!response.ok) {
    throw new Error(`Failed to fetch conversations: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Get a single conversation with all messages
 */
export async function getConversation(conversationId: string): Promise<ConversationDetailResponse> {
  const userId = getOrCreateGuestId()

  const response = await fetch(
    `${API_URL}/api/conversations/${conversationId}?user_id=${userId}`,
    buildFetchOptions()
  )

  if (!response.ok) {
    throw new Error(`Failed to fetch conversation: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Search conversations by query
 */
export async function searchConversations(
  query: string,
  page: number = 1,
  per_page: number = 20
): Promise<ConversationListResponse> {
  const userId = getOrCreateGuestId()

  const params = new URLSearchParams({
    user_id: userId,
    query,
    page: page.toString(),
    per_page: per_page.toString(),
  })

  const response = await fetch(
    `${API_URL}/api/conversations/search?${params.toString()}`,
    buildFetchOptions()
  )

  if (!response.ok) {
    throw new Error(`Failed to search conversations: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Update conversation metadata
 */
export async function updateConversation(
  conversationId: string,
  updates: Partial<Pick<Conversation, 'title' | 'tags' | 'is_favorite' | 'is_archived'>>
): Promise<Conversation> {
  const userId = getOrCreateGuestId()

  const response = await fetch(
    `${API_URL}/api/conversations/${conversationId}?user_id=${userId}`,
    buildFetchOptions('PUT', updates)
  )

  if (!response.ok) {
    throw new Error(`Failed to update conversation: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Toggle favorite status
 */
export async function toggleFavorite(conversationId: string): Promise<Conversation> {
  const userId = getOrCreateGuestId()

  const response = await fetch(
    `${API_URL}/api/conversations/${conversationId}/favorite?user_id=${userId}`,
    buildFetchOptions('POST')
  )

  if (!response.ok) {
    throw new Error(`Failed to toggle favorite: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Toggle archive status
 */
export async function toggleArchive(conversationId: string): Promise<Conversation> {
  const userId = getOrCreateGuestId()

  const response = await fetch(
    `${API_URL}/api/conversations/${conversationId}/archive?user_id=${userId}`,
    buildFetchOptions('POST')
  )

  if (!response.ok) {
    throw new Error(`Failed to toggle archive: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Delete conversation
 */
export async function deleteConversation(conversationId: string): Promise<void> {
  const userId = getOrCreateGuestId()

  const response = await fetch(
    `${API_URL}/api/conversations/${conversationId}?user_id=${userId}`,
    buildFetchOptions('DELETE')
  )

  if (!response.ok) {
    throw new Error(`Failed to delete conversation: ${response.statusText}`)
  }
}

/**
 * Bulk archive conversations
 */
export async function bulkArchive(conversationIds: string[]): Promise<{ success: boolean; updated: number }> {
  const userId = getOrCreateGuestId()

  const response = await fetch(
    `${API_URL}/api/conversations/bulk/archive?user_id=${userId}`,
    buildFetchOptions('POST', { conversation_ids: conversationIds })
  )

  if (!response.ok) {
    throw new Error(`Failed to bulk archive: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Bulk delete conversations
 */
export async function bulkDelete(conversationIds: string[]): Promise<{ success: boolean; deleted: number }> {
  const userId = getOrCreateGuestId()

  const response = await fetch(
    `${API_URL}/api/conversations/bulk/delete?user_id=${userId}`,
    buildFetchOptions('POST', { conversation_ids: conversationIds })
  )

  if (!response.ok) {
    throw new Error(`Failed to bulk delete: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Bulk tag conversations
 */
export async function bulkTag(
  conversationIds: string[],
  tags: string[]
): Promise<{ success: boolean; updated: number }> {
  const userId = getOrCreateGuestId()

  const response = await fetch(
    `${API_URL}/api/conversations/bulk/tag?user_id=${userId}`,
    buildFetchOptions('POST', { conversation_ids: conversationIds, tags })
  )

  if (!response.ok) {
    throw new Error(`Failed to bulk tag: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Get conversation statistics
 */
export async function getConversationStats(): Promise<ConversationStats> {
  const userId = getOrCreateGuestId()

  const response = await fetch(
    `${API_URL}/api/conversations/stats?user_id=${userId}`,
    buildFetchOptions()
  )

  if (!response.ok) {
    throw new Error(`Failed to fetch stats: ${response.statusText}`)
  }

  return response.json()
}
