# TWAS REPAIR - PRD

## Core Features

### Reports
- Relatorio de Servico - PDF Capa: Linhas separadas para CLIENTE, EMBARCACAO e LOCAL
- Relatorio Diario: Entradas Diarias como subsecoes

### Timesheet
- Validacao de conflito viagem vs servico: viagem nao pode coincidir com horario de servico
- Bloqueio no frontend (create + edit) e backend (create + update)
- Maximo 12 funcionarios por timesheet

### BM (Boletim de Medicao)
- Campos "COD." e "Linha" por item/funcao
- Titulo centralizado, auto-busca proposta

### Proposta Comercial
- Formato secoes numeradas (sem tabela), info cliente em texto simples
- Indice visivel no formulario com numeracao hierarquica (1, 1.1, 1.2, 2, 2.1...)
- Subsecoes dentro de cada secao (adicionar/editar/remover)
- Upload de fotos/arquivos por secao e subsecao com section_key
- "Termos e Condicoes Gerais" como ultima secao editavel com texto padrao
- Dois PDFs: Comercial (com precos) e Tecnica (sem precos)

### Dashboard Financeiro
- Pagina admin com controle de permissao (dashboard_access)
- Cards resumo, graficos BMs por mes, propostas por status, top clientes

### Ordens de Servico
- Campos: Numero, Cliente, Embarcacao, Local, Servico, Funcionarios

## Credentials
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Completed
- [x] Role-based auth, Timesheet/Report CRUD, PDF generation
- [x] Arquivo por O.S., BM com todos os recursos
- [x] Proposta Comercial: CRUD, secoes numeradas, termos gerais, upload fotos
- [x] Dashboard Financeiro com graficos e controle de acesso
- [x] Validacao de conflito viagem vs servico no timesheet (02/04/2026)
- [x] Propostas com subsecoes: indice hierarquico, CRUD subsecoes, fotos por subsecao, termos gerais (02/04/2026)
- [x] Backend update_proposal corrigido para preservar subsections (02/04/2026)

## Backlog
### P1
- Refactor backend/server.py em estrutura modular (~4100 linhas)
- Adicionar schedule_type (06-18 / 07-19) nas Ordens de Servico
### P2
- Refactor edit-report.tsx em componentes menores
- Modo Offline / EAS Build
