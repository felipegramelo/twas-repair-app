# TWAS REPAIR - PRD

## Reports
### Relatório de Serviço - PDF Capa
- Tabela da capa: Linhas separadas para CLIENTE, EMBARCAÇÃO e LOCAL (não mais "Embarcação / Local")
- Abaixo da foto da capa: mostra o nome da EMBARCAÇÃO (não o cliente/local)
- Seções completas com NDT, Avaliação, etc

### Relatório Diário
- Criação: Apenas Data Início (Data Fim = última data das entradas diárias)
- Seções: Introdução, Equipamentos, Objetivo, Descrição dos Serviços
- Entradas Diárias: subseções 4.1, 4.2... com data, descrição e fotos

## Supervisor Finalization Flow
- Botão "Finalizar" em timesheets e relatórios
- Admin pode "Devolver" documento ao supervisor
- Duplicar timesheet

## Functions
- E=ENGENHEIRO, EN=ENCARREGADO, Sup=SUPERVISOR, T=TÉCNICO, M=MECÂNICO, TS=TÉCNICO DE SEGURANÇA

## BM
- Seleção de timesheets, date pickers, edição, impostos toggle (%)

## Proposta Comercial
- CRUD completo com seções estruturadas (itens com título, descrição, valor)
- Auto-numeração: YYMM - Seq
- Dois PDFs: Proposta Comercial (com preço) e Proposta Técnica (sem preço)
- Informar P.O.: muda status para "Aprovada", cria O.S. automaticamente (SEQ - Nº_PROPOSTA)
- Filtros por mês/ano nas propostas e ordens de serviço

## Ordens de Serviço
- Campos: Número, Cliente, Embarcação (novo campo separado), Local, Serviço, Funcionários
- Filtro por mês/ano

## Credentials
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Completed (as of 2026-04-01)
- [x] Role-based auth, Timesheet/Report CRUD, PDF generation
- [x] Arquivo por O.S., BM with all features
- [x] Supervisor Finalization, Admin Revert, Duplicate Timesheet
- [x] Daily Report: Entradas Diárias como subseções
- [x] Proposta Comercial: CRUD, auto-numeração, PDF Comercial/Técnica
- [x] Informar P.O. + Auto-criação de O.S.
- [x] Filtros por mês/ano em Propostas e Ordens de Serviço
- [x] PDF Capa: Separar EMBARCAÇÃO e LOCAL em linhas distintas, foto mostra embarcação

## Backlog
### P1
- Refactor backend/server.py into modular structure (3700+ lines)
- Add schedule_type (06-18 / 07-19) to Service Orders UI
### P2
- Refactor edit-report.tsx into smaller components
- Offline Mode / EAS Build
