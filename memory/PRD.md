# TWAS REPAIR - PRD

## PDF Specifications
- Page borders: 1.0cm all sides
- Header/footer boxes: aligned at 1.0cm from page edge
- Logo: 5.5cm in header
- Watermark: 90% content width, 6% opacity, centered, all pages except cover
- Header: "RELATÓRIO TÉCNICO" + "20-FR-01-03 (1)" centered, client/vessel/OS/date on right
- Page numbers: "X de Y" right-aligned in footer, skip cover
- SUMÁRIO: dot leaders with page numbers right-aligned (PyMuPDF post-processing)
- Cover: service UPPERCASE above photo, vessel UPPERCASE below
- Cover table: bold labels, normal values
- All text: BLACK

## Frontend
- Edit report: no Período, no upload success message
- Multiple file selection, PDF+image upload
- "Adicionar Subseção" only on parent sections
- No text: Descrição do Serviço, NDT
- Plain text: Introdução, Equipamento, Objetivo
- Bullet text: other sections (auto "• " from first line)

## Credentials
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Backlog
### P1
- Refactor backend/server.py (2060+ lines)
### P2
- Refactor edit-report.tsx, Offline Mode, EAS Build
