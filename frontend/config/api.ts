// API configuration
// Uses environment variable in production, falls back to Railway URL
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://mcpress-chatbot-production.up.railway.app';

// For local development, you can override with:
// export const API_URL = 'http://localhost:8000';