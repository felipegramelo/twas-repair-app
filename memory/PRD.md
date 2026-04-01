# TWAS REPAIR - PRD

## Core Features

### Reports
- Relatorio de Servico - PDF Capa: Linhas separadas para CLIENTE, EMBARCACAO e LOCAL
- Relatorio Diario: Entradas Diarias como subsecoes

### BM (Boletim de Medicao)
- Campos "COD." e "Linha" por item/funcao
- Titulo centralizado, auto-busca proposta

### Proposta Comercial (Reestruturada 01/04/2026)
- Info do cliente no PDF em texto simples (sem tabela)
- Secoes numeradas sequencialmente (1., 2., 3....)
- Indice visivel apenas no formulario (nao no PDF)
- Cada secao: numero + titulo + descricao + valor + upload de fotos/arquivos
- "Termos e Condicoes Gerais" como ultima secao com texto padrao editavel
- Upload de fotos/arquivos por secao (object storage)
- Fotos aparecem automaticamente no PDF
- Dois PDFs: Comercial (com precos) e Tecnica (sem precos)
- Informar P.O.: muda status, cria O.S. automaticamente

### Dashboard Financeiro (01/04/2026)
- Pagina admin com controle de permissao (dashboard_access)
- Cards resumo, grafico BMs por mes, propostas por status, top clientes

### Ordens de Servico
- Campos: Numero, Cliente, Embarcacao, Local, Servico, Funcionarios
- Filtro por mes/ano

## Credentials
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Completed
- [x] Role-based auth, Timesheet/Report CRUD, PDF generation
- [x] Arquivo por O.S., BM com todos os recursos
- [x] Supervisor Finalization, Admin Revert, Duplicate Timesheet
- [x] Proposta Comercial: CRUD, auto-numeracao, PDFs
- [x] Informar P.O. + Auto-criacao de O.S.
- [x] BM: COD. e Linha por item, titulo centralizado, auto-busca proposta
- [x] Dashboard Financeiro com graficos e controle de acesso
- [x] Propostas: Secoes numeradas, indice, termos gerais, upload de fotos/arquivos, PDF sem tabela

## Backlog
### P1
- Refactor backend/server.py em estrutura modular (4000+ linhas)
- Adicionar schedule_type (06-18 / 07-19) nas Ordens de Servico
### P2
- Refactor edit-report.tsx em componentes menores
- Modo Offline / EAS Build
