'use client'

import { useEffect } from 'react'
import { initGuestAuth } from '../utils/guestAuth'

/**
 * Guest Auth Provider
 *
 * Initializes guest authentication on app load by auto-generating
 * a guest user ID and storing it in localStorage.
 *
 * This component should be included in the root layout to ensure
 * guest auth is ready before any code upload features are accessed.
 */
export default function GuestAuthProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Initialize guest auth on mount
    initGuestAuth()
  }, [])

  return <>{children}</>
}
