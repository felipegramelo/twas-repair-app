# TWAS REPAIR - PRD

## Original Problem Statement
Unify Timesheet Tracker and Service/Daily Report apps into a single "TWAS REPAIR" app with role-based auth, full CRUD for Timesheets and Reports, and advanced A4 PDF generation.

## Access Control
- **Admin**: Full access to dashboard, manage supervisors, employees, service orders, change password
- **Admin + bm_access**: Additional access to Boletim de Medição and client price tables
- **Admin + os_archive_access**: Additional access to Arquivo por O.S.
- **Supervisor**: Timesheet/Report CRUD only, NO access to BM or OS Archive
- Permissions managed via toggle badges on the Administradores page

## Boletim de Medição (BM)
- Linked to timesheets via Service Order
- Calculates days worked per function from timesheets
- Functions: SUPERVISOR (Sup), TECNICO (T), MECANICO (M), ELETRICISTA (E), TECNICO DE SEGURANCA (TS)
- NO Encanador (EN) - not in timesheets
- Day/night shift counting based on OS schedule_type (06-18 or 07-19)
- **Night rate = day rate + 20% (automatic)**
- Client price table stores only day_rate per function
- PDF: A4 landscape, report-style border, logo header + "BOLETIM DE MEDICAO", report-style footer
- **Timesheet Selection**: Admin can select specific timesheets (checkboxes) for BM calculation
- **Date Pickers**: Calendar date pickers for Data Inicio and Data Fim period filtering

## Credentials
- Admin: admin@twasrepair.com / admin123 (bm_access=true, os_archive_access=true)
- Supervisor: supervisor@twasrepair.com / super123

## Architecture
- Backend: FastAPI + MongoDB (motor)
- Frontend: Expo (React Native for Web) + TypeScript
- PDF: ReportLab + PyMuPDF/fitz
- Storage: emergentintegrations object storage

## Completed (as of 2026-03-25)
- [x] Role-based auth (admin/supervisor)
- [x] Timesheet CRUD + PDF generation
- [x] Report CRUD with dynamic sections/subsections
- [x] Photo/PDF upload with object storage
- [x] PDF generation with cover, TOC, content, signature, evaluation
- [x] Admin: Arquivo por O.S. (conditional on os_archive_access)
- [x] Boletim de Medicao: full feature (conditional on bm_access)
- [x] Per-admin access control toggles (bm_access + os_archive_access)
- [x] BM PDF: report-style border/header with logo/footer in landscape
- [x] BM night rate: automatic +20% over day rate
- [x] Functions aligned with timesheet (no Encanador)
- [x] Visual toast "PDF aberto com sucesso!" (green banner)
- [x] Mobile iOS Safari compatibility
- [x] BM Timesheet Selection: checkboxes to select specific timesheets per OS
- [x] BM Date Pickers: calendar inputs for Data Inicio / Data Fim period filtering
- [x] BM Calculate endpoint changed to POST with timesheet_ids, data_inicio, data_fim payload
- [x] New endpoint GET /api/bm/timesheets/{os_id} for listing available timesheets

## Key API Endpoints
- PUT /api/users/admins/{id}/bm-access - Toggle BM access
- PUT /api/users/admins/{id}/os-archive-access - Toggle OS Archive access
- GET /api/bm/timesheets/{os_id} - List timesheets for OS (for selection UI)
- POST /api/bm/calculate/{os_id} - Calculate BM with selected timesheets and date filters
- POST /api/bm - Create BM
- GET /api/bm/{id}/pdf - Generate BM PDF with logo

## Backlog
### P1
- Refactor backend/server.py into modular structure (routes/, models/, pdf_utils/)
- Add schedule_type field (06-18 / 07-19) to Service Orders UI
### P2
- Refactor frontend/app/supervisor/edit-report.tsx into smaller components
- Offline Mode (AsyncStorage + sync queue)
- EAS Build for App Store / Play Store
