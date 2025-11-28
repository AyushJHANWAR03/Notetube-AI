'use client';

import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { User } from '@/lib/types';
import api from '@/lib/api';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: () => void;
  logout: () => void;
  setUser: (user: User | null) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const initializedRef = useRef(false);

  useEffect(() => {
    // Prevent double initialization in strict mode
    if (initializedRef.current) return;
    initializedRef.current = true;

    // Check if user is already logged in on mount
    const token = localStorage.getItem('token');
    if (token) {
      fetchUser();
    } else {
      setLoading(false);
    }
  }, []);

  const fetchUser = async () => {
    try {
      const response = await api.get('/api/me');
      setUser(response.data);
    } catch (error: any) {
      console.error('Failed to fetch user:', error);
      // Only remove token on 401 Unauthorized - not on network errors
      if (error.response?.status === 401) {
        localStorage.removeItem('token');
      }
      // For other errors, keep the token - user might still be valid
    } finally {
      setLoading(false);
    }
  };

  const login = () => {
    // Redirect to backend Google OAuth endpoint
    window.location.href = `${process.env.NEXT_PUBLIC_API_URL}/auth/google/login`;
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
    window.location.href = '/';
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
