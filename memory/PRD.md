# TWAS REPAIR - PRD (Product Requirements Document)

## Problema Original
Unificar dois apps (Timesheet Tracker e Service/Daily Report) em um unico app "TWAS REPAIR" com autenticacao role-based (Admin/Supervisor), CRUD completo, geracao avancada de PDF A4, e funcionalidade cross-platform (React Native Web + iOS + Android).

## Stack Tecnica
- Frontend: React Native (Expo SDK 54, Expo Router), TypeScript
- Backend: FastAPI, MongoDB (motor) - Estrutura Modular com indices criados no startup
- PDF: ReportLab + PyMuPDF (fitz)
- Storage: Emergent Object Storage
- Deploy: Backend no Railway (Dockerfile), Frontend iOS/Android via EAS

## Arquitetura Backend (Refatorado)
```
backend/
  server.py          (app init + router includes + indices no startup)
  database.py, config.py, dependencies.py, models.py
  routes/ (auth, employees, service_orders, timesheets, reports, proposals, boletim, dashboard, sharing, translate)
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
- [x] Traducao automatica (EN/ES) via Gemini
- [x] PDF OS atualizado (2026-04-21):
    - Contatos reais: Daniel Gussen (Comercial), Felipe Melo (Tecnico), Jorge Campos (Logistica)
    - Secao EQUIPE mostra apenas quantidade por funcao (nomes completos: Tecnico, Mecanico, etc)
    - Previsao de inicio / Previsao de termino (era "P. de inicio / P. de termino")
    - Linha "Horario de trabalho" com valor 06h-18h ou 07h-19h
- [x] Campo schedule_type (06-18 / 07-19) na UI de OS (2026-04-21)
- [x] Otimizacao N+1 em /admin/os-archive: 3 queries totais (batch com $in) ao inves de 1+2N (2026-04-21)
- [x] Indices MongoDB criados no startup: timesheets.os_id, reports.os_id, reports.(os_id,status), service_orders.os_number
- [x] URL Production hardcoded em frontend/services/config.ts (2026-04-25)
    - Evita que builds Android via Emergent ("Re-deploy and generate build") apontem para o banco preview
    - Todas as 22 ocorrencias de `process.env.EXPO_PUBLIC_BACKEND_URL` substituidas por `BACKEND_URL` de `services/config.ts`
    - Override opcional via EXPO_PUBLIC_BACKEND_URL_OVERRIDE para testes
    - Arquivos atualizados: AuthContext.tsx, api.ts, services/config.ts, admin/(service-orders, boletim-medicao, daily-reports, timesheets, propostas, service-reports, os-archive), supervisor/(index, edit-report)
    - Bug pre-existente corrigido: codigo orfao no fim de service-orders.tsx (linhas 480-485)

## Versao Atual: 1.0.22 (proxima build Android)

## Deploy Web (Vercel) - Configurado em 2026-04-28
- vercel.json + .vercelignore criados na raiz
- Build command: `cd frontend && yarn install --frozen-lockfile && npx expo export --platform web`
- Output dir: `frontend/dist`
- SPA rewrites configurados (todas rotas -> index.html)
- Build local validado: 22 rotas estaticas, 7.5MB, login funcionando contra Railway

## Credenciais de Teste
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Backlog (P1/P2)
- [P2] Refatorar frontend/app/supervisor/edit-report.tsx (>1000 linhas) em componentes menores
- [P2] Modo Offline com AsyncStorage + fila de sincronizacao
