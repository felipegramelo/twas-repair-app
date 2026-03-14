# Timesheet Corporativo - TWAS Repair

## Problema Original
Aplicativo de timesheet corporativo usando Expo para mobile/web, com geracao de PDF seguindo modelo especifico.

## Stack
- Frontend: Expo + React Native + expo-router
- Backend: FastAPI + MongoDB + reportlab (PDF)
- Auth: JWT

## Credenciais de Teste
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Implementado
- [x] CRUD completo: Employees, Service Orders, Users/Supervisors, Timesheets
- [x] Autenticacao JWT com roles (admin/supervisor)
- [x] Dashboards por role (Admin e Supervisor)
- [x] Geracao de PDF com reportlab matching template (A4, 1 pagina)
- [x] Download de PDF (web) com anti-cache
- [x] Edicao de timesheet com calendario e seletor de horario
- [x] Legenda do PDF: titulo + 6 colunas PT/EN
- [x] Observacoes como titulo separado no PDF
- [x] Botao de excluir com window.confirm na web
- [x] Lista de timesheets atualiza automaticamente (useFocusEffect)
- [x] Funcionarios vinculados a O.S. - Multi-select na tela admin de O.S.
- [x] Calendario visual para selecao de data no timesheet
- [x] Seletor de horario 30 em 30 min para inicio/fim de servico e viagem
- [x] Filtro de funcionarios - Ao selecionar O.S., so mostra funcionarios vinculados
- [x] Limite 12 entradas por timesheet - Frontend bloqueia adicao, backend valida POST/PUT
- [x] Compatibilidade mobile (expo-file-system + expo-sharing para PDFs)
- [x] Assinatura do supervisor no PDF com funcao editavel
- [x] Acesso admin a PDFs (abrir/baixar)
- [x] Ordenacao de entradas por data e nome
- [x] Icones/logo do app personalizados
- [x] Contador de caracteres (800) no campo de observacoes
- [x] Multi-select checkbox para funcionarios na O.S. - 28/02/2026
- [x] Intervalo de datas no dashboard do supervisor - 28/02/2026
- [x] Servico visivel no card do timesheet (supervisor + admin) - 28/02/2026
- [x] Layout do card reorganizado: O.S. + icones no topo, detalhes abaixo - 28/02/2026
- [x] Alterar Senha - Tela para admin alterar propria senha - 03/03/2026
- [x] Gerenciar Administradores - CRUD completo de admins - 03/03/2026
- [x] Bug fix: Ordenacao de datas corrigida (DD/MM/YYYY convertido para YYYY-MM-DD) - 06/03/2026
- [x] Servico no picker de O.S. em italico - 06/03/2026
- [x] PDF com borda de pagina, cabecalho e rodape do relatorio de servico - 14/03/2026
- [x] **PDF: borda fina (0.5pt), cabecalho/rodape alinhados com largura das tabelas** - 14/03/2026
- [x] **Checkbox "Tem viagem?"** - Se desmarcado, viagem mostra "-" no PDF. Se marcado, pickers de horario aparecem - 14/03/2026

## Modelos de Dados
- **Employee**: name
- **Service Order**: os_number, client, location, service, employees[{employee_id, function}]
- **Timesheet**: os_id, os_number, client, location, service, entries[{date, employee_id, employee_name, employee_function, service_start, service_end, travel_start, travel_end}], observations, supervisor_id, supervisor_name, supervisor_function
- **User**: email, password_hash, role (admin/supervisor), name

## Backlog / Futuro
- [ ] Refatorar: centralizar funcoes de PDF entre supervisor e admin
- [ ] Refatorar: dividir server.py em modulos
- [ ] Preparacao EAS Build para app stores
- [ ] Modo offline com sincronizacao automatica
