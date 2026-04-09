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
- [x] Propostas Comerciais (secoes/subsecoes, fotos, termos gerais, campo servico)
- [x] Propostas Tecnicas (PDF)
- [x] iOS: GestureHandlerRootView + SafeAreaProvider
- [x] iOS: File pickers nativos (expo-image-picker, expo-document-picker)
- [x] iOS: PDF download/sharing (expo-file-system/legacy + expo-sharing)
- [x] iOS: Alert.alert em vez de window.alert
- [x] iOS: Inline pickers no Timesheet (sem modais aninhados)
- [x] iOS: Modal OS picker no Create Report
- [x] iOS: InlineCalendar para datas de periodo no Create Report
- [x] iOS: BulletTextArea com auto-bullets no Enter (edit-report)
- [x] iOS: Upload de imagens com 3 opcoes (Camera/Fototeca/Arquivo)
- [x] iOS: Fix expo-file-system/legacy (downloadAsync deprecated)
- [x] Compartilhamento de Documentos (Access Control) - Backend completo
- [x] Compartilhamento de Documentos - UI Admin (service-reports, daily-reports, timesheets)
- [x] Compartilhamento de Documentos - Badge "Compartilhado" no painel Supervisor
- [x] Compartilhamento de Documentos - Duplicar documentos compartilhados (Supervisor)
- [x] Troca de Senha - Supervisor pode trocar propria senha
- [x] Redefinir Senha - Admin pode redefinir senha de qualquer supervisor

## Tarefas Pendentes

### P1 (Alta Prioridade)
- [ ] Otimizar query N+1 em `get_service_orders` (usar $lookup)
- [ ] Adicionar campo `schedule_type` (06-18 / 07-19) nas Ordens de Servico
- [ ] Refatorar `backend/server.py` (>4200 linhas -> estrutura modular)

### P2 (Media Prioridade)
- [ ] Refatorar `frontend/app/supervisor/edit-report.tsx` em componentes menores
- [ ] Modo Offline (AsyncStorage + fila de sincronizacao)

## Credenciais de Teste
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123
