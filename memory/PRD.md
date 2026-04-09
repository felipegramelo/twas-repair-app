# TWAS REPAIR - PRD (Product Requirements Document)

## Problema Original
Unificar dois apps (Timesheet Tracker e Service/Daily Report) em um único app "TWAS REPAIR" com autenticação role-based (Admin/Supervisor), CRUD completo, geração avançada de PDF A4, e funcionalidade cross-platform (React Native Web + iOS).

## Stack Técnica
- Frontend: React Native (Expo SDK 54, Expo Router), TypeScript
- Backend: FastAPI, MongoDB (motor)
- PDF: ReportLab + PyMuPDF (fitz)
- Módulos Nativos: expo-sharing, expo-file-system/legacy, expo-image-picker, expo-document-picker
- Storage: Emergent Object Storage

## REGRAS IMPORTANTES - Expo SDK 54 / iOS
- `expo-file-system`: SEMPRE usar import de `expo-file-system/legacy`
- NÃO usar APIs web-only sem `Platform.OS` check (`window.alert`, `document.createElement`)
- Modais aninhados NÃO funcionam no iOS nativo - usar renderização inline
- Pickers/calendários devem ser inline dentro do modal pai no iOS
- Upload de imagens no iOS deve oferecer 3 opções: Câmera, Fototeca, Arquivo

## Funcionalidades Implementadas
- [x] Autenticação (Admin/Supervisor) com JWT
- [x] CRUD Timesheets (criar/editar/excluir, PDF)
- [x] CRUD Relatórios (serviço e diário, PDF)
- [x] Ordens de Serviço (CRUD + Arquivo por O.S.)
- [x] Boletim de Medição
- [x] Dashboard Financeiro
- [x] Propostas Comerciais (seções/subseções, fotos, termos gerais, campo serviço)
- [x] Propostas Técnicas (PDF)
- [x] iOS: GestureHandlerRootView + SafeAreaProvider
- [x] iOS: File pickers nativos (expo-image-picker, expo-document-picker)
- [x] iOS: PDF download/sharing (expo-file-system/legacy + expo-sharing)
- [x] iOS: Alert.alert em vez de window.alert
- [x] iOS: Inline pickers no Timesheet (sem modais aninhados)
- [x] iOS: Modal OS picker no Create Report
- [x] iOS: InlineCalendar para datas de período no Create Report
- [x] iOS: BulletTextArea com auto-bullets no Enter (edit-report)
- [x] iOS: Upload de imagens com 3 opções (Câmera/Fototeca/Arquivo)
- [x] iOS: Fix expo-file-system/legacy (downloadAsync deprecated)

## Tarefas Pendentes

### P1 (Alta Prioridade)
- [ ] Otimizar query N+1 em `get_service_orders` (usar $lookup)
- [ ] Adicionar campo `schedule_type` (06-18 / 07-19) nas Ordens de Serviço
- [ ] Refatorar `backend/server.py` (>4100 linhas → estrutura modular)

### P2 (Média Prioridade)
- [ ] Refatorar `frontend/app/supervisor/edit-report.tsx` em componentes menores
- [ ] Modo Offline (AsyncStorage + fila de sincronização)

## Credenciais de Teste
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123
