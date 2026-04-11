# TWAS REPAIR - PRD (Product Requirements Document)

## Problema Original
Unificar dois apps (Timesheet Tracker e Service/Daily Report) em um unico app "TWAS REPAIR" com autenticacao role-based (Admin/Supervisor), CRUD completo, geracao avancada de PDF A4, e funcionalidade cross-platform (React Native Web + iOS).

## Stack Tecnica
- Frontend: React Native (Expo SDK 54, Expo Router), TypeScript
- Backend: FastAPI, MongoDB (motor) - Estrutura Modular
- PDF: ReportLab + PyMuPDF (fitz)
- Modulos Nativos: expo-sharing, expo-file-system/legacy, expo-image-picker, expo-document-picker
- Storage: Emergent Object Storage

## Arquitetura Backend (Refatorado)
```
backend/
  server.py          (59 linhas - app init + router includes)
  database.py        (conexao MongoDB)
  config.py          (JWT, bcrypt, storage helpers)
  dependencies.py    (auth dependencies)
  models.py          (Pydantic models)
  routes/
    auth.py          (login, registro, users, senha)
    employees.py     (CRUD funcionarios)
    service_orders.py (CRUD OS + arquivo)
    timesheets.py    (CRUD + PDF timesheets)
    reports.py       (CRUD + fotos + PDF relatorios)
    proposals.py     (CRUD + fotos + PDF propostas)
    boletim.py       (BM calc + CRUD + PDF)
    dashboard.py     (dashboard financeiro + toggles acesso)
    sharing.py       (compartilhamento documentos)
```

## REGRAS IMPORTANTES - Expo SDK 54 / iOS
- `expo-file-system`: SEMPRE usar import de `expo-file-system/legacy`
- NAO usar APIs web-only sem `Platform.OS` check
- Modais aninhados NAO funcionam no iOS nativo
- Upload de imagens no iOS deve oferecer 3 opcoes: Camera, Fototeca, Arquivo

## Funcionalidades Implementadas
- [x] Autenticacao (Admin/Supervisor) com JWT
- [x] CRUD Timesheets (criar/editar/excluir, PDF) + Numero sequencial por OS (admin)
- [x] CRUD Relatorios (servico e diario, PDF)
- [x] Ordens de Servico (CRUD + Arquivo por O.S.)
- [x] Boletim de Medicao
- [x] Dashboard Financeiro
- [x] Propostas Comerciais (secoes/subsecoes, fotos, termos gerais, campo servico, campo local)
- [x] Auto-preenchimento da OS ao aprovar Proposta (embarcacao, local, servico)
- [x] iOS: Todas as funcionalidades nativas
- [x] Compartilhamento de Documentos (Access Control)
- [x] Troca/Redefinicao de Senha
- [x] Tema Preto (#000000) aplicado em toda a interface
- [x] Backend refatorado de monolito (4312 linhas) para estrutura modular (59 + routes/)

## Tarefas Pendentes

### P1 (Alta Prioridade)
- [ ] Adicionar campo `schedule_type` (06-18 / 07-19) na UI das Ordens de Servico

### P2 (Media Prioridade)
- [ ] Refatorar `frontend/app/supervisor/edit-report.tsx` em componentes menores
- [ ] Modo Offline (AsyncStorage + fila de sincronizacao)

## Credenciais de Teste
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123
