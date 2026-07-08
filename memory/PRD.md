# TWAS REPAIR — Product Requirements

## Original problem statement
The user wants to unify two separate applications (a Timesheet Tracker and a Service/Daily Report app) into a single "TWAS REPAIR" app with role-based auth (Admin/Supervisor), full CRUD for Timesheets & Reports, advanced A4 PDF generation (ReportLab), automated OneDrive sync (via Make.com), and a Projects module (Gantt-style task scheduling) with AI-powered PDF import (Gemini 3 Flash).

## Personas
- **Admin**: Manages Service Orders, Reports, Timesheets, Projects; assigns projects to Supervisors; imports PDFs to auto-populate task hierarchies.
- **Supervisor**: Creates/edits Reports & Timesheets, updates progress % on tasks assigned to them.

## Stack
- Expo Router + React Native Web / iOS / Android
- FastAPI + MongoDB (motor)
- ReportLab / PyMuPDF for PDF
- Make.com webhooks → personal OneDrive
- Emergent LLM key + `emergentintegrations` (Gemini 3 Flash) for PDF task extraction

## Implemented (recent → older)
- **2026-02-08** — Project PDF redesigned to match MS Project model: bold phase headers with gray background at any depth, bold column headers, day-of-week + date format ("Qua 14/01/26"), timeline date ticks above Gantt bars, and colored Gantt bars (dark for phases, blue for leaves) with progress overlay.
- **2026-02-08** — Fixed "Falha ao baixar PDF" in Projects: (a) `projectAPI.downloadPDF` blob helper added, (b) Content-Disposition now uses RFC 6266 UTF-8 encoding for Unicode titles (em-dash etc.).
- **2026-02-08** — Replaced YYYY-MM-DD text inputs with cross-platform Calendar widgets (`DateField` component: native HTML date input on web, `DateTimePicker` modal on iOS/Android).
- **2026-02-08** — Fixed misleading "Falha ao enviar PDF" error: extended polling to 3 min, swallowed transient GET failures, only shows the error when the initial POST truly fails.
- OneDrive Sync for Reports & Timesheets via Make.com Webhooks.
- Projects Module MVP (parent/child hierarchy, % progress, `shared_with` for supervisor assignment).
- Async AI PDF Import (Gemini 3 Flash → JSON task tree).
- Global Axios 401 interceptor (session expiration).

## Backlog
- **P1** OneDrive sync for Project PDFs (needs `MAKE_WEBHOOK_PROJECTS_URL`).
- **P2** Refactor `supervisor/edit-report.tsx` (>1100 lines) into smaller components.

## Credentials
- Admin: `admin@twasrepair.com` / `admin123`
- Supervisor: `supervisor@twasrepair.com` / `super123`

## Key files
- `/app/frontend/components/DateField.tsx` — cross-platform calendar input
- `/app/frontend/app/admin/edit-project.tsx` — task editor (uses DateField)
- `/app/frontend/app/admin/projects.tsx` — project creation (uses DateField)
- `/app/backend/routes/projects.py` — Project CRUD + AI PDF import
- `/app/backend/services/onedrive.py` — Make.com webhook helper
