# TWAS REPAIR - Product Requirements Document

## Original Problem Statement
Unify two separate applications (Timesheet Tracker and Service/Daily Report app) into a single "TWAS REPAIR" corporate application with role-based auth, CRUD operations, and PDF generation.

## User Personas
- **Admin**: Full CRUD on users, employees, service orders
- **Supervisor**: Full CRUD on timesheets and reports, PDF generation

## Tech Stack
- **Backend**: FastAPI, MongoDB (motor), reportlab (PDF), Pydantic
- **Frontend**: Expo (React Native for Web), expo-router, TypeScript
- **Database**: MongoDB (test_database)
- **Storage**: Emergent Object Storage (for photos)

## What's Been Implemented (as of March 19, 2026)
- Full auth system (Admin/Supervisor)
- CRUD for users, employees, service orders
- Timesheet CRUD with A4 PDF generation
- Report CRUD with dynamic sections and sequential numbering
- Report PDF generation with photos (cover + sections, 2 per row with captions)
- Unified supervisor dashboard with duplicate modal
- Report creation with native calendar date pickers
- Photo upload for cover and sections (via Emergent Object Storage)
- FOTOS subsections with photo grid (2 per row) + captions
- PDF margins: border 0.9cm, content/header/footer 2.5cm from edge
- Duplicate reports with OS/period change

## Credentials
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## PDF Layout Specs
- Page border: 0.9cm from edge (all sides)
- Header/Footer/Content: 2.5cm from edge (all sides)
- Photos: 2 per row, reduced, with captions below
- Cover photo on first page

## Backlog (Prioritized)
### P1
- Refactor backend/server.py into modules (routes/, models/, pdf_utils/)

### P2
- Offline Mode (AsyncStorage + sync queue)
- EAS Build (app.json, eas.json for App Store / Play Store)
