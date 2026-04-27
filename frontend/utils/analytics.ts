export function trackEvent(action: string, data?: Record<string, string | number | boolean>): void {
  try {
    const event = new CustomEvent('mc_analytics', {
      detail: { action, ...data, timestamp: Date.now() }
    })
    window.dispatchEvent(event)

    if (process.env.NODE_ENV === 'development') {
      console.log('[Analytics]', action, data)
    }
  } catch {
    // Analytics failures must never break the app
  }
}
