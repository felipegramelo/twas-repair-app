# TWAS REPAIR - PRD (Product Requirements Document)

## Problema Original
Unificar dois apps (Timesheet Tracker e Service/Daily Report) em um unico app "TWAS REPAIR" com autenticacao role-based (Admin/Supervisor), CRUD completo, geracao avancada de PDF A4, e funcionalidade cross-platform (React Native Web + iOS).

## Stack Tecnica
- Frontend: React Native (Expo SDK 54, Expo Router), TypeScript
- Backend: FastAPI, MongoDB (motor)
- PDF: ReportLab + PyMuPDF (fitz)
- Modulos Nativos: expo-sharing, expo-file-system/legacy, expo-image-picker, expo-document-picker
- Storage: Emergent Object Storage

## REGRAS IMPORTANTES - Expo SDK 54 / iOS
- `expo-file-system`: SEMPRE usar import de `expo-file-system/legacy`
- NAO usar APIs web-only sem `Platform.OS` check (`window.alert`, `document.createElement`)
- Modais aninhados NAO funcionam no iOS nativo - usar renderizacao inline
- Pickers/calendarios devem ser inline dentro do modal pai no iOS
- Upload de imagens no iOS deve oferecer 3 opcoes: Camera, Fototeca, Arquivo

## Funcionalidades Implementadas
- [x] Autenticacao (Admin/Supervisor) com JWT
- [x] CRUD Timesheets (criar/editar/excluir, PDF)
- [x] CRUD Relatorios (servico e diario, PDF)
- [x] Ordens de Servico (CRUD + Arquivo por O.S.)
- [x] Boletim de Medicao
- [x] Dashboard Financeiro
- [x] Propostas Comerciais (secoes/subsecoes, fotos, termos gerais, campo servico, campo local)
- [x] Propostas Tecnicas (PDF)
- [x] iOS: Todas as funcionalidades nativas
- [x] Compartilhamento de Documentos (Access Control) - Backend + UI completo
- [x] Troca/Redefinicao de Senha (Admin e Supervisor)
- [x] Tema Preto (#000000) aplicado em toda a interface
- [x] Campo "Local" nas Propostas Comerciais
- [x] Auto-preenchimento da OS ao aprovar Proposta (embarcacao, local, servico)
- [x] Numero sequencial por OS nas Timesheets (visivel apenas para Admin: TS 01, TS 02, etc.)
- [x] Nome do app: "TWAS"
- [x] Rich text toggles no editor de relatorios

## Tarefas Pendentes

### P1 (Alta Prioridade)
- [ ] Adicionar campo `schedule_type` (06-18 / 07-19) na UI das Ordens de Servico
- [ ] Otimizar query N+1 em `get_service_orders` (usar $lookup)
- [ ] Refatorar `backend/server.py` (>4200 linhas -> estrutura modular)

### P2 (Media Prioridade)
- [ ] Refatorar `frontend/app/supervisor/edit-report.tsx` em componentes menores
- [ ] Modo Offline (AsyncStorage + fila de sincronizacao)

## Credenciais de Teste
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123
