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
- Calculates days worked per function (Supervisor, Técnico, etc.)
- Day/night shift counting based on OS schedule_type (06-18 or 07-19)
- Client-specific price tables with day/night rates per function
- PDF: A4 landscape, report-style border, header with logo + "BOLETIM DE MEDIÇÃO", footer with company info

## PDF Layout (Reports)
- Page border: 1.0cm, color #AAAAAA
- KeepTogether for section titles + first photos
- Evaluation signatures: centered (TA_CENTER)
- CNPJ: 31.839.501/0001-90
- Image compression: quality=60

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
- [x] Boletim de Medição: full feature (conditional on bm_access)
- [x] Per-admin access control: bm_access + os_archive_access toggles
- [x] BM PDF: report-style border/header/footer in landscape
- [x] Visual toast "PDF aberto com sucesso!" (green banner, not window.alert)
- [x] Mobile iOS Safari compatibility

## Key API Endpoints
- PUT /api/users/admins/{id}/bm-access - Toggle BM access
- PUT /api/users/admins/{id}/os-archive-access - Toggle OS Archive access
- GET /api/admin/os-archive - Documents by OS
- GET /api/bm/calculate/{os_id} - Calculate BM from timesheets
- POST /api/bm - Create BM
- GET /api/bm/{id}/pdf - Generate BM PDF

## Key DB Collections
- users: { email, password_hash, role, name, bm_access, os_archive_access }
- service_orders: { os_number, client, location, service, employees, schedule_type }
- client_prices: { client_name, prices: [{function_code, function_name, day_rate, night_rate}] }
- boletins_medicao: { os_id, os_number, client, periodo, items, subtotal, impostos, valor_total }

## Backlog
### P1
- Refactor backend/server.py into modular structure
- Add schedule_type field to Service Orders UI
### P2
- Refactor edit-report.tsx into smaller components
- Offline Mode (AsyncStorage + sync queue)
- EAS Build for App Store/Play Store
