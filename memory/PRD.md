# TWAS REPAIR - PRD

## PDF Layout
- Page border: 1.0cm from edge
- Header box: 0.8cm below border, 2.49cm tall, logo 5.6cm
- Footer box: 0.7cm above border, 1.1cm tall (no "TOGETHER WE ARE STRONGER")
- Header right: labels right-aligned (Cliente:, Rig/Vessel:, Equipamento:, OS:, Rev:)
- Page numbers: "X de Y" at (507, 772) right bottom, skip cover
- SUMÁRIO: dot leaders connecting to page numbers
- Watermark: 115% content width, 6% opacity
- Section+first photo: KeepTogether, first photo 15cm max, subsequent 20cm max
- Cover: service UPPERCASE above, vessel UPPERCASE below
- All text BLACK

## Frontend
- Edit report: no Período, no upload success message
- Multiple file selection, PDF+image upload
- "Adicionar Subseção" only on parent sections

## Credentials
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Backlog
### P1
- Refactor backend/server.py (2100+ lines)
### P2
- Refactor edit-report.tsx, Offline Mode, EAS Build
