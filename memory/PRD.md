# TWAS REPAIR - PRD

## Reports
### Relatório Diário (Daily Report)
- Sections: Introdução, Equipamentos, Objetivo, Descrição dos Serviços (sem subseções)
- WITHOUT: NDT, Teste de Pressão, Certificados, Avaliação
- "Entradas Diárias" = subseções 4.1, 4.2... com data, descrição e fotos
- **Seleção de dias para PDF**: Checkboxes para selecionar quais dias incluir no PDF
- **Data Fim automática**: Última data das entradas diárias é usada como Data Fim
- **Apenas Data Início** no cabeçalho de criação

### Relatório de Serviço (Service Report)
- Seções completas com NDT, Avaliação, etc (inalterado)

## Functions
- E=ENGENHEIRO, EN=ENCARREGADO, Sup=SUPERVISOR, T=TÉCNICO, M=MECÂNICO, TS=TÉCNICO DE SEGURANÇA

## Boletim de Medição (BM)
- Seleção de timesheets, date pickers, edição, impostos toggle (%)

## Credentials
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Architecture
- Backend: FastAPI + MongoDB (motor)
- Frontend: Expo (React Native for Web) + TypeScript
- PDF: ReportLab + PyMuPDF/fitz
- Storage: emergentintegrations object storage

## Completed (as of 2026-03-31)
- [x] Role-based auth, Timesheet/Report CRUD, PDF generation
- [x] Arquivo por O.S., BM with all features
- [x] Functions: E=ENGENHEIRO, EN=ENCARREGADO
- [x] BM: timesheet selection, date pickers, edit, impostos toggle (%)
- [x] Daily Report: same sections as Service minus NDT/eval
- [x] Daily Report: Entradas Diárias as subsections (4.1, 4.2...) with description + photos
- [x] Daily Report PDF: includes daily entries, TOC, NO evaluation section
- [x] Daily Report: day_ids filter for selective PDF generation
- [x] Daily Report: Data Fim auto-calculated from last daily entry date
- [x] Daily Report: Checkbox selection for which days to include in PDF

## Backlog
### P1
- Refactor backend/server.py into modular structure
- Add schedule_type (06-18 / 07-19) to Service Orders UI
### P2
- Refactor edit-report.tsx into smaller components
- Offline Mode / EAS Build
