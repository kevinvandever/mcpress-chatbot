/**
 * Guest User Authentication Utility
 *
 * Manages lightweight guest authentication for code upload and chat features.
 * Auto-generates a guest user ID (UUID) on first visit and stores in localStorage.
 *
 * Future: This will be replaced with MCPress SSO token validation when the app
 * is integrated behind MCPressOnline authentication.
 */

const GUEST_USER_ID_KEY = 'guestUserId';

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
 * Get or create guest user ID
 *
 * On first visit, generates a new UUID and stores in localStorage.
 * On subsequent visits, retrieves the existing guest ID.
 *
 * @returns Guest user ID (UUID)
 */
export function getOrCreateGuestId(): string {
  if (typeof window === 'undefined') {
    // Server-side rendering - return temporary ID
    return 'ssr-temp-id';
  }

  let guestId = localStorage.getItem(GUEST_USER_ID_KEY);

  if (!guestId) {
    // First visit - generate new guest ID
    guestId = generateUUID();
    localStorage.setItem(GUEST_USER_ID_KEY, guestId);
    console.log('🆔 New guest user ID created:', guestId);
  }

  return guestId;
}

/**
 * Get current guest ID without creating a new one
 *
 * @returns Guest user ID if exists, null otherwise
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
 *
 * Call this early in app initialization to ensure guest ID is ready
 */
export function initGuestAuth(): void {
  getOrCreateGuestId();
}
