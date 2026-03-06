'use client'

import { useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'

/**
 * Silent token refresh hook.
 *
 * On mount, calls GET /api/auth/me to read the JWT `exp` claim.
 * Schedules a setTimeout to fire ~5 minutes before expiry and
 * calls POST /api/auth/refresh.  On success the timer is reset
 * for the new token; on 401/403 the user is redirected to /login.
 */
export function useAuthRefresh() {
  const router = useRouter()
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  // Guard against scheduling after unmount
  const mountedRef = useRef(true)

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const scheduleRefresh = useCallback(
    (expUnix: number) => {
      clearTimer()

      const nowSec = Math.floor(Date.now() / 1000)
      // Refresh 5 minutes (300 s) before expiry
      const refreshAtSec = expUnix - 300
      const delaySec = refreshAtSec - nowSec

      if (delaySec <= 0) {
        // Token is already within the refresh window — refresh immediately
        doRefresh()
        return
      }

      timerRef.current = setTimeout(() => {
        if (mountedRef.current) {
          doRefresh()
        }
      }, delaySec * 1000)
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  )

  const doRefresh = useCallback(async () => {
    try {
      const res = await fetch('/api/auth/refresh', { method: 'POST' })

      if (res.ok) {
        // Refresh succeeded — get new expiry and reschedule
        const meRes = await fetch('/api/auth/me')
        if (meRes.ok) {
          const data = await meRes.json()
          if (data.exp && mountedRef.current) {
            scheduleRefresh(data.exp)
          }
        }
        return
      }

      if (res.status === 403) {
        // Subscription no longer active — redirect with message
        clearTimer()
        router.push('/login?reason=subscription_inactive')
        return
      }

      if (res.status === 401) {
        // Token too expired — redirect to login
        clearTimer()
        router.push('/login')
        return
      }

      // Other errors — don't redirect, just log
      console.warn('Token refresh returned unexpected status:', res.status)
    } catch (err) {
      console.warn('Token refresh failed:', err)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    mountedRef.current = true

    const init = async () => {
      try {
        const res = await fetch('/api/auth/me')
        if (!res.ok) return // middleware will handle redirect if needed

        const data = await res.json()
        if (data.exp && mountedRef.current) {
          scheduleRefresh(data.exp)
        }
      } catch {
        // Silently ignore — middleware handles unauthenticated redirects
      }
    }

    init()

    return () => {
      mountedRef.current = false
      clearTimer()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
}
