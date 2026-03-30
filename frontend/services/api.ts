import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { User, Employee, ServiceOrder, Timesheet, TimesheetEntry } from '../types';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL + '/api';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
api.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth API
export const authAPI = {
  login: async (email: string, password: string) => {
    const response = await api.post('/auth/login', { email, password });
    return response.data;
  },
  register: async (email: string, password: string, name: string, role: string) => {
    const response = await api.post('/auth/register', { email, password, name, role });
    return response.data;
  },
  getMe: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },
};

// User/Supervisor API
export const supervisorAPI = {
  getAll: async (): Promise<User[]> => {
    const response = await api.get('/users/supervisors');
    return response.data;
  },
  create: async (email: string, name: string, password: string): Promise<User> => {
    const response = await api.post('/users/supervisors', { email, name, password });
    return response.data;
  },
  update: async (id: string, email: string, name: string, password?: string): Promise<User> => {
    const response = await api.put(`/users/supervisors/${id}`, { 
      email, 
      name, 
      ...(password && { password }) 
    });
    return response.data;
  },
  delete: async (id: string) => {
    const response = await api.delete(`/users/supervisors/${id}`);
    return response.data;
  },
};

// Admin API
export const adminAPI = {
  getAll: async (): Promise<User[]> => {
    const response = await api.get('/users/admins');
    return response.data;
  },
  create: async (email: string, name: string, password: string): Promise<User> => {
    const response = await api.post('/users/admins', { email, name, password });
    return response.data;
  },
  update: async (id: string, email: string, name: string, password?: string): Promise<User> => {
    const response = await api.put(`/users/admins/${id}`, { 
      email, 
      name, 
      ...(password && { password }) 
    });
    return response.data;
  },
  delete: async (id: string) => {
    const response = await api.delete(`/users/admins/${id}`);
    return response.data;
  },
  changePassword: async (currentPassword: string, newPassword: string) => {
    const response = await api.put('/auth/change-password', { current_password: currentPassword, new_password: newPassword });
    return response.data;
  },
};

// Employee API
export const employeeAPI = {
  getAll: async (): Promise<Employee[]> => {
    const response = await api.get('/employees');
    return response.data;
  },
  create: async (name: string): Promise<Employee> => {
    const response = await api.post('/employees', { name });
    return response.data;
  },
  update: async (id: string, name: string): Promise<Employee> => {
    const response = await api.put(`/employees/${id}`, { name });
    return response.data;
  },
  delete: async (id: string) => {
    const response = await api.delete(`/employees/${id}`);
    return response.data;
  },
};

// Service Order API
export const serviceOrderAPI = {
  getAll: async (): Promise<ServiceOrder[]> => {
    const response = await api.get('/service-orders');
    return response.data;
  },
  create: async (os_number: string, client: string, location: string, service: string, employees: {employee_id: string, function: string}[] = []): Promise<ServiceOrder> => {
    const response = await api.post('/service-orders', { os_number, client, location, service, employees });
    return response.data;
  },
  update: async (id: string, os_number: string, client: string, location: string, service: string, employees: {employee_id: string, function: string}[] = []): Promise<ServiceOrder> => {
    const response = await api.put(`/service-orders/${id}`, { os_number, client, location, service, employees });
    return response.data;
  },
  delete: async (id: string) => {
    const response = await api.delete(`/service-orders/${id}`);
    return response.data;
  },
};

// Timesheet API
export const timesheetAPI = {
  getAll: async (): Promise<Timesheet[]> => {
    const response = await api.get('/timesheets');
    return response.data;
  },
  getById: async (id: string): Promise<Timesheet> => {
    const response = await api.get(`/timesheets/${id}`);
    return response.data;
  },
  create: async (os_id: string, entries: TimesheetEntry[], observations?: string, supervisor_function?: string): Promise<Timesheet> => {
    const response = await api.post('/timesheets', { os_id, entries, observations, supervisor_function });
    return response.data;
  },
  update: async (id: string, os_id: string, entries: TimesheetEntry[], observations?: string, supervisor_function?: string): Promise<Timesheet> => {
    const response = await api.put(`/timesheets/${id}`, { os_id, entries, observations, supervisor_function });
    return response.data;
  },
  delete: async (id: string) => {
    const response = await api.delete(`/timesheets/${id}`);
    return response.data;
  },
  downloadPDF: async (id: string): Promise<Blob> => {
    const response = await api.get(`/timesheets/${id}/pdf?t=${Date.now()}`, {
      responseType: 'blob',
      headers: { 'Cache-Control': 'no-cache' },
    });
    return response.data;
  },
};

// Admin Archive API
export const archiveAPI = {
  getOSArchive: async () => {
    const response = await api.get('/admin/os-archive');
    return response.data;
  },
};

// Client Price Table API
export const clientPriceAPI = {
  getAll: async () => {
    const response = await api.get('/client-prices');
    return response.data;
  },
  create: async (data: any) => {
    const response = await api.post('/client-prices', data);
    return response.data;
  },
  update: async (id: string, data: any) => {
    const response = await api.put(`/client-prices/${id}`, data);
    return response.data;
  },
  delete: async (id: string) => {
    const response = await api.delete(`/client-prices/${id}`);
    return response.data;
  },
};

// Boletim de Medição API
export const bmAPI = {
  calculate: async (osId: string, payload?: { timesheet_ids?: string[], data_inicio?: string, data_fim?: string }) => {
    const response = await api.post(`/bm/calculate/${osId}`, payload || {});
    return response.data;
  },
  getTimesheets: async (osId: string) => {
    const response = await api.get(`/bm/timesheets/${osId}`);
    return response.data;
  },
  create: async (data: any) => {
    const response = await api.post('/bm', data);
    return response.data;
  },
  list: async () => {
    const response = await api.get('/bm');
    return response.data;
  },
  get: async (id: string) => {
    const response = await api.get(`/bm/${id}`);
    return response.data;
  },
  delete: async (id: string) => {
    const response = await api.delete(`/bm/${id}`);
    return response.data;
  },
  update: async (id: string, data: any) => {
    const response = await api.put(`/bm/${id}`, data);
    return response.data;
  },
  toggleBMAccess: async (userId: string) => {
    const response = await api.put(`/users/admins/${userId}/bm-access`);
    return response.data;
  },
};

export default api;

// Report API (local backend)
export const reportAPI = {
  getAll: async () => {
    const response = await api.get('/reports');
    return response.data.reports || [];
  },
  getById: async (id: string) => {
    const response = await api.get(`/reports/${id}`);
    return response.data;
  },
  create: async (data: { report_type: string; os_id: string; periodo_inicio?: string; periodo_fim?: string; executado_por?: string }) => {
    const response = await api.post('/reports', data);
    return response.data;
  },
  update: async (id: string, data: Record<string, any>) => {
    const response = await api.put(`/reports/${id}`, data);
    return response.data;
  },
  delete: async (id: string) => {
    const response = await api.delete(`/reports/${id}`);
    return response.data;
  },
  duplicate: async (id: string, data: { os_id?: string; periodo_inicio?: string; periodo_fim?: string; executado_por?: string }) => {
    const response = await api.post(`/reports/${id}/duplicate`, data);
    return response.data;
  },
  downloadPDF: async (id: string): Promise<Blob> => {
    const response = await api.get(`/reports/${id}/pdf?t=${Date.now()}`, {
      responseType: 'blob',
      headers: { 'Cache-Control': 'no-cache' },
      timeout: 120000,
    });
    return response.data;
  },
  uploadPhoto: async (reportId: string, file: File | Blob, sectionKey: string = 'cover', filename?: string) => {
    const formData = new FormData();
    formData.append('file', file, filename || 'photo.jpg');
    const response = await api.post(`/reports/${reportId}/upload-photo?section_key=${sectionKey}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
  getPhotos: async (reportId: string) => {
    const response = await api.get(`/reports/${reportId}/photos`);
    return response.data.photos || [];
  },
  deletePhoto: async (reportId: string, photoId: string) => {
    const response = await api.delete(`/reports/${reportId}/photos/${photoId}`);
    return response.data;
  },
  getPhotoUrl: (storagePath: string, token: string) => {
    const baseUrl = process.env.EXPO_PUBLIC_BACKEND_URL + '/api';
    return `${baseUrl}/photos/${storagePath}?auth=${token}`;
  },
};
