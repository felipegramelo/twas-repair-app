# Timesheet Corporativo - TWAS Repair

## Problema Original
Aplicativo de timesheet corporativo usando Expo para mobile, com geração de PDF seguindo modelo específico.

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
- [x] Edição de timesheet
- [x] Legenda do PDF: título + 6 colunas PT/EN
- [x] Observações como título separado no PDF
- [x] Botão de excluir (O.S., timesheets, employees, supervisors) com window.confirm na web
- [x] Lista de timesheets atualiza automaticamente (useFocusEffect)
- [x] **Funcionários vinculados a O.S.** — Multi-select na tela admin de O.S. - 25/02/2026
- [x] **Calendário visual** para seleção de data no timesheet - 25/02/2026
- [x] **Seletor de horário 30 em 30 min** para início/fim de serviço e viagem - 25/02/2026
- [x] **Filtro de funcionários** — Ao selecionar O.S., só mostra funcionários vinculados - 25/02/2026

## Modelos de Dados
- **Employee**: name, function
- **Service Order**: os_number, client, location, service, **employee_ids[]**
- **Timesheet**: os_id, entries[], observations, supervisor_id

## Backlog / Futuro
- [ ] Refatorar server.py (extrair PDF para módulo separado)
- [ ] Suporte a download de PDF em dispositivos nativos (expo-file-system + expo-sharing)
- [ ] Edição de timesheet com calendário e seletor de horário (mesma UX do create)
