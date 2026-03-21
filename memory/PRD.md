# TWAS REPAIR - PRD

## PDF Layout (matching reference)
- Page border: 1.0cm from page edge
- Header/footer boxes: ~2cm from page edge (~1cm inside border)
- Header: logo 5.2cm | "RELATÓRIO TÉCNICO" + "20-FR-01-03 (1)" center | label:value pairs right (Cliente, Rig/Vessel, Equipamento, OS, Rev)
- Footer: company info centered (8pt), "TOGETHER WE ARE STRONGER" italic
- Page numbers: "X de Y" at (x=507, y=772) right-aligned, skip cover
- SUMÁRIO: 3 columns [number bold | title regular | page number], numbers injected by PyMuPDF
- Watermark: 95% content width, 6% opacity, all pages except cover
- Cover: service UPPERCASE above photo, vessel UPPERCASE below
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
- Refactor backend/server.py (2080+ lines)
### P2
- Refactor edit-report.tsx, Offline Mode, EAS Build
