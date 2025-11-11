/**
 * Export Service for Story-012
 * Handles conversation export to PDF and Markdown
 */

import { API_URL } from '../config/api'

export interface ExportOptions {
  custom_title?: string
  subtitle?: string
  include_toc?: boolean
  include_timestamps?: boolean
  footer?: string
  page_size?: string
  margin?: string
  font_size?: string
}

export interface ExportRequest {
  conversation_id: string
  format: 'pdf' | 'markdown'
  options?: ExportOptions
}

export interface BulkExportRequest {
  conversation_ids: string[]
  format: 'pdf' | 'markdown'
  options?: ExportOptions
}

/**
 * Export a single conversation
 */
export async function exportConversation(
  conversationId: string,
  format: 'pdf' | 'markdown' = 'pdf',
  options?: ExportOptions
): Promise<Blob> {
  const token = localStorage.getItem('auth_token')

  const requestBody: ExportRequest = {
    conversation_id: conversationId,
    format,
    options,
  }

  const response = await fetch(`${API_URL}/api/conversations/${conversationId}/export`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    },
    body: JSON.stringify(requestBody),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Export failed' }))
    throw new Error(error.detail || 'Failed to export conversation')
  }

  return await response.blob()
}

/**
 * Export multiple conversations
 */
export async function bulkExportConversations(
  conversationIds: string[],
  format: 'pdf' | 'markdown' = 'pdf',
  options?: ExportOptions
): Promise<Blob> {
  const token = localStorage.getItem('auth_token')

  const requestBody: BulkExportRequest = {
    conversation_ids: conversationIds,
    format,
    options,
  }

  const response = await fetch(`${API_URL}/api/conversations/bulk-export`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    },
    body: JSON.stringify(requestBody),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Bulk export failed' }))
    throw new Error(error.detail || 'Failed to export conversations')
  }

  return await response.blob()
}

/**
 * Download a blob as a file
 */
export function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(url)
  document.body.removeChild(a)
}

/**
 * Get export history
 */
export async function getExportHistory() {
  const token = localStorage.getItem('auth_token')

  const response = await fetch(`${API_URL}/api/conversations/exports`, {
    headers: {
      ...(token && { Authorization: `Bearer ${token}` }),
    },
  })

  if (!response.ok) {
    throw new Error('Failed to fetch export history')
  }

  return await response.json()
}
