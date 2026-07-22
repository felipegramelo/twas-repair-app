# TWAS REPAIR — Product Requirements

## Original problem statement
The user wants to unify two separate applications (a Timesheet Tracker and a Service/Daily Report app) into a single "TWAS REPAIR" app with role-based auth (Admin/Supervisor), full CRUD for Timesheets & Reports, advanced A4 PDF generation (ReportLab), automated OneDrive sync (via Make.com), and a Projects module (Gantt-style task scheduling) with AI-powered PDF import (Gemini 3 Flash).

## Personas
- **Admin**: Manages Service Orders, Reports, Timesheets, Projects; assigns projects to Supervisors; imports PDFs to auto-populate task hierarchies.
- **Supervisor**: Creates/edits Reports & Timesheets, updates progress % on tasks assigned to them.

## Stack
- Expo Router + React Native Web / iOS / Android
- FastAPI + MongoDB (motor)
- ReportLab / PyMuPDF for PDF
- Make.com webhooks → personal OneDrive
- Emergent LLM key + `emergentintegrations` (Gemini 3 Flash) for PDF task extraction

## Implemented (recent → older)
- **2026-06** — Botão de atualização (iOS/Android APENAS, web excluída a pedido do usuário): `UpdateChecker` reescrito com `expo-updates` (instalado ~29.0.19) — checa OTA update no mount e ao voltar ao foreground; banner "Nova versão disponível — Atualizar" faz `fetchUpdateAsync` + `reloadAsync`. Guard `Updates.isEnabled` (não aparece em Expo Go/dev). REQUER EAS Update configurado no build (`eas update:configure`). Endpoint `GET /api/version` mantido para diagnóstico.
- **2026-06** — BM: modo "Diária Fechada" (`daily_only` no `/bm/calculate`): ignora horas extras e adicional noturno, cobra só diárias — 3º chip no Modo de Cálculo. Botão ✕ em cada item calculado para excluir cobranças que o cliente não paga (subtotal recalcula). Itens de logística agora salvos com `data_inicial`/`data_final` do período do BM e exibidos nas colunas de data do PDF (fallback: período do BM).
- **2026-06** — Boletim UX: ao escolher a OS, tabela de preço E tabela de logística do cliente são pré-selecionadas automaticamente (match normalizado + parcial por nome do cliente; itens de logística já entram no boletim com qtd. 1) — ambas alteráveis. Ao EDITAR um BM, os cálculos salvos são mantidos (removido o recálculo automático em background que sobrescrevia); recálculo agora é só manual pelo botão "Calcular".
- **2026-06** — Boletim: `price_table_id` agora persistido no BM (faltava no modelo `BMCreate` — Pydantic descartava; edição "esquecia" a tabela). Logística no BM: selecionar tabela importa TODOS os trechos de uma vez (qtd. 1), com quantidade editável inline e remoção individual por item (antes era item por item via picker).
- **2026-06** — Boletim de Medição: corrigido bug onde `price_table_id` selecionado no dropdown era ignorado no `/bm/calculate` (agora usa a tabela escolhida, com fallback para o cliente da OS). Adicionados botões rápidos "+ Hotel / + Alimentação / + Consumíveis" no formulário de Tabela de Logística. Corrigido erro 500 (UnicodeEncodeError latin-1) no download de PDFs com caracteres especiais (–) em Reports e Timesheets (RFC 6266).
- **2026-06** — Make.com: cenário "TWAS Reports → OneDrive" reconfigurado com o usuário (API Call por path + Set variable `pastas` com merge/map + Router pasta existe/não existe). Conta OneDrive é MSA pessoal (Search API não funciona). Checklist entregue para replicar em Timesheets.
- **2026-06** — OneDrive folder naming: webhook payload agora inclui campo `folder` no formato "OS - CLIENTE - EMBARCAÇÃO - SERVIÇO" (maiúsculas, ex: "18-2604-33 - CONSTELLATION - AMARALINA STAR - ANÁLISE DE VIBRAÇÃO") via `build_folder_name()` em `services/onedrive.py`. Aplicado a reports, timesheets e projects (projects busca `service` da OS vinculada). Usuário precisa mapear o campo `folder` no cenário Make.com.
- **2026-06** — Progresso inline + rollup automático: % de subtarefas editável direto na lista (input inline, leaf only); fases e projeto recalculam automaticamente via `_rollup_progress` (média ponderada por duração, bottom-up), persistido em `project.progress` e `progress_percent` dos pais. Rollup disparado em: PATCH progress, update/add/delete task, import PDF, reschedule, create. Migração aplicada aos projetos existentes. Seletor de regime removido do modal de criação (padrão 8h; regime editável só em "Editar dados" — projetos importados de PDF não precisam).
- **2026-06** — Work regimes (8h/12h/24h por dia): campo `work_regime` no projeto (padrão 8) e override por fase/tarefa. Horas efetivas descontam almoço (8h→7, 12h→11, 24h→22) na conversão hrs→dias do agendador, com herança fase→sub-tarefas. IA detecta regime do PDF importado. Novo endpoint `POST /api/projects/{id}/reschedule` + botão "Reagendar" no editor. Seletores de regime na criação do projeto, no modal "Editar dados" e no modal de tarefa. Corrigido modal de meta sem fundo (estilos modalCard/btnSecondary ausentes).
- **2026-06** — Fixed auto-scheduling bug (15.5-day project spanning ~56 days): `_schedule_tasks_from_start` now uses fractional-day math (8h=1d); a parent phase's own duration defines its window and children are compressed proportionally inside it (they run in parallel in practice). Phases run sequentially, so total project span = sum of phase durations. Existing projects rescheduled in DB.
- **2026-02-08** — Project PDF redesigned to match MS Project model: bold phase headers with gray background at any depth, bold column headers, day-of-week + date format ("Qua 14/01/26"), timeline date ticks above Gantt bars, and colored Gantt bars (dark for phases, blue for leaves) with progress overlay.
- **2026-02-08** — Fixed "Falha ao baixar PDF" in Projects: (a) `projectAPI.downloadPDF` blob helper added, (b) Content-Disposition now uses RFC 6266 UTF-8 encoding for Unicode titles (em-dash etc.).
- **2026-02-08** — Replaced YYYY-MM-DD text inputs with cross-platform Calendar widgets (`DateField` component: native HTML date input on web, `DateTimePicker` modal on iOS/Android).
- **2026-02-08** — Fixed misleading "Falha ao enviar PDF" error: extended polling to 3 min, swallowed transient GET failures, only shows the error when the initial POST truly fails.
- OneDrive Sync for Reports & Timesheets via Make.com Webhooks.
- Projects Module MVP (parent/child hierarchy, % progress, `shared_with` for supervisor assignment).
- Async AI PDF Import (Gemini 3 Flash → JSON task tree).
- Global Axios 401 interceptor (session expiration).

## Backlog
- **P1** OneDrive sync for Project PDFs (needs `MAKE_WEBHOOK_PROJECTS_URL`).
- **P2** Refactor `supervisor/edit-report.tsx` (>1100 lines) into smaller components.

## Credentials
- Admin: `admin@twasrepair.com` / `admin123`
- Supervisor: `supervisor@twasrepair.com` / `super123`

## Key files
- `/app/frontend/components/DateField.tsx` — cross-platform calendar input
- `/app/frontend/app/admin/edit-project.tsx` — task editor (uses DateField)
- `/app/frontend/app/admin/projects.tsx` — project creation (uses DateField)
- `/app/backend/routes/projects.py` — Project CRUD + AI PDF import
- `/app/backend/services/onedrive.py` — Make.com webhook helper
