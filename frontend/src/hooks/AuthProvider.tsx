import { createContext, useState, useEffect, useCallback, useContext, type ReactNode } from 'react';
import api from '../lib/api';
import type { User, TokenResponse } from '../types';

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<TokenResponse>;
  register: (email: string, password: string, business_name: string) => Promise<TokenResponse>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const token = localStorage.getItem('finpilot_token');

    if (token) {
      api.get<User>('/auth/me')
        .then(r => {
          if (!cancelled) setUser(r.data);
        })
        .catch(() => {
          localStorage.removeItem('finpilot_token');
          if (!cancelled) setUser(null);
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    } else {
      setLoading(false);
    }

    return () => { cancelled = true; };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.post<TokenResponse>('/auth/login', { email, password });
    localStorage.setItem('finpilot_token', res.data.access_token);
    const me = await api.get<User>('/auth/me');
    setUser(me.data);
    return res.data;
  }, []);

  const register = useCallback(async (email: string, password: string, business_name: string) => {
    const res = await api.post<TokenResponse>('/auth/register', { email, password, business_name });
    localStorage.setItem('finpilot_token', res.data.access_token);
    const me = await api.get<User>('/auth/me');
    setUser(me.data);
    return res.data;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('finpilot_token');
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, isAuthenticated: !!user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>');
  return ctx;
}
