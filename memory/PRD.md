# TWAS REPAIR - PRD

## Core Features
- Auth (Admin/Supervisor), CRUD (users, employees, service orders, timesheets, reports)
- Timesheet + Report A4 PDF generation with custom headers/footers
- Unified dashboard, report duplication, photo upload (Emergent Object Storage)
- Dynamic sections with subsections, pre-filled templates, bullet markers
- PDF upload → image conversion (PyMuPDF)

## PDF Specifications
- Margins: 1.2cm from edge for content/header/footer
- Logo: 4.5cm width in header
- Header: "RELATÓRIO TÉCNICO" + "20-FR-01-03 (1)" centered, client/vessel/OS/date on right
- No OS number in header center (only on right side)
- Cover page: service name above photo, vessel below, no page number
- Page numbering: "X de Y" format starting from page 2 (via PyMuPDF post-processing)
- Cover table: bold labels only, normal font for values
- Image compression: quality 45 in PDF, 60 on upload, max 2000px resize
- Full-page images for NDT subsections, pressure_test, certificate, custom sections

## Frontend Specifications
- Edit report: no "Período e Informações" (set at creation only)
- No success message on photo upload
- Multiple file selection supported
- "Adicionar Subseção" button only on parent sections (not subsections)
- No text area: Descrição do Serviço, NDT (container sections)
- No photo upload on NDT section (subsections have it)
- Plain text: Introduction, Equipment, Objective (no auto-bullets)
- Bullet text: all other sections (auto-prepend "• " from first line)
- PDF + image upload supported (PDF converted to images)

## Credentials
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Completed (March 20, 2026)
- Page numbers "X de Y" (PyMuPDF post-processing, skip cover)
- Wider margins 1.2cm, bigger logo 4.5cm
- Cover table bold labels only
- Remove OS from header center
- Multiple file selection
- No success message on photo upload
- Subsection button only on parent sections
- NDT: no text/photo, subsections handle it
- PDF upload converts to images via fitz
- Image compression for smaller PDFs

## Backlog
### P1
- Refactor backend/server.py into modules (2000+ lines)
- SUMÁRIO with actual page numbers (requires anchor tracking)
### P2
- Refactor edit-report.tsx into smaller components
- Offline Mode, EAS Build
