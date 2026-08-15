import { useState, useEffect, useCallback } from 'react';
import api from '../lib/api';
import type { User, TokenResponse } from '../types';

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('finpilot_token');
    if (token) {
      api.get('/auth/me').then(r => setUser(r.data)).catch(() => {
        localStorage.removeItem('finpilot_token');
      }).finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.post<TokenResponse>('/auth/login', { email, password });
    localStorage.setItem('finpilot_token', res.data.access_token);
    const me = await api.get('/auth/me');
    setUser(me.data);
    return res.data;
  }, []);

  const register = useCallback(async (email: string, password: string, business_name: string) => {
    const res = await api.post<TokenResponse>('/auth/register', { email, password, business_name });
    localStorage.setItem('finpilot_token', res.data.access_token);
    const me = await api.get('/auth/me');
    setUser(me.data);
    return res.data;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('finpilot_token');
    setUser(null);
  }, []);

  return { user, loading, login, register, logout, isAuthenticated: !!user };
}
