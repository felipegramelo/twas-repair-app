# TWAS REPAIR - PRD (Product Requirements Document)

## Problema Original
Unificar dois apps (Timesheet Tracker e Service/Daily Report) em um unico app "TWAS REPAIR" com autenticacao role-based (Admin/Supervisor), CRUD completo, geracao avancada de PDF A4, e funcionalidade cross-platform (React Native Web + iOS + Android).

## Stack Tecnica
- Frontend: React Native (Expo SDK 54, Expo Router), TypeScript
- Backend: FastAPI, MongoDB (motor) - Estrutura Modular com indices criados no startup
- PDF: ReportLab + PyMuPDF (fitz)
- Storage: Emergent Object Storage
- Deploy: Backend no Railway (Dockerfile), Frontend iOS/Android via EAS

## Arquitetura Backend (Refatorado)
```
backend/
  server.py          (app init + router includes + indices no startup)
  database.py, config.py, dependencies.py, models.py
  routes/ (auth, employees, service_orders, timesheets, reports, proposals, boletim, dashboard, sharing, translate)
```

## Funcionalidades Implementadas
- [x] Autenticacao (Admin/Supervisor) com JWT
- [x] CRUD Timesheets + PDF + Numero sequencial por OS (admin)
- [x] CRUD Relatorios (servico e diario) + PDF + Fotos
- [x] Ordens de Servico CRUD + PDF (10-FR-01-06) gerado automaticamente
- [x] Boletim de Medicao + Dashboard Financeiro
- [x] Propostas Comerciais (campo local, auto-preenchimento OS)
- [x] iOS/Android: PDFs, Fotos, Alerts, Sharing - tudo nativo
- [x] Compartilhamento de Documentos + Troca de Senha
- [x] Tema Preto (#000000)
- [x] Marcadores toggle por linha nos relatorios
- [x] Confirmacao "Enviar para administrador" com tipo do documento
- [x] Backend refatorado (monolito -> modular)
- [x] Object Storage atualizado (novos endpoints /init, /objects/)
- [x] Traducao automatica (EN/ES) via Gemini
- [x] PDF OS atualizado (2026-04-21):
    - Contatos reais: Daniel Gussen (Comercial), Felipe Melo (Tecnico), Jorge Campos (Logistica)
    - Secao EQUIPE mostra apenas quantidade por funcao (nomes completos: Tecnico, Mecanico, etc)
    - Previsao de inicio / Previsao de termino (era "P. de inicio / P. de termino")
    - Linha "Horario de trabalho" com valor 06h-18h ou 07h-19h
- [x] Campo schedule_type (06-18 / 07-19) na UI de OS (2026-04-21)
- [x] Otimizacao N+1 em /admin/os-archive: 3 queries totais (batch com $in) ao inves de 1+2N (2026-04-21)
- [x] Indices MongoDB criados no startup: timesheets.os_id, reports.os_id, reports.(os_id,status), service_orders.os_number
- [x] URL Production hardcoded em frontend/services/config.ts (2026-04-25)
    - Evita que builds Android via Emergent ("Re-deploy and generate build") apontem para o banco preview
    - Todas as 22 ocorrencias de `process.env.EXPO_PUBLIC_BACKEND_URL` substituidas por `BACKEND_URL` de `services/config.ts`
    - Override opcional via EXPO_PUBLIC_BACKEND_URL_OVERRIDE para testes
    - Arquivos atualizados: AuthContext.tsx, api.ts, services/config.ts, admin/(service-orders, boletim-medicao, daily-reports, timesheets, propostas, service-reports, os-archive), supervisor/(index, edit-report)
    - Bug pre-existente corrigido: codigo orfao no fim de service-orders.tsx (linhas 480-485)

## Versao Atual: 1.0.22 (proxima build Android)

## Boletim de Medição - Refatoração Completa (2026-04-28)
- **Tela: `app/admin/boletim-medicao.tsx`**
- Toggle "Por Diária / Por Hora" SUBSTITUÍDO por "Onshore (8h) / Offshore (12h)"
- Onshore: base 8h, hour_rate = day_rate / 7 (desconta 1h almoço)
- Offshore: base 12h, hour_rate = day_rate / 11 (desconta 1h almoço)
- **Horas extras com multiplicadores:** Seg-Sex +70%, Sábado +80%, Dom/Feriado +100%
- **Horas de viagem** somam à diária; excedente vira hora extra
- **Saída: linhas separadas** por tipo (Diárias / Extras Seg-Sex / Extras Sábado / Extras Dom-Feriado)
- **Vírgula em valores quebrados** funcionando: tabela aceita "2.850,72" e formata em pt-BR
- **Nova aba "Feriados"**:
  - Feriados nacionais brasileiros calculados automaticamente (`backend/holidays_util.py`)
    - Fixos: 01/01, 21/04, 01/05, 07/09, 12/10, 02/11, 15/11, 25/12
    - Móveis baseados na Páscoa: Carnaval, Sexta-Santa, Corpus Christi
  - CRUD de feriados regionais (`/api/holidays`)
- Novos arquivos: `backend/holidays_util.py`, `backend/routes/holidays.py`

## Deploy Web (Vercel) - Configurado em 2026-04-28
- vercel.json + .vercelignore criados na raiz
- Build command: `cd frontend && yarn install --frozen-lockfile && npx expo export --platform web`
- Output dir: `frontend/dist`
- SPA rewrites configurados (todas rotas -> index.html)
- Build local validado: 22 rotas estaticas, 7.5MB, login funcionando contra Railway

## Credenciais de Teste
- Admin: admin@twasrepair.com / admin123
- Supervisor: supervisor@twasrepair.com / super123

## Tradução de Propostas (2026-05-18)
**Botão "Traduzir" na lista de Propostas** (admin), ícone de idioma azul ao lado de Editar/Excluir:
- Abre modal com 2 opções: 🇺🇸 Inglês / 🇪🇸 Espanhol
- Cria uma **cópia** da proposta original com todo o conteúdo traduzido via Gemini Nano Banana (Emergent LLM Key)
- Numeração da cópia traduzida ganha sufixo `-EN` ou `-ES` (ex: `P-0011-EN`)
- Campos traduzidos: serviço, descrição de itens, subseções, termos gerais, observações
- **Tabela de Preços e Tabela de Logística são preservadas** na cópia (valores não traduzem)
- PDFs Comercial e Técnico ficam disponíveis nos dois idiomas
- Arquivos tocados: `backend/routes/translate.py`, `backend/routes/proposals.py`, `frontend/app/admin/propostas.tsx`

## Modo Offline para Supervisor (2026-05-12)
**Supervisor agora pode trabalhar offline** (timesheet, relatório diário, relatório de serviço):

- Detecção automática de conexão via `@react-native-community/netinfo`
- Banner colorido no topo do dashboard do supervisor:
  - Vermelho "Você está offline" (sem conexão)
  - Laranja "X item(ns) aguardando sincronização" (online, com pendentes) + botão "Sincronizar"
- Quando offline, criar timesheet/relatório salva o documento na fila local (`AsyncStorage` chave `offline_queue_v1`)
- Drafts offline aparecem no dashboard com borda laranja + badge "Pendente sincronização"
- Quando a conexão volta, a fila é processada automaticamente (com retry e log de erro por item)
- Após sincronização bem-sucedida, o item sai da fila e a versão online (`status: draft`) substitui o item local
- Documentos sincronizados ficam como **draft** — o supervisor revisa e finaliza manualmente

**Arquivos criados:**
- `frontend/services/offlineQueue.ts` — fila + persistência + sincronização
- `frontend/contexts/OfflineContext.tsx` — estado global de online/pendentes
- `frontend/components/OfflineBanner.tsx` — banner visual

**Arquivos modificados:**
- `frontend/app/_layout.tsx` — wrap com `OfflineProvider`
- `frontend/app/supervisor/index.tsx` — banner + drafts offline mesclados na lista
- `frontend/app/supervisor/create-timesheet.tsx` — usa fila quando offline
- `frontend/app/supervisor/create-report.tsx` — usa fila quando offline

## Backlog (P1/P2)
- [P2] Refatorar frontend/app/supervisor/edit-report.tsx (>1000 linhas) em componentes menores

## Tabela de Logística Opcional na Proposta (2026-05-12)
**Checkbox "Incluir tabela de logística"** no formulário da Proposta:
- Layout fixo: Descrição + Valor/Colaborador + Qtd + Total (auto-calculado)
- Botão "Importar tabela existente" busca tabelas de logística do BM (por cliente)
- Botão "Adicionar trecho" para digitar manualmente
- Cada trecho editável e removível individualmente
- Persistência: campos `show_logistics_table`, `logistics_rows` no documento da proposta
- PDF: nova seção "TABELA DE LOGÍSTICA" com rodapé "TOTAL LOGÍSTICA"
- Pode ser combinado com a tabela de preços (ambos aparecem se marcados)
- Arquivos tocados: `backend/routes/proposals.py`, `frontend/app/admin/propostas.tsx`, `frontend/types/index.ts`

## Tabela de Preços Opcional na Proposta (2026-05-12)
**Checkbox "Incluir tabela de preços"** no formulário da Proposta:
- Quando marcada, o admin pode escolher um dos dois formatos:
  - **rates**: Função/Cargo + Day Rate + Night Rate (igual à tabela de preços do BM)
  - **custom**: Descrição + Unidade + Quantidade + Valor Unitário + Total (auto-calculado)
- Botão "Importar tabela existente" permite trazer linhas de uma tabela já cadastrada em BM (apenas formato rates)
- Botão "Adicionar linha" para digitar manualmente
- Cada linha pode ser editada ou removida
- Persistência: campos `show_price_table`, `price_table_layout`, `price_table_rows` no documento da proposta
- PDF da proposta: nova seção "TABELA DE PREÇOS" aparece após o "VALOR TOTAL" e antes dos Termos, apenas quando o checkbox estiver marcado
- Layout custom no PDF exibe linha extra "TOTAL TABELA" com a soma dos totais
- Arquivos tocados: `backend/routes/proposals.py`, `frontend/app/admin/propostas.tsx`, `frontend/types/index.ts`

## Logistica no Boletim de Medicao (2026-05-07)
**Nova aba "Logistica"** ao lado de Tabela de Precos e Feriados:
- CRUD por cliente de tabelas de logistica (cada tabela tem varios trechos com descricao + valor por colaborador)
- Endpoints backend: `GET/POST/PUT/DELETE /api/logistics-prices` (`backend/routes/boletim.py`)
- Persistencia: colecao `logistics_prices` no MongoDB
- Botao "Duplicar" disponivel por tabela

**Integracao no formulario de BM:**
- Secao "Logistica" aparece apos os Itens Calculados
- Botao "Adicionar" abre modal que permite selecionar tabela -> trecho -> quantidade de colaboradores
- Total por trecho = valor_por_colaborador x quantidade
- Multiplos trechos podem ser adicionados (ex: mobilizacao + desmobilizacao)
- Itens de logistica ficam persistidos no BM (campo `logistics_items`) e reaparecem ao editar
- Subtotal e Valor Total recalculam automaticamente incluindo logistica

**PDF do Boletim:**
- Trechos de logistica aparecem como linhas adicionais no final da tabela principal (antes de Subtotal)
- Formato: `[descricao] | Evento | valor_und | qtd | total`
- Subtotal, Impostos e Valor Total continuam no rodape mostrando o acumulado final
