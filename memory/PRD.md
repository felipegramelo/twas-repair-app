# TWAS REPAIR - PRD

## Core Features Implemented
- Auth (Admin/Supervisor), CRUD (users, employees, service orders)
- Timesheet CRUD + A4 PDF (original margins: 0.7cm border, 1.2cm content)
- Report CRUD + A4 PDF (adjusted: 0.9cm border, 2.5cm content)
- Unified dashboard + duplicate reports + photo upload (Emergent Object Storage)
- Predefined section texts using OS data (client, service, location)
- Bullet markers (•) with auto-insert on Enter ONLY in non-intro/equip/objective sections
- Introduction, Equipment, Objective: plain text (no auto-bullets, no bullet templates)
- Line breaks preserved in PDF (justified text)
- Clean SUMÁRIO with dot leaders
- Dynamic section numbering (enabled-only)
- Montagem/Desmontagem: text only (FOTOS subsections for photos)
- Edit report: no Período/Informações (set at creation only)
- Add custom subsections within any existing section
- Compartilhar PDF (download) + Visualizar PDF
- Section selection modal with checkboxes

## Credentials
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Completed (March 19, 2026)
- Removed bullet markers from Introdução/Equipamentos/Objetivo templates
- Removed Período e Informações from edit report screen
- Added "Adicionar Subseção" button for creating subsections
- PlainTextArea for intro/equip/objective, BulletTextArea for other sections

## Backlog
### P1
- Refactor backend/server.py into modules (1885+ lines)
### P2
- Refactor edit-report.tsx into smaller components
- Offline Mode, EAS Build
