// API configuration  
// In production, use Railway backend directly. In development, use local.
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 
  (process.env.NODE_ENV === 'production' 
    ? 'https://mcpress-chatbot-production-569b.up.railway.app'
    : '/api');
