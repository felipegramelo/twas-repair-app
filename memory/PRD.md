# TWAS REPAIR - PRD

## Original Problem Statement
Unify Timesheet Tracker and Service/Daily Report apps into a single "TWAS REPAIR" app with role-based auth, full CRUD for Timesheets and Reports, and advanced A4 PDF generation.

## Reports
### Relatório de Serviço (Service Report)
- Sections: Introdução, Equipamentos, Objetivo, Descrição dos Serviços (with subsections), NDT, Teste de Pressão, Certificados, Avaliação do Cliente
- Cover photo, PDF generation, section selection, signatures

### Relatório Diário (Daily Report)
- Sections: Introdução, Equipamentos, Objetivo, Descrição dos Serviços (no subsections)
- WITHOUT: NDT, Teste de Pressão, Certificados, Avaliação
- "Entradas Diárias" = subsections of Descrição dos Serviços (4.1, 4.2, etc.)
- Each day entry has: date, description, photos
- PDF includes daily entries with numbering (4.1 DIA dd/mm/yyyy) + photos
- TOC includes daily entries as subsections

## Functions
- E = ENGENHEIRO, EN = ENCARREGADO, Sup = SUPERVISOR, T = TÉCNICO, M = MECÂNICO, TS = TÉCNICO DE SEGURANÇA

## Boletim de Medição (BM)
- Timesheet selection (checkboxes), date pickers, edit BM, impostos toggle (%)
- Night rate = day rate + 20% (automatic)

## Credentials
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Completed (as of 2026-03-30)
- [x] Role-based auth, Timesheet/Report CRUD, PDF generation
- [x] Arquivo por O.S., Boletim de Medição with all features
- [x] Functions: E=ENGENHEIRO, EN=ENCARREGADO
- [x] BM: timesheet selection, date pickers, edit, impostos toggle (%)
- [x] Daily Report: same sections as Service minus NDT/eval
- [x] Daily Report: Entradas Diárias as subsections (4.1, 4.2...) with description + photos
- [x] Daily Report PDF: includes daily entries, TOC, NO evaluation section
- [x] Service Report PDF: unchanged, keeps all sections + evaluation

## Backlog
### P1
- Refactor backend/server.py into modular structure
- Add schedule_type field (06-18 / 07-19) to Service Orders UI
### P2
- Refactor edit-report.tsx into smaller components
- Offline Mode / EAS Build
