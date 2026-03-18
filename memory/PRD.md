# TWAS REPAIR - Product Requirements Document

## Original Problem Statement
Unify two separate applications (Timesheet Tracker and Service/Daily Report app) into a single "TWAS REPAIR" corporate application with role-based auth, CRUD operations, and PDF generation.

## User Personas
- **Admin**: Full CRUD on users, employees, service orders
- **Supervisor**: Full CRUD on timesheets and reports, PDF generation

## Core Requirements
1. Role-based auth (Admin, Supervisor)
2. CRUD for users, employees, service orders
3. Supervisor CRUD on Timesheets
4. Generate A4 PDF of timesheets with logo, header, footer, border, signature
5. Unified "TWAS REPAIR" branding
6. Unified supervisor dashboard (single list, no tabs, one "Criar Novo" button)
7. Report creation with date period (inicio/fim)
8. Report editing with dynamic sections (add, remove, toggle, nested subsections)
9. Report PDF matching timesheet style (boxed header/footer, page border, logo)
10. Duplicate reports with ability to change OS and period
11. Photo upload for cover and sections (excluding introdução, equipamento, objetivo, descrição do serviço)

## Tech Stack
- **Backend**: FastAPI, MongoDB (motor), reportlab (PDF), Pydantic
- **Frontend**: Expo (React Native for Web), expo-router, TypeScript
- **Database**: MongoDB (test_database)
- **Storage**: Emergent Object Storage (for photos)

## Architecture
```
/app
├── backend/
│   ├── server.py          # FastAPI (auth, timesheets, reports, photos, storage)
│   ├── tests/
│   │   ├── test_report_api.py
│   │   └── test_new_features.py
│   └── .env
├── frontend/
│   ├── app/
│   │   ├── admin/
│   │   ├── supervisor/
│   │   │   ├── index.tsx         # Unified dashboard + duplicate modal
│   │   │   ├── create-report.tsx # Report creation with date pickers
│   │   │   ├── edit-report.tsx   # Report editing with sections + photo upload
│   │   │   ├── create-timesheet.tsx
│   │   │   └── edit-timesheet.tsx
│   │   ├── _layout.tsx
│   │   └── index.tsx             # Login
│   ├── services/api.ts
│   ├── types/index.ts
│   └── contexts/AuthContext.tsx
└── logo.bmp
```

## Key API Endpoints
- POST/GET /api/reports
- GET/PUT/DELETE /api/reports/{id}
- GET /api/reports/{id}/pdf
- POST /api/reports/{id}/duplicate
- POST /api/reports/{id}/upload-photo
- GET /api/reports/{id}/photos
- DELETE /api/reports/{id}/photos/{photo_id}
- GET /api/photos/{path}
- POST/GET /api/timesheets
- GET/PUT/DELETE /api/timesheets/{id}
- GET /api/timesheets/{id}/pdf
- POST /api/auth/login, /api/auth/register
- CRUD /api/service-orders, /api/employees, /api/users/*

## DB Schema - Reports
```json
{
  "report_type": "service|daily",
  "os_id": "ObjectId ref",
  "os_number": "string",
  "client": "string",
  "location": "string",
  "service": "string",
  "supervisor_id": "string",
  "supervisor_name": "string",
  "periodo_inicio": "DD/MM/YYYY",
  "periodo_fim": "DD/MM/YYYY",
  "executado_por": "string",
  "cover_photo": "storage_path",
  "sections": [{ "key", "number", "title", "content", "enabled", "subsections": [...] }],
  "status": "draft|completed|approved",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

## DB Schema - Report Photos
```json
{
  "report_id": "string",
  "section_key": "string (cover, ndt, etc.)",
  "storage_path": "string",
  "original_filename": "string",
  "content_type": "string",
  "size": "int",
  "is_deleted": "boolean",
  "created_at": "datetime"
}
```

## What's Been Implemented (as of March 18, 2026)
- Full auth system (Admin/Supervisor)
- CRUD for users, employees, service orders
- Timesheet CRUD with A4 PDF generation
- Report CRUD with dynamic sections
- Report PDF generation matching timesheet style
- Unified supervisor dashboard
- Report creation with date period inputs
- Report editing with section management modal
- Duplicate reports with OS/period change
- Photo upload for cover and sections (via Emergent Object Storage)
- Scroll fix on supervisor dashboard
- stopPropagation fix on action buttons

## Credentials
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Backlog (Prioritized)
### P1
- Refactor backend/server.py into modules (routes/, models/, pdf_utils/)
- Extract duplicated PDF header/footer into shared utility
- Include uploaded photos in PDF generation

### P2
- Offline Mode (AsyncStorage + sync queue)
- EAS Build (app.json, eas.json for App Store / Play Store)
