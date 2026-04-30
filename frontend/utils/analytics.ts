declare global {
  interface Window {
    gtag?: (
      command: string,
      action: string,
      params?: Record<string, string | number | boolean>
    ) => void
  }
}

export function toSnakeCase(str: string): string {
  return str.replace(/([a-z])([A-Z])/g, '$1_$2').toLowerCase()
}

export function convertKeysToSnakeCase(
  data: Record<string, string | number | boolean>
): Record<string, string | number | boolean> {
  const result: Record<string, string | number | boolean> = {}
  for (const [key, value] of Object.entries(data)) {
    result[toSnakeCase(key)] = value
  }
  return result
}

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

  // Forward to Google Analytics gtag
  try {
    if (typeof window.gtag === 'function') {
      const gaParams = data ? convertKeysToSnakeCase(data) : undefined
      window.gtag('event', action, gaParams)
    }
  } catch {
    // GA failures must never break the app
  }
}
