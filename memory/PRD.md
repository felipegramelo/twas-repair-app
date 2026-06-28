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
- **OneDrive sync via Make.com (Reports + Timesheets) ✅**

## Production Deployment
- **Web**: Vercel (frontend)
- **Backend**: Railway projeto `dynamic-compassion` / serviço `twas-repair-app` (`twas-repair-app-production.up.railway.app`)
- **Database**: MongoDB (managed)
- **iOS**: EAS Build (yarn-based)

## Architecture
```
/app
├── backend/
│   ├── routes/ — auth, service_orders, reports, timesheets, boletim, holidays, proposals, translate
│   ├── services/ — onedrive.py (Make.com webhook helper)
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
- **Make.com Webhook → OneDrive (Personal Account) — 2 cenários ativos:**
  - **TWAS Reports → OneDrive**: `https://hook.us2.make.com/haeb0tfy171wrr3t7sqrw4knshcqr7kx`
  - **TWAS Timesheets → OneDrive**: `https://hook.us2.make.com/p43xnik7eupifvurj4maastrmlmxro5a`

## What's Been Implemented (Recent)
### 2026-06-28 — OneDrive Sync (Timesheets) ✅
- Backend `routes/timesheets.py`: asyncio.create_task dispara `send_pdf_to_onedrive(kind="timesheet")` quando `?download=1`
- Make.com scenario: `Webhook → Create a Folder (os_number) → Upload a File (Rename the new file)`
- Pasta de destino: `/TWAS BR/.../ORDENS DE SERVIÇOS/[OS_NUMBER]/`
- "Rename the new file" garante preservação de versões antigas (sufixo `(1)`, `(2)`...)
- Pasta mantida com "Replace the existing folder" (retorna ID da existente, não deleta conteúdo)
- Validado por testing_agent (100% — 8/8 testes)

### 2026-06-27/28 — OneDrive Sync (Reports) ✅
- `services/onedrive.py` (multipart/form-data via httpx)
- `routes/reports.py` asyncio.create_task em `?download=1`
- Make.com scenario com Create a Folder + Upload File
- Railway env var `MAKE_WEBHOOK_REPORTS_URL` configurada
- Validado em produção

### Anteriores
- iOS EAS build fix (yarn.lock)
- App Logo + Feature Graphic
- HEIC photo upload (pillow_heif)
- PDF photo_layout toggle (1 foto/página vs grid)
- `?download=1` separa Visualizar vs Baixar PDF
- OS sort by created_at desc
- Propagação de campos OS → Reports
- Embarcação/Vessel name em PDF
- Representante TWAS/Cliente
- Calendar widgets para Duplicate

## Prioritized Backlog

### P0 (próxima sessão)
- **Save to GitHub** — push das mudanças backend para que o Railway tenha o código novo (services/onedrive.py + triggers em routes)
- **Railway env var pendente**: `MAKE_WEBHOOK_TIMESHEETS_URL=https://hook.us2.make.com/p43xnik7eupifvurj4maastrmlmxro5a` (Reports já adicionada)

### P1
- Botão dedicado "Salvar no OneDrive" no UI (manual trigger, sem precisar baixar)
- Indicador visual no UI mostrando última sincronização ao OneDrive

### P2
- Refatorar `/app/frontend/app/supervisor/edit-report.tsx` (>1100 linhas)
- Extrair PDF generation de `routes/reports.py` (1456 linhas) e `routes/timesheets.py` (674 linhas) para modules dedicados
- DRY: dependência compartilhada `get_current_user_pdf` para JWT (?token + Bearer header)
- Considerar plano pago Make.com (Free: 1000 ops/mês ≈ 500 PDFs entre Reports + Timesheets)

## Key API Endpoints
- `GET /api/reports/{id}/pdf?download=1` — download PDF + dispara OneDrive webhook (kind=report)
- `GET /api/timesheets/{id}/pdf?download=1` — download PDF + dispara OneDrive webhook (kind=timesheet)
- `GET /api/{reports|timesheets}/{id}/pdf` (sem download=1) — preview inline (não dispara webhook)

## Critical Setup Info
- **MongoDB**: usar apenas `MONGO_URL` e `DB_NAME` do backend/.env
- **Frontend backend URL**: `EXPO_PUBLIC_BACKEND_URL` (preview) e `EXPO_PUBLIC_REPORT_API_URL` (Railway prod)
- **Make.com Free plan**: 1000 ops/mês — cada PDF baixado = 2 ops (Create Folder + Upload)
- **OneDrive Personal Account**: NÃO usar Azure Entra ID/Power Automate — só Make.com Webhook
- **Backend asyncio.create_task**: precisa de restart do supervisor após mudar .env (uvicorn --reload não detecta .env)

## Test Credentials
- Admin: `admin@twasrepair.com` / `admin123`
- Supervisor: `supervisor@twasrepair.com` / `super123`
