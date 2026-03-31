# TWAS REPAIR - PRD

## Reports
### Relatório Diário (Daily Report)
- Criação: Apenas Data Início (Data Fim = última data das entradas diárias)
- Seções: Introdução, Equipamentos, Objetivo, Descrição dos Serviços (sem subseções)
- WITHOUT: NDT, Teste de Pressão, Certificados, Avaliação
- Entradas Diárias: subseções 4.1, 4.2... com data, descrição e fotos
- Seleção de dias para PDF: checkboxes para incluir/excluir dias

### Relatório de Serviço (Service Report)
- Seções completas com NDT, Avaliação, etc (inalterado)

## Supervisor Finalization Flow
- Botão "Finalizar" (checkmark verde) em cada timesheet e relatório na aba supervisor
- Ao finalizar: documento fica com status "finalized"
- Supervisor perde acesso de edição/exclusão (só visualizar PDF)
- Badge "Finalizado" verde exibido no card
- Backend bloqueia PUT requests em documentos finalizados (403)
- Admin pode continuar editando documentos finalizados

## Functions
- E=ENGENHEIRO, EN=ENCARREGADO, Sup=SUPERVISOR, T=TÉCNICO, M=MECÂNICO, TS=TÉCNICO DE SEGURANÇA

## Boletim de Medição (BM)
- Seleção de timesheets, date pickers, edição, impostos toggle (%)

## Credentials
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Architecture
- Backend: FastAPI + MongoDB (motor), Frontend: Expo (React Native for Web) + TypeScript
- PDF: ReportLab + PyMuPDF/fitz, Storage: emergentintegrations object storage

## Completed (as of 2026-03-31)
- [x] Role-based auth, Timesheet/Report CRUD, PDF generation
- [x] Arquivo por O.S., BM with all features
- [x] Functions: E=ENGENHEIRO, EN=ENCARREGADO
- [x] BM: timesheet selection, date pickers, edit, impostos toggle (%)
- [x] Daily Report: same sections as Service minus NDT/eval
- [x] Daily Report: Entradas Diárias as subsections (4.1, 4.2...) with description + photos
- [x] Daily Report: Seleção de dias para PDF, Data Fim automática
- [x] Daily Report: Criação sem Data Fim (só Data Início)
- [x] Supervisor Finalization: Botão finalizar, bloqueio de edição, badge visual
- [x] Backend: PUT /api/timesheets/{id}/finalize, PUT /api/reports/{id}/finalize
- [x] Backend: Bloqueio de edição para documentos finalizados

## Backlog
### P1
- Refactor backend/server.py into modular structure
- Add schedule_type (06-18 / 07-19) to Service Orders UI
### P2
- Refactor edit-report.tsx into smaller components
- Offline Mode / EAS Build
