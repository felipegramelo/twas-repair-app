# TWAS REPAIR - PRD

## Reports
### Relatório Diário
- Criação: Apenas Data Início (Data Fim = última data das entradas diárias)
- Seções: Introdução, Equipamentos, Objetivo, Descrição dos Serviços (sem subseções)
- WITHOUT: NDT, Teste de Pressão, Certificados, Avaliação
- Entradas Diárias: subseções 4.1, 4.2... com data, descrição e fotos
- Seleção de dias para PDF: checkboxes

### Relatório de Serviço
- Seções completas com NDT, Avaliação, etc
- PDF Avaliação: campos alinhados com cabeçalho/rodapé, linhas mais compridas, tabela com mais espaçamento

## Supervisor Finalization Flow
- Botão "Finalizar" em timesheets e relatórios
- Após finalizar: badge "Finalizado", editar/excluir bloqueados
- **Apenas admin pode "Devolver"** documento ao supervisor (botão no Arquivo por O.S.)
- Supervisor não pode reverter (403)
- Duplicar timesheet (mesma funcionalidade do duplicar relatório)

## Functions
- E=ENGENHEIRO, EN=ENCARREGADO, Sup=SUPERVISOR, T=TÉCNICO, M=MECÂNICO, TS=TÉCNICO DE SEGURANÇA

## BM
- Seleção de timesheets, date pickers, edição, impostos toggle (%)

## Credentials
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Completed (as of 2026-03-31)
- [x] Role-based auth, Timesheet/Report CRUD, PDF generation
- [x] Arquivo por O.S., BM with all features
- [x] Functions: E=ENGENHEIRO, EN=ENCARREGADO
- [x] BM: timesheet selection, date pickers, edit, impostos toggle (%)
- [x] Daily Report: Entradas Diárias como subseções (4.1...) com descrição + fotos
- [x] Daily Report: Seleção de dias para PDF, Data Fim automática, sem Data Fim na criação
- [x] Supervisor Finalization: finalizar/bloquear edição, badge visual
- [x] Admin Revert: devolver documento ao supervisor para ajustes
- [x] Duplicate Timesheet
- [x] PDF Avaliação: campos alinhados, linhas mais compridas, tabela mais espaçada

## Backlog
### P1
- Refactor backend/server.py into modular structure
- Add schedule_type (06-18 / 07-19) to Service Orders UI
### P2
- Refactor edit-report.tsx into smaller components
- Offline Mode / EAS Build
