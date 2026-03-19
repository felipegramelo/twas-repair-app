# TWAS REPAIR - PRD

## Core Features Implemented
- Auth (Admin/Supervisor), CRUD (users, employees, service orders)
- Timesheet CRUD + A4 PDF (original margins: 0.7cm border, 1.2cm content)
- Report CRUD + A4 PDF (adjusted: 0.9cm border, 2.5cm content)
- Unified dashboard + duplicate reports + photo upload (Emergent Object Storage)
- Predefined section texts using OS data (client, service, location)
- Bullet markers (•) with auto-insert from FIRST line in non-intro/equip/objective sections
- Introduction, Equipment, Objective: plain text (no auto-bullets, no bullet templates)
- Line breaks preserved in PDF (justified text)
- Clean SUMÁRIO with dot leaders
- Dynamic section numbering (enabled-only)
- Montagem/Desmontagem: text with bullets from first line
- Edit report: no Período/Informações (set at creation only)
- Add custom subsections within any existing section
- Baixar PDF (download) + Visualizar PDF (new tab) with loading states
- Section selection modal with checkboxes
- PDF header: "20-FR-01-03 (1)" below "Relatório Técnico"
- Cover page: service name above photo, vessel below photo
- Descrição do Serviço: no text area (container for subsections only)
- PDF upload support: converts PDF pages to images (PyMuPDF)
- Image compression: quality 45 in PDF, quality 60 on upload, max 2000px resize
- Smaller font sizes for sections/subsections
- NDT/pressure_test: full-page image rendering in PDF

## Credentials
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Completed (March 19, 2026)
- Removed bullet markers from Introdução/Equipamentos/Objetivo templates
- Removed Período e Informações from edit report screen
- Added "Adicionar Subseção" button for creating subsections
- PlainTextArea for intro/equip/objective, BulletTextArea for other sections
- BulletTextArea: auto-prepend "• " on focus (first line always has bullet)
- PDF header: added "20-FR-01-03 (1)" below "Relatório Técnico"
- Cover page redesign: service name above, vessel below photo
- Font sizes reduced for sections (14→13) and subsections (14→12, 13→11)
- Descrição do Serviço: removed text area
- PDF upload: converts to images via PyMuPDF
- Image compression: reduced quality for smaller PDFs
- Loading states for PDF buttons (spinner while generating)

## Backlog
### P1
- Refactor backend/server.py into modules (1970+ lines)
### P2
- Refactor edit-report.tsx into smaller components
- Offline Mode, EAS Build
