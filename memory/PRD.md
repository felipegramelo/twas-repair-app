# TWAS REPAIR - Aplicativo Corporativo Unificado

## Problema Original
Unificar dois aplicativos separados - Timesheet Tracker e Service/Daily Report - em um único aplicativo corporativo "TWAS REPAIR", com geração de PDF, gerenciamento de timesheets e relatórios de serviço/diários.

## Stack
- Frontend: Expo + React Native + expo-router + TypeScript
- Backend: FastAPI + MongoDB + reportlab (PDF)
- Auth: JWT
- External API: Service Report Hub (https://service-report-hub-6.preview.emergentagent.com/api)

## Credenciais de Teste
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Implementado
- [x] CRUD completo: Employees, Service Orders, Users/Supervisors, Timesheets
- [x] Autenticação JWT com roles (admin/supervisor)
- [x] Dashboards por role (Admin e Supervisor)
- [x] Geração de PDF com reportlab matching template (A4, 1 página)
- [x] Download de PDF (web) com anti-cache
- [x] Edição de timesheet com calendário e seletor de horário
- [x] Legenda do PDF: título + 6 colunas PT/EN
- [x] Observações como título separado no PDF
- [x] Botão de excluir com window.confirm na web
- [x] Lista de timesheets atualiza automaticamente
- [x] Funcionários vinculados a O.S. - Multi-select na tela admin de O.S.
- [x] Calendário visual para seleção de data no timesheet
- [x] Seletor de horário 30 em 30 min
- [x] Filtro de funcionários por O.S.
- [x] Limite 12 entradas por timesheet
- [x] Compatibilidade mobile (expo-file-system + expo-sharing)
- [x] Assinatura do supervisor no PDF
- [x] Acesso admin a PDFs
- [x] Ordenação de entradas por data e nome
- [x] Ícones/logo do app personalizados
- [x] Contador de caracteres (1200) no campo de observações
- [x] Multi-select checkbox para funcionários na O.S.
- [x] Intervalo de datas no dashboard do supervisor
- [x] Serviço visível no card do timesheet
- [x] Layout do card reorganizado
- [x] Alterar Senha - Tela para admin
- [x] Gerenciar Administradores - CRUD completo
- [x] Bug fix: Ordenação de datas corrigida
- [x] PDF com borda de página, cabeçalho e rodapé
- [x] Checkbox "Tem viagem?" com toggle no PDF
- [x] **UNIFICAÇÃO: Título "TWAS REPAIR" no app** - 18/03/2026
- [x] **UNIFICAÇÃO: Integração com API externa de relatórios** - 18/03/2026
- [x] **UNIFICAÇÃO: Dashboard supervisor com 3 abas (Timesheets, Rel. Serviço, Rel. Diário)** - 18/03/2026
- [x] **UNIFICAÇÃO: Modal "Criar Novo" com 3 opções** - 18/03/2026
- [x] **UNIFICAÇÃO: Cards admin para Relatórios de Serviço e Diários** - 18/03/2026
- [x] **UNIFICAÇÃO: Telas de listagem de relatórios (admin)** - 18/03/2026
- [x] **UNIFICAÇÃO: Tela de criação de relatórios (supervisor)** - 18/03/2026
- [x] **UNIFICAÇÃO: Autenticação dual (timesheet API + report API)** - 18/03/2026
- [x] **UNIFICAÇÃO: Download/visualização PDF de relatórios** - 18/03/2026

## Modelos de Dados
- **Employee**: name
- **Service Order**: os_number, client, location, service, employees[{employee_id, function}]
- **Timesheet**: os_id, os_number, client, location, service, entries[{date, employee_id, employee_name, employee_function, service_start, service_end, travel_start, travel_end}], observations, supervisor_id, supervisor_name, supervisor_function
- **User**: email, password_hash, role (admin/supervisor), name
- **Report** (external): id, service_order_id, service_order_number, client, vessel, equipment, supervisor_id, supervisor_name, status, report_type (daily/service), sections[], created_at, updated_at

## Backlog / Futuro
- [ ] Refatorar: centralizar funções de PDF entre supervisor e admin
- [ ] Refatorar: dividir server.py em módulos
- [ ] Preparação EAS Build para app stores
- [ ] Modo offline com sincronização automática
