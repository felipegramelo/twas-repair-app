# Timesheet Corporativo - TWAS Repair

## Problema Original
Aplicativo de timesheet corporativo usando Expo para mobile, com geração de PDF seguindo modelo específico.

## Requisitos
- **Autenticação**: Admin e Supervisor com email corporativo (JWT)
- **Admin**: Gerencia funcionários, ordens de serviço, supervisores. Visualiza/exclui todos os timesheets e O.S.
- **Supervisor**: Preenche timesheets da equipe. Pode excluir seus timesheets
- **PDF**: Layout exato do modelo fornecido, A4, uma página, com logo, legenda em 6 colunas

## Credenciais de Teste
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Stack
- Frontend: Expo + React Native + expo-router
- Backend: FastAPI + MongoDB + reportlab (PDF)
- Auth: JWT

## Implementado
- [x] CRUD completo: Employees, Service Orders, Users/Supervisors, Timesheets
- [x] Autenticação JWT com roles (admin/supervisor)
- [x] Dashboards por role (Admin e Supervisor)
- [x] Geração de PDF com reportlab matching template
- [x] PDF A4 em página única com todas as seções
- [x] Download de PDF (web) com anti-cache
- [x] Edição de timesheet
- [x] Legenda do PDF: título "Legenda / Caption" + 6 colunas PT/EN - 25/02/2026
- [x] Observações como título separado acima da caixa - 25/02/2026
- [x] Botão de excluir timesheet (admin e supervisor) com window.confirm na web - 25/02/2026
- [x] Botão de excluir O.S. corrigido para funcionar na web - 25/02/2026
- [x] Todos os botões de delete (employees, supervisors, O.S., timesheets) usam window.confirm na web - 25/02/2026
- [x] Deploy health check passed - 25/02/2026

## Backlog / Futuro
- [ ] Refatorar server.py (extrair PDF para módulo separado)
- [ ] Suporte a download de PDF em dispositivos nativos (expo-file-system + expo-sharing)
