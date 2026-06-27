# TWAS Repair - Product Requirements Document

## Original Problem Statement
Unificar dois apps (Timesheet Tracker + Service/Daily Report) em um único app "TWAS REPAIR" com autenticação por roles (Admin/Supervisor), CRUD completo para Timesheets/Reports/Service Orders, geração de PDFs A4 avançados (capa, índice dinâmico, watermark, fotos), Boletim de Medição, Dashboard Financeiro, sincronização automática com OneDrive e build iOS nativo via EAS.

## User's preferred language
Portuguese (pt-BR)

## What Currently Exists
Full-stack app React Native (Expo Web + iOS) + FastAPI + MongoDB com:
- Modo offline (AsyncStorage + NetInfo)
- Geração de PDFs avançada (ReportLab + PyMuPDF)
- Auth JWT por roles (Admin/Supervisor)
- CRUD completo (OS, Reports, Timesheets)
- Boletim de Medição
- Object Storage Emergent
- Tradução via Gemini Nano Banana
- **OneDrive sync via Make.com webhook (Reports) ✅ NOVO**

## Production Deployment
- **Web**: Vercel (frontend)
- **Backend**: Railway (`twas-repair-app-production.up.railway.app`) — NÃO modificar outro projeto `empowering-ambition`
- **Database**: MongoDB (managed)
- **iOS**: EAS Build (yarn-based após bug fix de package-lock)

## Architecture
```
/app
├── backend/
│   ├── routes/ — auth, service_orders, reports, timesheets, boletim, holidays, proposals, translate
│   ├── services/ — onedrive.py (NOVO: webhook Make.com)
│   ├── utils.py, models.py, database.py, server.py
│   └── .env — MAKE_WEBHOOK_REPORTS_URL, MAKE_WEBHOOK_TIMESHEETS_URL
├── frontend/
│   ├── app/ — admin/*, supervisor/*
│   ├── services/api.ts, utils/pdfHelper.ts
│   └── .env — EXPO_PUBLIC_BACKEND_URL, EXPO_PUBLIC_REPORT_API_URL (Railway)
```

## Key DB Schema
- `service_orders` (os_number, embarcacao, client, location, ...)
- `reports` (os_number, photo_layout, representante_twas, representante_cliente, ...)
- `timesheets`

## 3rd Party Integrations
- Emergent Object Storage (Universal Key)
- Gemini Nano Banana (Universal Key)
- **Make.com Webhook → OneDrive (Personal Account) ✅ NOVO**

## What's Been Implemented (Recent)
### 2026-06-27 — OneDrive Sync (Reports) ✅
- Backend: `services/onedrive.py` envia PDF (multipart/form-data) ao webhook Make.com como fire-and-forget asyncio task
- Trigger: `GET /api/reports/{id}/pdf?download=1` dispara upload
- Make.com scenario: `Webhook → Create a Folder (nome=os_number) → Upload a File`
- Pasta de destino: `/TWAS BR/TÉCNICOS/SERVIÇOS/2026/ORDENS DE SERVIÇOS/[OS_NUMBER]/`
- "Visualizar PDF" (sem download=1) NÃO dispara o webhook
- Validado por testing_agent ✅
- Validado em produção pelo usuário ✅

### Anteriores (mesma sessão)
- iOS EAS build fix (yarn.lock substituindo package-lock.json)
- App Logo 512x512 + Feature Graphic 1024x500
- HEIC photo upload (pillow_heif)
- PDF photo_layout toggle (1 foto/página vs grid 2 fotos)
- `?download=1` separa Visualizar vs Baixar PDF
- Ordenação OS por created_at desc
- Propagação de campos OS → Reports linkados (com migration startup)
- Embarcação/Vessel name em PDF cover/intro/evaluation
- Representante TWAS/Cliente em cover
- Calendar widgets para Duplicate dialogs

## Prioritized Backlog

### P0 (next session)
- **Adicionar `MAKE_WEBHOOK_REPORTS_URL` no Railway** (variável de ambiente em produção)
  - Sem isso, app de produção não envia ao OneDrive
  - URL: `https://hook.us2.make.com/haeb0tfy171wrr3t7sqrw4knshcqr7kx`
  - Passo: railway.app → projeto twas-repair-app → backend service → Variables → New Variable

### P1
- **OneDrive sync para Timesheets**: replicar mesma integração Make.com para Timesheets
  - Backend já preparado (`MAKE_WEBHOOK_TIMESHEETS_URL` env var vazia, código pronto)
  - Criar segundo cenário Make.com (Webhook → Create Folder → Upload) ou reusar mesmo cenário com filtro
  - Atualizar `routes/timesheets.py` no endpoint `?download=1` para chamar `send_pdf_to_onedrive(kind="timesheet")`

### P2
- Refatorar `/app/frontend/app/supervisor/edit-report.tsx` (>1100 linhas → componentes menores)
- Adicionar botão dedicado "Salvar no OneDrive" no UI (manual trigger, sem download)
- Considerar mover refresh de scenarios (Make.com Free plan: 1000 ops/mês ≈ 500 PDFs)

## Key API Endpoints
- `GET /api/reports/{id}/pdf?download=1` — download PDF + dispara OneDrive webhook
- `GET /api/reports/{id}/pdf` — preview inline (NÃO dispara webhook)
- `GET /api/timesheets/{id}/pdf?download=1` — download (OneDrive ainda não configurado)

## Critical Setup Info
- **MongoDB**: usar apenas `MONGO_URL` e `DB_NAME` do backend/.env (não modificar)
- **Frontend backend URL**: `EXPO_PUBLIC_BACKEND_URL` (preview) e `EXPO_PUBLIC_REPORT_API_URL` (Railway prod)
- **Make.com Free plan**: 1000 ops/mês, ~500 PDFs (2 ops cada: Create Folder + Upload)
- **OneDrive Personal Account**: NÃO usar Azure Entra ID/Power Automate — só Make.com Webhook funciona

## Test Credentials
- Admin: `admin@twasrepair.com` / `admin123`
- Supervisor: `supervisor@twasrepair.com` / `super123`
