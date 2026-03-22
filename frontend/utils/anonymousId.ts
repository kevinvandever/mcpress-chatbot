/**
 * Anonymous User ID Utility
 *
 * Generates and persists a unique anonymous user ID in localStorage.
 * Used by the freemium usage gate to track anonymous question counts
 * via the X-Anonymous-Id header.
 */

const ANON_ID_KEY = 'anonymousUserId'

/**
 * Get or create an anonymous user ID.
 *
 * Reads from localStorage; if missing, generates a new UUID via
 * crypto.randomUUID(), persists it, and returns it.
 * Returns empty string during SSR (no window).
 */
export function getOrCreateAnonymousId(): string {
  if (typeof window === 'undefined') return ''

  let id = localStorage.getItem(ANON_ID_KEY)
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem(ANON_ID_KEY, id)
  }
  return id
}
