# TWAS REPAIR - PRD

## Original Problem Statement
Unify Timesheet Tracker and Service/Daily Report apps into a single "TWAS REPAIR" app with role-based auth, full CRUD for Timesheets and Reports, and advanced A4 PDF generation with headers, footers, watermarks, dynamic TOC, and photo/PDF attachments.

## PDF Layout
- Page border: 1.0cm from edge, color #AAAAAA
- Header box: 0.8cm below border, 2.49cm tall, logo 5.6cm, border #AAAAAA
- Footer box: 0.7cm above border, 1.1cm tall, border #AAAAAA
- Page numbers: "X de Y", skip cover
- SUMÁRIO: dot leaders, numbers bold
- Watermark: 115% content width, 6% opacity
- Evaluation signatures: centered (TA_CENTER)
- CNPJ: 31.839.501/0001-90
- Image compression: quality=60

## Boletim de Medição (BM) - NEW
- Linked to timesheets via Service Order
- Calculates days worked per function (Supervisor, Técnico, Mecânico, Eletricista, etc.)
- Separate day/night shift counting based on OS schedule_type (06-18 or 07-19)
- Client-specific price tables with day/night rates per function
- PDF generation: A4 landscape, company header, client info, service scope table
- Access restricted to admins with `bm_access: true` flag
- Supervisor role has NO access

## Access Control
- **Admin**: Full access to all features
- **Admin + bm_access**: Additional access to Boletim de Medição and client price tables
- **Supervisor**: Timesheet/Report CRUD, NO access to BM

## Credentials
- Admin: admin@twasrepair.com / admin123 (bm_access=true)
- Supervisor: supervisor@twasrepair.com / super123

## Architecture
- Backend: FastAPI + MongoDB (motor) - server.py (~2930 lines)
- Frontend: Expo (React Native for Web) + TypeScript
- PDF: ReportLab + PyMuPDF/fitz
- Storage: emergentintegrations object storage

## Completed (as of 2026-03-25)
- [x] Role-based auth (admin/supervisor)
- [x] Timesheet CRUD + PDF generation
- [x] Report CRUD with dynamic sections/subsections
- [x] Photo/PDF upload with object storage
- [x] PDF generation with cover, TOC, content, signature
- [x] PyMuPDF post-processing for accurate page numbers
- [x] KeepTogether for section titles + first photos
- [x] Evaluation section: 2-page layout with centered signatures
- [x] Image compression, cover photo 12cm centered
- [x] Mobile iOS Safari compatibility
- [x] Admin: Arquivo por O.S. (documents grouped by Service Order)
- [x] Admin: Removed flat list cards (Timesheets/Service Reports/Daily Reports)
- [x] **Boletim de Medição**: Complete feature with:
  - [x] BM access flag on admin users
  - [x] Client price table CRUD (day/night rates per function)
  - [x] BM calculation from timesheets (group by function + shift)
  - [x] BM CRUD (create, list, delete)
  - [x] BM PDF generation (A4 landscape)
  - [x] Frontend: Dashboard card (conditional on bm_access)
  - [x] Frontend: BM management page with tabs (Boletins / Tabela de Preços)
  - [x] Frontend: Create BM modal with OS selection + calculation
  - [x] Frontend: Price table management with day/night rates
  - [x] Bug fix: jwt.JWTError → jwt.PyJWTError

## Key API Endpoints
- GET /api/admin/os-archive - All OS with nested documents
- GET /api/client-prices - Client price tables (bm_access required)
- POST /api/client-prices - Create price table
- GET /api/bm/calculate/{os_id} - Calculate BM from timesheets
- POST /api/bm - Create BM
- GET /api/bm - List BMs
- GET /api/bm/{id}/pdf - Generate BM PDF
- PUT /api/users/admins/{id}/bm-access - Toggle BM access

## Key DB Collections
- `users`: { email, password_hash, role, name, bm_access }
- `service_orders`: { os_number, client, location, service, employees, schedule_type }
- `timesheets`: { os_id, entries: [{date, employee_id, employee_function, service_start, service_end, ...}] }
- `reports`: { os_id, os_number, client, sections, ... }
- `client_prices`: { client_name, prices: [{function_code, function_name, day_rate, night_rate}] }
- `boletins_medicao`: { os_id, os_number, client, periodo, items, subtotal, impostos, valor_total }

## Backlog
### P1
- Refactor backend/server.py (~2930 lines) into modular structure
- Add schedule_type field to Service Orders UI (currently API-only)
### P2
- Refactor edit-report.tsx into smaller components
- Offline Mode (AsyncStorage + sync queue)
- EAS Build for App Store/Play Store
