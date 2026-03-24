/**
 * Guest User Authentication Utility
 *
 * Manages user identification for conversation tracking.
 * When a user is authenticated, their email is used as the user ID.
 * Falls back to 'guest' for unauthenticated sessions.
 */

const GUEST_USER_ID_KEY = 'guestUserId';
const AUTH_USER_ID_KEY = 'authUserId';

/**
 * Generate a new UUID v4
 */
function generateUUID(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

/**
 * Set the authenticated user's ID (email) in localStorage.
 * Call this after successful login / fetching user info.
 */
export function setAuthUserId(email: string): void {
  if (typeof window !== 'undefined' && email) {
    localStorage.setItem(AUTH_USER_ID_KEY, email);
  }
}

/**
 * Clear the authenticated user's ID from localStorage.
 * Call this on logout.
 */
export function clearAuthUserId(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(AUTH_USER_ID_KEY);
  }
}

/**
 * Get the current user ID for conversation tracking.
 *
 * Returns the authenticated user's email if available,
 * otherwise falls back to 'guest'.
 */
export function getOrCreateGuestId(): string {
  if (typeof window === 'undefined') {
    return 'guest';
  }

  // Prefer authenticated user ID (email)
  const authUserId = localStorage.getItem(AUTH_USER_ID_KEY);
  if (authUserId) {
    return authUserId;
  }

  // Fallback for unauthenticated sessions
  return 'guest';
}

/**
 * Get current guest ID without creating a new one
 */
export function getGuestId(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }
  return localStorage.getItem(GUEST_USER_ID_KEY);
}

/**
 * Clear guest user ID (for testing/logout)
 */
export function clearGuestId(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(GUEST_USER_ID_KEY);
    console.log('🗑️ Guest user ID cleared');
  }
}

/**
 * Initialize guest auth on app load
 */
export function initGuestAuth(): void {
  getOrCreateGuestId();
}
