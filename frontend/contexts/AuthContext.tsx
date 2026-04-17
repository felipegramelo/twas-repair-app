import React, { createContext, useState, useContext, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import { authAPI } from '../services/api';
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
      if (token) {
        // Wake up server with a quick ping before full auth check
        try { await axios.get(process.env.EXPO_PUBLIC_BACKEND_URL + '/api/auth/login', { timeout: 5000 }).catch(() => {}); } catch {}
        const userData = await authAPI.getMe();
        setUser(userData);
      }
    } catch (error) {
      await AsyncStorage.removeItem('token');
      setUser(null);
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
      throw new Error('Servidor iniciando. Aguarde alguns segundos e tente novamente.');
    }
    throw new Error(lastError?.response?.data?.detail || 'Erro ao conectar. Tente novamente.');
  }

  async function signOut() {
    await AsyncStorage.removeItem('token');
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
