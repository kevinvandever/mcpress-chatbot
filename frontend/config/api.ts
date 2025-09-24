// API configuration
// In production, use Railway backend directly. In development, use local.
export const API_URL = process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== 'undefined' && window.location.hostname === 'mc-press-chatbot.netlify.app'
    ? 'https://mcpress-chatbot-production.up.railway.app'
    : process.env.NODE_ENV === 'production'
      ? 'https://mcpress-chatbot-production.up.railway.app'
      : 'http://localhost:8000');
