# TWAS REPAIR - PRD (Product Requirements Document)

## Problema Original
Unificar dois apps (Timesheet Tracker e Service/Daily Report) em um unico app "TWAS REPAIR" com autenticacao role-based (Admin/Supervisor), CRUD completo, geracao avancada de PDF A4, e funcionalidade cross-platform (React Native Web + iOS + Android).

## Stack Tecnica
- Frontend: React Native (Expo SDK 54, Expo Router), TypeScript
- Backend: FastAPI, MongoDB (motor) - Estrutura Modular
- PDF: ReportLab + PyMuPDF (fitz)
- Storage: Emergent Object Storage

## Arquitetura Backend (Refatorado)
```
backend/
  server.py          (59 linhas - app init + router includes)
  database.py, config.py, dependencies.py, models.py
  routes/ (auth, employees, service_orders, timesheets, reports, proposals, boletim, dashboard, sharing)
```

## Funcionalidades Implementadas
- [x] Autenticacao (Admin/Supervisor) com JWT
- [x] CRUD Timesheets + PDF + Numero sequencial por OS (admin)
- [x] CRUD Relatorios (servico e diario) + PDF + Fotos
- [x] Ordens de Servico CRUD + PDF (10-FR-01-06) gerado automaticamente
- [x] Boletim de Medicao + Dashboard Financeiro
- [x] Propostas Comerciais (campo local, auto-preenchimento OS)
- [x] iOS/Android: PDFs, Fotos, Alerts, Sharing - tudo nativo
- [x] Compartilhamento de Documentos + Troca de Senha
- [x] Tema Preto (#000000)
- [x] Marcadores toggle por linha nos relatorios
- [x] Confirmacao "Enviar para administrador" com tipo do documento
- [x] Backend refatorado (monolito -> modular)
- [x] Object Storage atualizado (novos endpoints /init, /objects/)

## Versao Atual: 1.0.10 (build 6)

## Credenciais de Teste
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123
