import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';

interface User {
  id: string;
  email: string;
  created_at?: string;
  last_login?: string;
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  token: string | null;
}

export const useAuth = () => {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
    token: null,
  });
  const router = useRouter();

  // Check if token is expired
  const isTokenExpired = useCallback(() => {
    const expiryTime = localStorage.getItem('tokenExpiry');
    if (!expiryTime) return true;
    return Date.now() > parseInt(expiryTime, 10);
  }, []);

  // Verify token with backend
  const verifyToken = useCallback(async (token: string) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/admin/verify`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        return data.user;
      }
      return null;
    } catch (error) {
      console.error('Token verification failed:', error);
      return null;
    }
  }, []);

  // Initialize auth state on mount
  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('adminToken');
      
      if (!token || isTokenExpired()) {
        localStorage.removeItem('adminToken');
        localStorage.removeItem('tokenExpiry');
        setAuthState({
          user: null,
          isLoading: false,
          isAuthenticated: false,
          token: null,
        });
        return;
      }

      const user = await verifyToken(token);
      if (user) {
        setAuthState({
          user,
          isLoading: false,
          isAuthenticated: true,
          token,
        });
      } else {
        localStorage.removeItem('adminToken');
        localStorage.removeItem('tokenExpiry');
        setAuthState({
          user: null,
          isLoading: false,
          isAuthenticated: false,
          token: null,
        });
      }
    };

    initAuth();
  }, [isTokenExpired, verifyToken]);

  // Login function
  const login = useCallback(async (email: string, password: string) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/admin/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (response.ok) {
        localStorage.setItem('adminToken', data.access_token);
        localStorage.setItem('tokenExpiry', String(Date.now() + data.expires_in * 1000));
        
        const user = await verifyToken(data.access_token);
        if (user) {
          setAuthState({
            user,
            isLoading: false,
            isAuthenticated: true,
            token: data.access_token,
          });
        }
        
        return { success: true };
      } else {
        return { success: false, error: data.detail || 'Login failed' };
      }
    } catch (error) {
      return { success: false, error: 'Network error. Please try again.' };
    }
  }, [verifyToken]);

  // Logout function
  const logout = useCallback(async () => {
    const token = localStorage.getItem('adminToken');
    
    if (token) {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        await fetch(`${apiUrl}/api/admin/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
      } catch (error) {
        console.error('Logout error:', error);
      }
    }
    
    localStorage.removeItem('adminToken');
    localStorage.removeItem('tokenExpiry');
    
    setAuthState({
      user: null,
      isLoading: false,
      isAuthenticated: false,
      token: null,
    });
    
    router.push('/admin/login');
  }, [router]);

  // Refresh token function
  const refreshToken = useCallback(async () => {
    const token = localStorage.getItem('adminToken');
    
    if (!token) {
      return false;
    }

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/admin/refresh`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      const data = await response.json();

      if (response.ok) {
        localStorage.setItem('adminToken', data.access_token);
        localStorage.setItem('tokenExpiry', String(Date.now() + data.expires_in * 1000));
        
        setAuthState(prev => ({
          ...prev,
          token: data.access_token,
        }));
        
        return true;
      }
      return false;
    } catch (error) {
      console.error('Token refresh failed:', error);
      return false;
    }
  }, []);

  // Check auth status
  const checkAuth = useCallback(() => {
    if (!authState.isAuthenticated) {
      router.push('/admin/login');
      return false;
    }
    return true;
  }, [authState.isAuthenticated, router]);

  return {
    ...authState,
    login,
    logout,
    refreshToken,
    checkAuth,
    isTokenExpired,
  };
};