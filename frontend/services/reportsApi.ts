import api from './api';

// Reports API - uses the same backend as timesheets
export const reportsAPI = {
  getAll: async () => {
    const response = await api.reports.getAll();
    return response;
  },
  create: async (data: { report_type: string; os_id: string; periodo?: string; executado_por?: string }) => {
    const response = await api.reports.create(data);
    return response;
  },
  delete: async (id: string) => {
    const response = await api.reports.delete(id);
    return response;
  },
  downloadPDF: async (id: string) => {
    const response = await api.reports.downloadPDF(id);
    return response;
  },
};
