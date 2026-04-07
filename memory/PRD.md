# TWAS REPAIR - PRD

## Core Features

### Reports
- Relatorio de Servico - PDF Capa: Linhas separadas para CLIENTE, EMBARCACAO e LOCAL
- Relatorio Diario: Entradas Diarias como subsecoes

### Timesheet
- Validacao de conflito viagem vs servico
- Maximo 12 funcionarios por timesheet
- iOS: Modais nao-aninhados (pendingPicker pattern)

### BM (Boletim de Medicao)
- Campos "COD." e "Linha" por item/funcao

### Proposta Comercial
- Campo "Servico" obrigatorio
- Texto introdutorio automatico (Prezados...)
- Secoes com subsecoes, upload fotos/arquivos, Termos Gerais
- Dois PDFs: Comercial e Tecnica
- iOS: PDF via expo-file-system + expo-sharing

### Dashboard Financeiro
- Pagina admin com controle de permissao

### iOS Native Compatibility
- GestureHandlerRootView + SafeAreaProvider no root layout
- Modais nao-aninhados em create-timesheet e edit-timesheet (pendingPicker state machine)
- PDF download nativo via expo-file-system + expo-sharing em TODAS as telas
- Utility compartilhado: /frontend/utils/pdfHelper.ts

## Credentials
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Completed
- [x] Role-based auth, Timesheet/Report CRUD, PDF generation
- [x] Arquivo por O.S., BM com todos os recursos
- [x] Proposta Comercial: CRUD, secoes/subsecoes, termos gerais, upload fotos
- [x] Dashboard Financeiro
- [x] Validacao conflito viagem vs servico
- [x] Campo "Servico" + texto introdutorio nas propostas
- [x] iOS Native: GestureHandlerRootView, modais nao-aninhados, PDF nativo (07/04/2026)
- [x] Fix timesheet PDF KeyError para campos faltantes (07/04/2026)

## Backlog
### P1
- Refactor backend/server.py em estrutura modular (~4100 linhas)
- Adicionar schedule_type (06-18 / 07-19) nas Ordens de Servico
### P2
- Refactor edit-report.tsx em componentes menores
- Modo Offline / EAS Build
