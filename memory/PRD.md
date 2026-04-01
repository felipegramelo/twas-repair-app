# TWAS REPAIR - PRD

## Core Features
### Reports
- Relatorio de Servico - PDF Capa: Linhas separadas para CLIENTE, EMBARCACAO e LOCAL
- Abaixo da foto da capa: nome da EMBARCACAO
- Secoes completas com NDT, Avaliacao, etc

### Relatorio Diario
- Criacao: Apenas Data Inicio (Data Fim = ultima data das entradas diarias)
- Secoes: Introducao, Equipamentos, Objetivo, Descricao dos Servicos
- Entradas Diarias: subsecoes 4.1, 4.2... com data, descricao e fotos

### Functions
- E=ENGENHEIRO, EN=ENCARREGADO, Sup=SUPERVISOR, T=TECNICO, M=MECANICO, TS=TECNICO DE SEGURANCA

### BM (Boletim de Medicao)
- Selecao de timesheets, date pickers, edicao, impostos toggle (%)
- Campos "COD." e "Linha" por item/funcao (nao mais global)
- Titulo "BOLETIM DE MEDICAO" centralizado no PDF
- Auto-busca da proposta ao selecionar O.S. com proposal_id vinculado

### Proposta Comercial (REESTRUTURADA em 01/04/2026)
- Formato secoes numeradas (sem tabela)
- Indice visivel apenas no formulario (NAO no PDF)
- Cada secao: numero + titulo + descricao + valor + opcao de imagem
- "Termos e Condicoes Gerais" como ultima secao numerada com texto padrao editavel
- Dois PDFs: Comercial (com precos) e Tecnica (sem precos)
- Informar P.O.: muda status, cria O.S. automaticamente
- Filtros por mes/ano

### Dashboard Financeiro (NOVO em 01/04/2026)
- Pagina admin com controle de permissao (dashboard_access)
- Cards: Total BMs, Propostas, O.S., Timesheets
- Grafico de barras: BMs por mes (12 meses)
- Barra horizontal empilhada: Propostas por status
- Top 5 clientes por valor de BM
- Toggle de permissao na pagina de administradores

### Ordens de Servico
- Campos: Numero, Cliente, Embarcacao, Local, Servico, Funcionarios
- Filtro por mes/ano

## Credentials
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Completed (as of 2026-04-01)
- [x] Role-based auth, Timesheet/Report CRUD, PDF generation
- [x] Arquivo por O.S., BM with all features
- [x] Supervisor Finalization, Admin Revert, Duplicate Timesheet
- [x] Daily Report: Entradas Diarias como subsecoes
- [x] Proposta Comercial: CRUD, auto-numeracao, PDF Comercial/Tecnica
- [x] Informar P.O. + Auto-criacao de O.S.
- [x] Filtros por mes/ano em Propostas e Ordens de Servico
- [x] PDF Capa: Separar EMBARCACAO e LOCAL
- [x] BM: COD. e Linha por item, titulo centralizado, auto-busca proposta
- [x] Dashboard Financeiro com graficos e controle de acesso
- [x] Reestruturacao de Propostas: secoes numeradas, indice, termos gerais

## Backlog
### P1
- Refactor backend/server.py into modular structure (3900+ lines)
- Add schedule_type (06-18 / 07-19) to Service Orders UI
- Adicionar upload de imagens/arquivos por secao nas propostas
### P2
- Refactor edit-report.tsx into smaller components
- Offline Mode / EAS Build
