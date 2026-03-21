# TWAS REPAIR - PRD

## Original Problem Statement
Unify Timesheet Tracker and Service/Daily Report apps into a single "TWAS REPAIR" app with role-based auth, full CRUD for Timesheets and Reports, and advanced A4 PDF generation with headers, footers, watermarks, dynamic TOC, and photo/PDF attachments.

## PDF Layout
- Page border: 1.0cm from edge, color #AAAAAA
- Header box: 0.8cm below border, 2.49cm tall, logo 5.6cm, border #AAAAAA
- Footer box: 0.7cm above border, 1.1cm tall, border #AAAAAA
- Header right: labels right-aligned (Cliente:, Rig/Vessel:, Equipamento:, OS:, Rev:)
- Page numbers: "X de Y" at (507, 772) right bottom, skip cover
- SUMÁRIO: dot leaders calculated with stringWidth, numbers bold, titles normal weight
- Watermark: 115% content width, 6% opacity
- Image heights: dynamically calculated from frame dimensions (max_full_photo_height, max_first_photo_height)
- Section+first photo: KeepTogether
- Cover: service UPPERCASE above, vessel UPPERCASE below, info table border #AAAAAA
- All text BLACK

## Frontend
- Edit report: no Período card, no upload success message
- Multiple file selection, PDF+image upload
- "Adicionar Subseção" only on parent sections

## Credentials
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Architecture
- Backend: FastAPI + MongoDB (motor) - server.py monolith (2100+ lines)
- Frontend: Expo (React Native for Web) + TypeScript
- PDF: ReportLab (layout) + PyMuPDF/fitz (post-processing page numbers + TOC)
- Storage: emergentintegrations object storage

## Completed (as of 2026-03-21)
- [x] Role-based auth (admin/supervisor)
- [x] Timesheet CRUD + PDF generation
- [x] Report CRUD with dynamic sections/subsections
- [x] Photo/PDF upload with object storage
- [x] PDF generation with cover, TOC, content, signature
- [x] PyMuPDF post-processing for accurate page numbers
- [x] KeepTogether for section titles + first photos
- [x] Fix LayoutError crash (dynamic image height calculation)
- [x] Fix TOC formatting (bold numbers only, stringWidth dot leaders)
- [x] Fix lighter border colors (#AAAAAA)

## Backlog
### P1
- Refactor backend/server.py (2100+ lines) into modular structure
### P2
- Refactor edit-report.tsx into smaller components
- Offline Mode (AsyncStorage + sync queue)
- EAS Build for App Store/Play Store
