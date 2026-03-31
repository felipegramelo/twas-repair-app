export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'supervisor';
  bm_access?: boolean;
  os_archive_access?: boolean;
  proposta_access?: boolean;
}

export interface ProposalItem {
  id: string;
  titulo: string;
  descricao: string;
  valor?: number;
}

export interface Proposal {
  id: string;
  numero_proposta: string;
  empresa: string;
  contato: string;
  email: string;
  embarcacao: string;
  equipamento: string;
  itens: ProposalItem[];
  observacoes?: string;
  status?: string;
  po_number?: string;
  os_id?: string;
  os_number?: string;
  created_at: string;
  updated_at: string;
}

export interface Employee {
  id: string;
  name: string;
}

export interface SOEmployee {
  employee_id: string;
  function: string;
}

export interface ServiceOrder {
  id: string;
  os_number: string;
  client: string;
  location: string;
  service: string;
  employees: SOEmployee[];
}

export interface TimesheetEntry {
  date: string;
  employee_id: string;
  employee_name: string;
  employee_function: string;
  service_start: string;
  service_end: string;
  travel_start?: string;
  travel_end?: string;
}

export interface Timesheet {
  id: string;
  os_id: string;
  os_number: string;
  client: string;
  location: string;
  service: string;
  entries: TimesheetEntry[];
  observations?: string;
  supervisor_id: string;
  supervisor_name: string;
  created_at: string;
  updated_at: string;
}

// Report types (local API)
export interface ReportSection {
  key: string;
  number: string;
  title: string;
  content: string;
  enabled: boolean;
  subsections: ReportSection[];
}

export interface Report {
  id: string;
  report_type: 'daily' | 'service';
  os_id: string;
  os_number: string;
  client: string;
  location: string;
  service: string;
  supervisor_id: string;
  supervisor_name: string;
  periodo_inicio: string;
  periodo_fim: string;
  executado_por: string;
  sections: ReportSection[];
  status: string;
  created_at: string;
  updated_at: string;
}
