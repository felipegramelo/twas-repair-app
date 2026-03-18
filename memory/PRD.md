# TWAS REPAIR - Aplicativo Corporativo Unificado

## Problema Original
Unificar dois aplicativos separados - Timesheet Tracker e Service/Daily Report - em um único aplicativo corporativo "TWAS REPAIR", com geração de PDF, gerenciamento de timesheets e relatórios de serviço/diários.

## Stack
- Frontend: Expo + React Native + expo-router + TypeScript
- Backend: FastAPI + MongoDB + reportlab (PDF)
- Auth: JWT

## Credenciais de Teste
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Implementado
- [x] CRUD completo: Employees, Service Orders, Users/Supervisors, Timesheets
- [x] Autenticação JWT com roles (admin/supervisor)
- [x] Dashboards por role (Admin e Supervisor)
- [x] Geração de PDF Timesheet com reportlab (A4, 1 página)
- [x] Download/visualização de PDF (web)
- [x] Edição de timesheet com calendário e seletor de horário
- [x] Limite 12 entradas por timesheet
- [x] Checkbox "Tem viagem?" com toggle no PDF
- [x] Contador de caracteres (1200) no campo de observações
- [x] Gerenciar Administradores - CRUD completo
- [x] Alterar Senha - Tela para admin
- [x] **UNIFICAÇÃO: Título "TWAS REPAIR"** - 18/03/2026
- [x] **UNIFICAÇÃO: Dashboard supervisor sem abas - lista unificada** - 18/03/2026
- [x] **UNIFICAÇÃO: Modal "Criar Novo" com 3 opções (Timesheet, Rel. Serviço, Rel. Diário)** - 18/03/2026
- [x] **UNIFICAÇÃO: CRUD completo de Relatórios (local, mesmo banco)** - 18/03/2026
- [x] **UNIFICAÇÃO: Relatórios usam mesmas Ordens de Serviço locais** - 18/03/2026
- [x] **UNIFICAÇÃO: Tela de edição de relatórios com seções editáveis** - 18/03/2026
- [x] **UNIFICAÇÃO: Geração de PDF de relatórios (RELATÓRIO TÉCNICO / DIÁRIO)** - 18/03/2026
- [x] **UNIFICAÇÃO: Cards admin para Relatórios de Serviço e Diários** - 18/03/2026
- [x] **UNIFICAÇÃO: Telas de listagem de relatórios (admin)** - 18/03/2026
- [x] **UNIFICAÇÃO: PDF inclui conteúdo editável dos relatórios** - 18/03/2026

## Endpoints de Relatórios
- POST /api/reports - Criar relatório
- GET /api/reports - Listar todos
- GET /api/reports/{id} - Obter por ID
- PUT /api/reports/{id} - Atualizar
- DELETE /api/reports/{id} - Excluir
- GET /api/reports/{id}/pdf - Gerar PDF

## Backlog / Futuro
- [ ] Modo offline com sincronização automática (P1)
- [ ] Preparação EAS Build para app stores (P2)
- [ ] Refatorar: centralizar funções de PDF
- [ ] Refatorar: dividir server.py em módulos
