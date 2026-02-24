# Timesheet Corporativo - TWAS Repair

## Problema Original
Aplicativo de timesheet corporativo usando Expo para mobile, com geração de PDF seguindo modelo específico.

## Requisitos
- **Autenticação**: Admin e Supervisor com email corporativo (JWT)
- **Admin**: Gerencia funcionários, ordens de serviço, supervisores. Visualiza todos os timesheets
- **Supervisor**: Preenche timesheets da equipe, seleciona funcionários pré-cadastrados para OS específica
- **PDF**: Layout exato do modelo fornecido, A4, uma página, com logo da empresa

## Modelos de Dados
- **Employee**: name, function
- **Service Order**: os_number, client, location, service
- **Timesheet**: service_order_id, entries[], observations, supervisor_id

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
- [x] Download de PDF (web)
- [x] Edição de timesheet
- [x] Legenda do PDF em formato tabela 6 colunas (PT/EN) - 24/02/2026
- [x] Rodapé com endereço da empresa na mesma página - 24/02/2026

## Backlog / Futuro
- [ ] Refatorar server.py (extrair PDF para módulo separado)
- [ ] Deduplicar lógica de download no frontend
- [ ] Suporte a download de PDF em dispositivos nativos (expo-file-system + expo-sharing)
