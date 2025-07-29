// API configuration that works both locally and through tunnels
export const getApiUrl = () => {
  // Check if we're running through a tunnel
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    
    // If accessing through a tunnel URL, use a different backend tunnel
    if (hostname.includes('trycloudflare.com') || hostname.includes('ngrok')) {
      // We'll update this with the actual backend tunnel URL
      return process.env.NEXT_PUBLIC_TUNNEL_API_URL || 'http://localhost:8000';
    }
  }
  
  // Default local development
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
};

export const API_URL = getApiUrl();