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
7. Report creation with date period using calendar pickers
8. Report editing with dynamic sections and sequential numbering
9. Report PDF matching timesheet style (boxed header/footer, page border, logo)
10. Duplicate reports with ability to change OS and period
11. Photo upload for cover and sections (excluding introdução, equipamento, objetivo, descrição do serviço)
12. FOTOS subsections show photo grid (2 per row) with captions, no text area

## Tech Stack
- **Backend**: FastAPI, MongoDB (motor), reportlab (PDF), Pydantic
- **Frontend**: Expo (React Native for Web), expo-router, TypeScript
- **Database**: MongoDB (test_database)
- **Storage**: Emergent Object Storage (for photos)

## Architecture
```
/app
├── backend/
│   ├── server.py
│   ├── tests/
│   └── .env
├── frontend/
│   ├── app/
│   │   ├── admin/
│   │   ├── supervisor/
│   │   │   ├── index.tsx          # Dashboard + duplicate modal
│   │   │   ├── create-report.tsx  # Native select + date picker
│   │   │   ├── edit-report.tsx    # Dynamic numbering + photo grid
│   │   │   ├── create-timesheet.tsx
│   │   │   └── edit-timesheet.tsx
│   │   ├── _layout.tsx
│   │   └── index.tsx
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

## What's Been Implemented (as of March 19, 2026)
- Full auth system (Admin/Supervisor)
- CRUD for users, employees, service orders
- Timesheet CRUD with A4 PDF generation
- Report CRUD with dynamic sections
- Report PDF generation matching timesheet style
- Unified supervisor dashboard
- Report creation with native calendar date pickers
- Report editing with dynamic section numbering
- Duplicate reports with OS/period change
- Photo upload for cover and sections
- FOTOS subsections with photo grid (2/row) + captions
- Fixed: OS dropdown using native HTML select for web
- Fixed: Alert.alert → window.alert for web compatibility
- Fixed: Scroll on supervisor dashboard
- Fixed: stopPropagation on action buttons
- PDF margins aligned (header = footer = content width)

## Credentials
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Backlog (Prioritized)
### P1
- Include uploaded photos in PDF generation
- Refactor backend/server.py into modules (routes/, models/, pdf_utils/)

### P2
- Offline Mode (AsyncStorage + sync queue)
- EAS Build (app.json, eas.json for App Store / Play Store)
