export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'supervisor';
  bm_access?: boolean;
  os_archive_access?: boolean;
  proposta_access?: boolean;
  dashboard_access?: boolean;
}

export interface ProposalSubsection {
  id: string;
  titulo: string;
  descricao: string;
}

export interface ProposalItem {
  id: string;
  titulo: string;
  descricao: string;
  valor?: number;
  images?: string[];
  subsections?: ProposalSubsection[];
}

export interface Proposal {
  id: string;
  numero_proposta: string;
  empresa: string;
  contato: string;
  email: string;
  embarcacao: string;
  local?: string;
  equipamento: string;
  servico: string;
  itens: ProposalItem[];
  termos_gerais?: string;
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
  embarcacao?: string;
  service: string;
  employees: SOEmployee[];
  schedule_type?: '06-18' | '07-19';
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
  shared_with?: string[];
  status?: string;
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
  shared_with?: string[];
  periodo_inicio: string;
  periodo_fim: string;
  executado_por: string;
  sections: ReportSection[];
  status: string;
  created_at: string;
  updated_at: string;
}
