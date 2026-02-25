export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'supervisor';
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
