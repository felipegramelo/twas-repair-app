# TWAS REPAIR - PRD

## PDF Specifications
- Page borders: 1.0cm all sides
- Content/header/footer aligned at 1.0cm from edge
- Logo: 5.0cm in header
- Watermark logo: 70% of content width, 6% opacity, centered, all pages except cover
- Header: "RELATÓRIO TÉCNICO" + "20-FR-01-03 (1)" centered, client/vessel/OS/date on right
- Page numbers: "X de Y" right-aligned in footer, skip cover page
- Cover: service name UPPERCASE above photo, vessel UPPERCASE below
- Cover table: bold labels, normal values
- SUMÁRIO: page numbers on right side for each section/subsection
- All text in PDF: BLACK (no colored text)
- Full-page images for NDT subsections, pressure_test, certificate, custom sections
- Image compression: quality 45 in PDF, 60 on upload

## Frontend
- Edit report: no Período (set at creation), no success message on upload
- Multiple file selection, PDF+image upload (PDF→images via PyMuPDF)
- "Adicionar Subseção" only on parent sections
- No text: Descrição do Serviço, NDT section
- Plain text: Introdução, Equipamento, Objetivo (no auto-bullets)
- Bullet text: other sections (auto "• " from first line)

## Credentials
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Backlog
### P1
- Refactor backend/server.py (2050+ lines)
### P2
- Refactor edit-report.tsx, Offline Mode, EAS Build
