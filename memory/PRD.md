# TWAS REPAIR - PRD

## Core Features

### Reports
- Relatorio de Servico e Diario com upload de fotos/arquivos
- PDF gerado via ReportLab/PyMuPDF

### Timesheet
- Validacao conflito viagem vs servico
- Maximo 12 funcionarios
- iOS: Pickers inline (CalendarPicker/TimePicker renderizam DENTRO do modal pai, sem modais aninhados)

### Proposta Comercial
- Campo "Servico" obrigatorio
- Texto introdutorio automatico (Prezados...)
- Secoes com subsecoes, upload fotos/arquivos, Termos Gerais
- Dois PDFs: Comercial e Tecnica

### Dashboard Financeiro
- Pagina admin com controle de permissao

### iOS Native Compatibility
- GestureHandlerRootView + SafeAreaProvider no root layout (_layout.tsx)
- CalendarPicker/TimePickerModal com prop "inline" - renderizam sem wrapper Modal quando parent modal esta aberto
- Upload nativo via expo-image-picker + expo-document-picker (edit-report.tsx)
- PDF download nativo via expo-file-system + expo-sharing (pdfHelper.ts)
- Todas as URLs nativas com prefixo /api/ e token no query param
- Alert.alert no nativo para confirmacoes e mensagens (showMsg, handleDeletePhoto, deleteCustomSection)

## Credentials
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Completed
- [x] Role-based auth, Timesheet/Report CRUD, PDF generation
- [x] Arquivo por O.S., BM com todos os recursos
- [x] Proposta Comercial: CRUD, secoes/subsecoes, termos gerais, upload fotos
- [x] Dashboard Financeiro
- [x] Campo "Servico" + texto introdutorio nas propostas
- [x] iOS: GestureHandlerRootView + SafeAreaProvider
- [x] iOS: Pickers inline (sem modais aninhados) em create/edit-timesheet
- [x] iOS: Upload nativo em edit-report (image-picker + document-picker)
- [x] iOS: PDF nativo em TODAS as telas (pdfHelper.ts com /api/ prefix + token)
- [x] iOS: Alert.alert cross-platform em edit-report (08/04/2026)

## Backlog
### P1
- Refactor backend/server.py em estrutura modular (~4100 linhas)
- Adicionar schedule_type (06-18 / 07-19) nas Ordens de Servico
### P2
- Refactor edit-report.tsx em componentes menores
- Modo Offline / EAS Build
