# TWAS REPAIR - PRD (Product Requirements Document)

## Problema Original
Unificar dois apps (Timesheet Tracker e Service/Daily Report) em um único app "TWAS REPAIR" com autenticação role-based (Admin/Supervisor), CRUD completo, geração avançada de PDF A4, e funcionalidade cross-platform (React Native Web + iOS).

## Stack Técnica
- Frontend: React Native (Expo SDK 54, Expo Router), TypeScript
- Backend: FastAPI, MongoDB (motor)
- PDF: ReportLab + PyMuPDF (fitz)
- Módulos Nativos: expo-sharing, expo-file-system/legacy, expo-image-picker, expo-document-picker
- Storage: Emergent Object Storage

## IMPORTANTE - Expo SDK 54
- `expo-file-system`: Usar import de `expo-file-system/legacy` (a API padrão depreciou downloadAsync)
- NÃO usar APIs web-only (window.alert, document.createElement) sem Platform.OS check
- Modais aninhados não funcionam no iOS nativo - usar renderização inline

## Funcionalidades Implementadas
- [x] Autenticação (Admin/Supervisor) com JWT
- [x] CRUD Timesheets (criar/editar/excluir, PDF)
- [x] CRUD Relatórios (serviço e diário, PDF)
- [x] Ordens de Serviço (CRUD + Arquivo por O.S.)
- [x] Boletim de Medição
- [x] Dashboard Financeiro
- [x] Propostas Comerciais (seções/subseções, fotos, termos gerais, campo serviço)
- [x] Propostas Técnicas (PDF)
- [x] iOS Native: Touch interactions (GestureHandlerRootView)
- [x] iOS Native: File pickers (expo-image-picker, expo-document-picker)
- [x] iOS Native: PDF download/sharing (expo-file-system/legacy + expo-sharing)
- [x] iOS Native: Alert.alert em vez de window.alert
- [x] iOS Native: Inline pickers no Timesheet (sem modais aninhados)
- [x] iOS Native: Modal OS picker no Create Report
- [x] iOS Native: Fix expo-file-system deprecated API (usar /legacy)

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

## Arquitetura
```
/app
├── backend/
│   ├── .env
│   ├── server.py
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── _layout.tsx
│   │   ├── admin/ (propostas, timesheets, reports, etc.)
│   │   └── supervisor/ (create/edit timesheet, create/edit report)
│   ├── utils/pdfHelper.ts (expo-file-system/legacy)
│   ├── services/api.ts
│   ├── contexts/AuthContext.tsx (token key: 'token')
│   └── types/index.ts
└── memory/PRD.md
```
