# Timesheet Corporativo - TWAS Repair

## Problema Original
Aplicativo de timesheet corporativo usando Expo para mobile/web, com geração de PDF seguindo modelo específico.

## Stack
- Frontend: Expo + React Native + expo-router
- Backend: FastAPI + MongoDB + reportlab (PDF)
- Auth: JWT

## Credenciais de Teste
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Implementado
- [x] CRUD completo: Employees, Service Orders, Users/Supervisors, Timesheets
- [x] Autenticação JWT com roles (admin/supervisor)
- [x] Dashboards por role (Admin e Supervisor)
- [x] Geração de PDF com reportlab matching template (A4, 1 página)
- [x] Download de PDF (web) com anti-cache
- [x] Edição de timesheet com calendário e seletor de horário (mesma UX do create) - 25/02/2026
- [x] Legenda do PDF: título + 6 colunas PT/EN
- [x] Observações como título separado no PDF
- [x] Botão de excluir com window.confirm na web
- [x] Lista de timesheets atualiza automaticamente (useFocusEffect)
- [x] Funcionários vinculados a O.S. — Multi-select na tela admin de O.S. - 25/02/2026
- [x] Calendário visual para seleção de data no timesheet - 25/02/2026
- [x] Seletor de horário 30 em 30 min para início/fim de serviço e viagem - 25/02/2026
- [x] Filtro de funcionários — Ao selecionar O.S., só mostra funcionários vinculados - 25/02/2026
- [x] **PDF multi-página** — Paginação com 12 entradas por página, cada página com observações próprias - 25/02/2026
- [x] **Per-page sections** — Cada página do PDF tem cabeçalho, legenda, aprovação, observações e rodapé - 25/02/2026
- [x] **Fix API _id/id inconsistency** — GET/PUT timesheets retorna `id` consistentemente - 25/02/2026
- [x] **Fix Alert.alert web** — Todas as mensagens de erro/sucesso usam window.alert/confirm na web - 25/02/2026
- [x] **Fix travel display** — Viagem "0" não é mais exibida nas entradas - 25/02/2026

- [x] **Limite 12 entradas por timesheet** — Frontend bloqueia adição, backend valida POST/PUT, contador X/12 - 25/02/2026

## Modelos de Dados
- **Employee**: name
- **Service Order**: os_number, client, location, service, employees[{employee_id, function}]
- **Timesheet**: os_id, os_number, client, location, service, entries[], observations, supervisor_id, supervisor_name

## Arquitetura
```
/app
├── backend/
│   ├── .env
│   ├── requirements.txt
│   ├── server.py         # FastAPI: models, endpoints, PDF logic
│   └── tests/            # pytest tests
├── frontend/
│   ├── services/api.ts   # Centralized API functions
│   ├── app/
│   │   ├── admin/        # Admin screens
│   │   └── supervisor/   # Supervisor screens (dashboard, create, edit)
│   ├── contexts/AuthContext.tsx
│   ├── types/index.ts
│   └── .env
└── memory/PRD.md
```

## Backlog / Futuro
- [ ] Refatorar server.py (extrair PDF para módulo separado)
- [ ] Suporte a download de PDF em dispositivos nativos (expo-file-system + expo-sharing)
