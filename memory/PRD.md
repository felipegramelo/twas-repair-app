# TWAS Repair - Product Requirements Document

## Original Problem Statement
Unificar dois apps (Timesheet + Service/Daily Report) em um único app "TWAS REPAIR" com autenticação por roles (Admin/Supervisor), CRUD completo para Timesheets/Reports/Service Orders, geração de PDFs A4, Boletim de Medição, Dashboard Financeiro, sincronização OneDrive, build iOS via EAS.

## User's preferred language
Portuguese (pt-BR)

## Production Deployment
- **Web**: Vercel (frontend)
- **Backend**: Railway projeto `dynamic-compassion` / serviço `twas-repair-app` (`twas-repair-app-production.up.railway.app`) — NÃO mexer no `empowering-ambition`
- **Database**: MongoDB (managed)
- **iOS**: EAS Build (yarn-based)

## Architecture
```
/app/backend/
  routes/ — auth, service_orders, reports, timesheets, boletim, holidays, proposals, translate, projects
  services/ — onedrive.py (Make.com webhook helper — 3 kinds: report/timesheet/project)
  models.py, database.py, server.py
  .env — MAKE_WEBHOOK_REPORTS_URL, MAKE_WEBHOOK_TIMESHEETS_URL, MAKE_WEBHOOK_PROJECTS_URL(vazia)

/app/frontend/
  app/admin/ — projects.tsx, edit-project.tsx (novos)
  app/supervisor/ — projects.tsx (novo)
  services/api.ts — projectAPI (novo)
```

## Key DB Schema
- `service_orders` (os_number, embarcacao, client, location, service, ...)
- `reports` (os_number, photo_layout, representante_twas, representante_cliente, ...)
- `timesheets`
- `projects` (NOVO — os_number, title, embarcacao, client, start_date, end_date, lock_end_date, tasks[])
  - tasks[]: id (UUID), parent_id, name, duration_value, duration_unit (dias/hrs), start_date, end_date, progress_percent, order, notes

## 3rd Party Integrations
- Emergent Object Storage / Gemini Nano Banana (Universal Key)
- **Make.com Webhook → OneDrive Personal (2 cenários ativos):**
  - TWAS Reports → OneDrive: `hook.us2.make.com/haeb0tfy171wrr3t7sqrw4knshcqr7kx`
  - TWAS Timesheets → OneDrive: `hook.us2.make.com/p43xnik7eupifvurj4maastrmlmxro5a`
- Cenário Projects: ainda NÃO criado (Fase 3)

## What's Been Implemented (Recent)

### 2026-07-08 — Módulo Projetos MVP (Fase 1) ✅
- Backend `routes/projects.py`: CRUD completo + hierarquia parent/child + auto-recalc end_date + cascade delete
- PDF landscape A4 com **Gantt visual** (barras coloridas, portion azul = concluído)
- Permissões: Admin CRUD full; Supervisor apenas PATCH progress_percent
- Frontend Admin: tela de listagem + modal criar (com input manual OS + chips de OS existentes) + tela de edição com árvore de tarefas
- Frontend Supervisor: tela de projetos com expand/collapse + modal de edição de % apenas
- Bug fix pós-teste inicial: input manual de OS adicionado (não depender só de chips), título tornou-se opcional
- **Validado**: testing_agent iteration_45 (backend 18/18) + iteration_46 (frontend 100%)

### 2026-06-28/29 — OneDrive Bug Fix ✅
- Corrigido: envio de `os_number=''` derrubava cenários Make.com. Agora usa 'SEM-OS' como fallback.
- Iterations 43/44 validados

### Anteriores
- OneDrive Reports+Timesheets, iOS EAS build, HEIC upload, photo_layout, ?download=1, Vessel/Embarcação, Representantes, etc.

## Prioritized Backlog

### P1
- **Fase 2 — Projetos**: Melhorias visuais no Gantt (dias/labels no eixo x, milestones), calendário para inputs de data (não texto)
- **Fase 3 — Projetos → OneDrive**: criar 3º cenário Make.com para Projects + configurar `MAKE_WEBHOOK_PROJECTS_URL` (backend/local + Railway)
- Save to GitHub para Railway pegar routes/projects.py

### P2
- Refatorar edit-project.tsx (calendar widget em vez de texto ISO)
- testID prop (RN Web canonical) em vez de data-testid onde possível (para melhor test coverage automatizado)
- Splitting rot es/reports.py (>1500 linhas) e routes/timesheets.py (>700 linhas) em módulos separados
- Índice OS Archive incluir projetos

## Key API Endpoints
### Projects (NOVO)
- `POST /api/projects` (admin)
- `GET /api/projects[?os_number=...]` (all authenticated)
- `GET /api/projects/{id}` (all)
- `PUT /api/projects/{id}` (admin)
- `DELETE /api/projects/{id}` (admin)
- `POST /api/projects/{id}/tasks` (admin)
- `PUT /api/projects/{id}/tasks/{task_id}` (admin)
- `PATCH /api/projects/{id}/tasks/{task_id}/progress` (admin + supervisor)
- `DELETE /api/projects/{id}/tasks/{task_id}` (admin, cascade)
- `GET /api/projects/{id}/pdf?download=1&token=...` (auth via query OR Bearer)

### Reports / Timesheets (existentes)
- `GET /api/reports/{id}/pdf?download=1` — download + OneDrive
- `GET /api/timesheets/{id}/pdf?download=1` — download + OneDrive

## Critical Setup Info
- **MongoDB**: usar apenas `MONGO_URL` e `DB_NAME`
- **Frontend**: `EXPO_PUBLIC_BACKEND_URL` (preview) e `EXPO_PUBLIC_REPORT_API_URL` (Railway prod)
- **Make.com Free plan**: 1000 ops/mês, ~500 PDFs (2 ops por PDF)
- **OneDrive Personal**: SÓ Make.com Webhook funciona (não Entra ID/Power Automate)
- **Backend restart necessário após mudanças em .env** (uvicorn --reload não detecta .env)
- **auth JWT**: `access_token` no login response (não `token`); login endpoint retorna `{access_token, token_type, user}`

## Test Credentials
- Admin: `admin@twasrepair.com` / `admin123`
- Supervisor: `supervisor@twasrepair.com` / `super123`

## Bug Fixes Recentes
- **SEM-OS fallback** (iter 44): impede que reports/timesheets sem os_number derrubem cenários Make.com
- **OS input manual** (iter 46): resolve UX bug onde admin não conseguia digitar OS no modal
