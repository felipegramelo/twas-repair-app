import React, { createContext, useState, useContext, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { authAPI } from '../services/api';
import { reportAuthAPI } from '../services/reportsApi';
import { User } from '../types';

interface AuthContextData {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  ensureReportAuth: () => Promise<void>;
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
        const userData = await authAPI.getMe();
        setUser(userData);
      }
    } catch (error) {
      console.error('Error loading stored data:', error);
    } finally {
      setLoading(false);
    }
  }

  async function signIn(email: string, password: string) {
    try {
      const response = await authAPI.login(email, password);
      await AsyncStorage.setItem('token', response.access_token);
      // Store credentials for report API re-auth
      await AsyncStorage.setItem('user_email', email);
      await AsyncStorage.setItem('user_pwd', password);
      setUser(response.user);
      // Also authenticate with the external report API
      try {
        await reportAuthAPI.login(email, password);
      } catch (e) {
        console.warn('Report API login failed (non-blocking):', e);
      }
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Erro ao fazer login');
    }
  }

  async function ensureReportAuth() {
    const isAuth = await reportAuthAPI.isAuthenticated();
    if (!isAuth) {
      const email = await AsyncStorage.getItem('user_email');
      const pwd = await AsyncStorage.getItem('user_pwd');
      if (email && pwd) {
        try { await reportAuthAPI.login(email, pwd); } catch (e) {
          console.warn('Report API re-auth failed:', e);
        }
      }
    }
  }

  async function signOut() {
    await AsyncStorage.removeItem('token');
    await AsyncStorage.removeItem('user_email');
    await AsyncStorage.removeItem('user_pwd');
    await reportAuthAPI.logout();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signOut, ensureReportAuth }}>
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
