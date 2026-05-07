import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { User, Employee, ServiceOrder, Timesheet, TimesheetEntry } from '../types';
import { BACKEND_URL, API_URL } from './config';

const api = axios.create({
  baseURL: API_URL,
  timeout: 15000,
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
  resetUserPassword: async (userId: string, newPassword: string) => {
    const response = await api.put(`/admin/reset-password/${userId}`, { new_password: newPassword });
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
  getAll: async (month?: number, year?: number): Promise<ServiceOrder[]> => {
    let url = '/service-orders';
    const params: string[] = [];
    if (month) params.push(`month=${month}`);
    if (year) params.push(`year=${year}`);
    if (params.length > 0) url += '?' + params.join('&');
    const response = await api.get(url);
    return response.data;
  },
  create: async (os_number: string, client: string, location: string, service: string, employees: {employee_id: string, function: string}[] = [], embarcacao: string = ''): Promise<ServiceOrder> => {
    const response = await api.post('/service-orders', { os_number, client, location, embarcacao, service, employees });
    return response.data;
  },
  update: async (id: string, os_number: string, client: string, location: string, service: string, employees: {employee_id: string, function: string}[] = [], embarcacao: string = ''): Promise<ServiceOrder> => {
    const response = await api.put(`/service-orders/${id}`, { os_number, client, location, embarcacao, service, employees });
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
  finalize: async (id: string) => {
    const response = await api.put(`/timesheets/${id}/finalize`);
    return response.data;
  },
  revert: async (id: string) => {
    const response = await api.put(`/timesheets/${id}/revert`);
    return response.data;
  },
  duplicate: async (id: string) => {
    const response = await api.post(`/timesheets/${id}/duplicate`);
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

// Logistics Price Table API
export const logisticsPriceAPI = {
  getAll: async () => {
    const response = await api.get('/logistics-prices');
    return response.data;
  },
  create: async (data: any) => {
    const response = await api.post('/logistics-prices', data);
    return response.data;
  },
  update: async (id: string, data: any) => {
    const response = await api.put(`/logistics-prices/${id}`, data);
    return response.data;
  },
  delete: async (id: string) => {
    const response = await api.delete(`/logistics-prices/${id}`);
    return response.data;
  },
};

// Holidays API (regional + national listing)
export const holidaysAPI = {
  list: async (year?: number) => {
    const url = year ? `/holidays?year=${year}` : '/holidays';
    const response = await api.get(url);
    return response.data;
  },
  create: async (data: { date: string; description?: string }) => {
    const response = await api.post('/holidays', data);
    return response.data;
  },
  delete: async (id: string) => {
    const response = await api.delete(`/holidays/${id}`);
    return response.data;
  },
};

// Boletim de Medição API
export const bmAPI = {
  calculate: async (osId: string, payload?: { timesheet_ids?: string[], data_inicio?: string, data_fim?: string, calc_mode?: 'onshore' | 'offshore' }) => {
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

// Proposal API
export const proposalAPI = {
  getAll: async () => {
    const response = await api.get('/proposals');
    return response.data;
  },
  getAllFiltered: async (month?: number, year?: number) => {
    let url = '/proposals';
    const params: string[] = [];
    if (month) params.push(`month=${month}`);
    if (year) params.push(`year=${year}`);
    if (params.length > 0) url += '?' + params.join('&');
    const response = await api.get(url);
    return response.data;
  },
  getById: async (id: string) => {
    const response = await api.get(`/proposals/${id}`);
    return response.data;
  },
  create: async (data: any) => {
    const response = await api.post('/proposals', data);
    return response.data;
  },
  update: async (id: string, data: any) => {
    const response = await api.put(`/proposals/${id}`, data);
    return response.data;
  },
  delete: async (id: string) => {
    const response = await api.delete(`/proposals/${id}`);
    return response.data;
  },
  downloadPDF: async (id: string, tipo: string = 'comercial'): Promise<Blob> => {
    const response = await api.get(`/proposals/${id}/pdf?tipo=${tipo}&t=${Date.now()}`, {
      responseType: 'blob',
      headers: { 'Cache-Control': 'no-cache' },
      timeout: 120000,
    });
    return response.data;
  },
  informarPO: async (id: string, po_number: string) => {
    const response = await api.put(`/proposals/${id}/informar-po`, { po_number });
    return response.data;
  },
  togglePropostaAccess: async (userId: string) => {
    const response = await api.put(`/users/admins/${userId}/proposta-access`);
    return response.data;
  },
  uploadPhoto: async (proposalId: string, file: File | Blob, sectionIndex: number, filename?: string, sectionKey?: string) => {
    const formData = new FormData();
    formData.append('file', file, filename || 'photo.jpg');
    const params = new URLSearchParams({ section_index: String(sectionIndex) });
    if (sectionKey) params.append('section_key', sectionKey);
    const response = await api.post(`/proposals/${proposalId}/upload-photo?${params.toString()}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
  getPhotos: async (proposalId: string) => {
    const response = await api.get(`/proposals/${proposalId}/photos`);
    return response.data;
  },
  deletePhoto: async (proposalId: string, photoId: string) => {
    const response = await api.delete(`/proposals/${proposalId}/photos/${photoId}`);
    return response.data;
  },
  getPhotoUrl: (storagePath: string, token: string) => {
    const baseUrl = api.defaults.baseURL || '';
    return `${baseUrl}/photos/${storagePath}?auth=${token}`;
  },
};

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
  updateCaption: async (reportId: string, photoId: string, caption: string) => {
    const response = await api.put(`/reports/${reportId}/photos/${photoId}/caption`, { caption });
    return response.data;
  },
  finalize: async (id: string) => {
    const response = await api.put(`/reports/${id}/finalize`);
    return response.data;
  },
  revert: async (id: string) => {
    const response = await api.put(`/reports/${id}/revert`);
    return response.data;
  },
  getPhotoUrl: (storagePath: string, token: string) => {
    const baseUrl = BACKEND_URL + '/api';
    return `${baseUrl}/photos/${storagePath}?auth=${token}`;
  },
};

// Document Sharing API (Admin)
export const sharingAPI = {
  share: async (documentId: string, documentType: string, supervisorIds: string[]) => {
    const response = await api.post('/admin/share-document', {
      document_id: documentId,
      document_type: documentType,
      supervisor_ids: supervisorIds,
    });
    return response.data;
  },
  unshare: async (documentId: string, documentType: string, supervisorIds: string[]) => {
    const response = await api.post('/admin/unshare-document', {
      document_id: documentId,
      document_type: documentType,
      supervisor_ids: supervisorIds,
    });
    return response.data;
  },
  getShares: async (documentType: string, documentId: string) => {
    const response = await api.get(`/admin/document-shares/${documentType}/${documentId}`);
    return response.data;
  },
};
