import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Report, ExternalServiceOrder, ExternalSupervisor } from '../types';

const REPORT_API_URL = process.env.EXPO_PUBLIC_REPORT_API_URL;

const reportApi = axios.create({
  baseURL: REPORT_API_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Store and retrieve the report API token separately
const REPORT_TOKEN_KEY = 'report_api_token';

async function getReportToken(): Promise<string | null> {
  return AsyncStorage.getItem(REPORT_TOKEN_KEY);
}

reportApi.interceptors.request.use(async (config) => {
  const token = await getReportToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth - login to external report API and store token
export const reportAuthAPI = {
  login: async (email: string, password: string): Promise<string> => {
    const response = await reportApi.post('/auth/login', { email, password });
    const token = response.data.token;
    await AsyncStorage.setItem(REPORT_TOKEN_KEY, token);
    return token;
  },
  logout: async () => {
    await AsyncStorage.removeItem(REPORT_TOKEN_KEY);
  },
  isAuthenticated: async (): Promise<boolean> => {
    const token = await getReportToken();
    return !!token;
  },
};

// Reports
export const reportsAPI = {
  getAll: async (): Promise<Report[]> => {
    const response = await reportApi.get('/reports');
    return response.data.reports || [];
  },
  getByType: async (reportType: 'daily' | 'service'): Promise<Report[]> => {
    const all = await reportsAPI.getAll();
    return all.filter(r => r.report_type === reportType);
  },
  getById: async (id: string): Promise<Report> => {
    const response = await reportApi.get(`/reports/${id}`);
    return response.data;
  },
  create: async (data: {
    report_type: 'daily' | 'service';
    service_order_id: string;
    service_order_number: string;
    client: string;
    vessel: string;
    equipment: string;
    supervisor_id: string;
    supervisor_name: string;
  }): Promise<Report> => {
    const response = await reportApi.post('/reports', data);
    return response.data;
  },
  delete: async (id: string) => {
    const response = await reportApi.delete(`/reports/${id}`);
    return response.data;
  },
  downloadPDF: async (id: string): Promise<Blob> => {
    const response = await reportApi.get(`/reports/${id}/pdf/download`, {
      responseType: 'blob',
      headers: { 'Cache-Control': 'no-cache' },
    });
    return response.data;
  },
};

// Service Orders from external API
export const externalServiceOrderAPI = {
  getAll: async (): Promise<ExternalServiceOrder[]> => {
    const response = await reportApi.get('/service-orders');
    return response.data.service_orders || [];
  },
};

// Supervisors from external API
export const externalSupervisorAPI = {
  getAll: async (): Promise<ExternalSupervisor[]> => {
    const response = await reportApi.get('/supervisors');
    return response.data.supervisors || [];
  },
};

export default reportApi;
