# TWAS REPAIR - PRD

## Original Problem Statement
Unify Timesheet Tracker and Service/Daily Report apps into a single "TWAS REPAIR" app with role-based auth, full CRUD for Timesheets and Reports, and advanced A4 PDF generation.

## Access Control
- **Admin**: Full access to dashboard, manage supervisors, employees, service orders
- **Admin + bm_access**: Boletim de Medição and client price tables
- **Admin + os_archive_access**: Arquivo por O.S.
- **Supervisor**: Timesheet/Report CRUD only

## Functions (Funções)
- E = ENGENHEIRO, EN = ENCARREGADO, Sup = SUPERVISOR, T = TÉCNICO, M = MECÂNICO, TS = TÉCNICO DE SEGURANÇA

## Boletim de Medição (BM)
- Timesheet selection (checkboxes), date pickers, edit BM, impostos toggle (%)
- Night rate = day rate + 20% (automatic)
- PDF: A4 landscape with TWAS logo

## Reports
### Relatório de Serviço (Service Report)
- Sections: Introdução, Equipamentos, Objetivo, Descrição dos Serviços (Desmontagem/Montagem + Fotos), NDT, Teste de Pressão, Certificados, Avaliação do Cliente
- Cover photo, PDF generation, section selection

### Relatório Diário (Daily Report)
- Same sections as Service: Introdução, Equipamentos, Objetivo, Descrição dos Serviços (Desmontagem/Montagem + Fotos)
- WITHOUT: NDT, Teste de Pressão, Certificados, Avaliação
- PLUS: "Entradas Diárias" - per-day entries with date, description, and photo upload
- Each day entry is expandable/collapsible with bullet-point description and photo grid

## Credentials
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Architecture
- Backend: FastAPI + MongoDB (motor)
- Frontend: Expo (React Native for Web) + TypeScript
- PDF: ReportLab + PyMuPDF/fitz
- Storage: emergentintegrations object storage

## Completed (as of 2026-03-30)
- [x] Role-based auth (admin/supervisor)
- [x] Timesheet CRUD + PDF generation
- [x] Report CRUD with dynamic sections/subsections
- [x] Photo/PDF upload with object storage
- [x] PDF generation with cover, TOC, content, signature, evaluation
- [x] Admin: Arquivo por O.S., Boletim de Medição
- [x] Per-admin access control toggles
- [x] BM: timesheet selection, date pickers, edit, impostos toggle (%)
- [x] Functions: E=ENGENHEIRO, EN=ENCARREGADO
- [x] Daily Report: same sections as Service (minus NDT/eval)
- [x] Daily Report: Entradas Diárias with per-day description + photos
- [x] daily_entries stored in report document, persisted via PUT

## Backlog
### P1
- Refactor backend/server.py into modular structure (routes/, models/, pdf_utils/)
- Add schedule_type field (06-18 / 07-19) to Service Orders UI
### P2
- Refactor frontend/app/supervisor/edit-report.tsx into smaller components
- Offline Mode (AsyncStorage + sync queue)
- EAS Build for App Store / Play Store
