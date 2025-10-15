import axios from 'axios'
import { API_URL } from './api'
import { getOrCreateGuestId } from '../utils/guestAuth'

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * Determine if endpoint requires admin auth vs guest auth
 */
function isAdminEndpoint(url: string): boolean {
  // Admin endpoints: /admin/* and /api/code/admin/*
  return url.includes('/admin/')
}

/**
 * Determine if endpoint is a code upload endpoint (requires guest auth)
 */
function isCodeUploadEndpoint(url: string): boolean {
  // Code upload endpoints: /api/code/* (excluding /api/code/admin/*)
  return url.includes('/api/code/') && !url.includes('/api/code/admin/')
}

// Request interceptor to add appropriate auth headers
apiClient.interceptors.request.use(
  (config) => {
    if (typeof window !== 'undefined') {
      const url = config.url || ''

      if (isAdminEndpoint(url)) {
        // Admin endpoints: use Bearer token
        const token = localStorage.getItem('adminToken')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
      } else if (isCodeUploadEndpoint(url)) {
        // Code upload endpoints: use guest ID
        const guestId = getOrCreateGuestId()
        config.headers['X-Guest-User-Id'] = guestId
      }
      // Other endpoints: no auth required
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle auth errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const url = error.config?.url || ''

      if (typeof window !== 'undefined') {
        if (isAdminEndpoint(url)) {
          // Admin auth failed - redirect to admin login
          localStorage.removeItem('adminToken')
          localStorage.removeItem('tokenExpiry')
          if (!window.location.pathname.includes('/login')) {
            window.location.href = '/admin/login'
          }
        } else if (isCodeUploadEndpoint(url)) {
          // Guest auth failed - show friendly error
          console.error('Guest auth failed. Please reload the application.')
          // Could show a toast notification here
        }
      }
    }
    return Promise.reject(error)
  }
)

export default apiClient
