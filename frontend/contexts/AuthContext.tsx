import React, { createContext, useState, useContext, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import { authAPI } from '../services/api';
import { BACKEND_URL } from '../services/config';
import { User } from '../types';

interface AuthContextData {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextData>({} as AuthContextData);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStoredData();
  }, []);

  async function loadStoredData() {
    try {
      const token = await AsyncStorage.getItem('token');
      if (!token) { setLoading(false); return; }

      // Always restore the cached user first so the app can boot offline.
      // The server check below only updates / clears the session when online.
      const cachedRaw = await AsyncStorage.getItem('user_profile');
      if (cachedRaw) {
        try { setUser(JSON.parse(cachedRaw)); } catch {}
      }

      try {
        // Wake up server with a quick ping before full auth check
        await axios.get(BACKEND_URL + '/api/auth/login', { timeout: 5000 }).catch(() => {});
        const userData = await authAPI.getMe();
        setUser(userData);
        await AsyncStorage.setItem('user_profile', JSON.stringify(userData));
      } catch (err: any) {
        // 401/403 means the token is bad — log out. Anything else (no internet,
        // server down, timeout) → keep the cached session so the user can work
        // offline.
        const status = err?.response?.status;
        if (status === 401 || status === 403) {
          await AsyncStorage.removeItem('token');
          await AsyncStorage.removeItem('user_profile');
          setUser(null);
        }
        // Otherwise: silently keep the cached user we already restored
      }
    } finally {
      setLoading(false);
    }
  }

  async function signIn(email: string, password: string) {
    const maxRetries = 4;
    let lastError: any = null;
    
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        const response = await authAPI.login(email, password);
        await AsyncStorage.setItem('token', response.access_token);
        await AsyncStorage.setItem('user_profile', JSON.stringify(response.user));
        setUser(response.user);
        return;
      } catch (error: any) {
        lastError = error;
        if (error.response?.status === 401 || error.response?.status === 400) {
          throw new Error(error.response?.data?.detail || 'Email ou senha incorretos');
        }
        if (attempt < maxRetries) {
          await new Promise(resolve => setTimeout(resolve, 1500 * attempt));
        }
      }
    }
    
    if (lastError?.message?.includes('Network') || lastError?.code === 'ERR_NETWORK' || lastError?.code === 'ECONNABORTED') {
      throw new Error('Sem conexão com a internet. Conecte-se para fazer o primeiro login. Após o primeiro login, o app funciona offline.');
    }
    throw new Error(lastError?.response?.data?.detail || 'Erro ao conectar. Tente novamente.');
  }

  async function signOut() {
    await AsyncStorage.removeItem('token');
    await AsyncStorage.removeItem('user_profile');
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
