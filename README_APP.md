# App de Timesheet TWAS REPAIR

## 📱 Sobre o App

Aplicativo mobile/web para gerenciamento de timesheets corporativos da TWAS REPAIR. Permite que supervisores registrem horas trabalhadas de suas equipes e gerem PDFs para impressão.

## 🔐 Credenciais de Acesso

### Administrador
- **Email:** admin@twasrepair.com
- **Senha:** admin123
- **Permissões:** Gerenciar funcionários, ordens de serviço e visualizar todos os timesheets

### Supervisor
- **Email:** supervisor@twasrepair.com
- **Senha:** super123
- **Permissões:** Criar e gerenciar timesheets da sua equipe

## 🎯 Funcionalidades

### Para Administradores:

1. **Gerenciar Funcionários**
   - Cadastrar novos funcionários
   - Editar informações de funcionários
   - Excluir funcionários
   - Funções disponíveis:
     - E - Engenheiro / Engineer
     - SE - Especialista / Specialist
     - T - Técnico / Technician
     - M - Mecânico / Mechanic
     - W - Soldador / Welder
     - TK - Almoxarife / Tool Keeper

2. **Gerenciar Ordens de Serviço**
   - Cadastrar novas O.S. com:
     - Número da O.S.
     - Cliente
     - Local
     - Serviço
   - Editar e excluir O.S.

3. **Visualizar Timesheets**
   - Ver todos os timesheets criados por supervisores
   - Baixar/Imprimir PDFs

### Para Supervisores:

1. **Criar Timesheet**
   - Selecionar Ordem de Serviço
   - Adicionar múltiplas entradas de funcionários
   - Para cada entrada:
     - Data (DD/MM/YYYY)
     - Funcionário (seleção da lista)
     - Horário de início e fim do serviço
     - Horário de início e fim da viagem (opcional)
   - Adicionar observações

2. **Visualizar Timesheets**
   - Ver lista de timesheets criados
   - Baixar/Imprimir PDFs

## 📄 Geração de PDF

O PDF é gerado automaticamente com:
- Logo da empresa TWAS REPAIR
- Informações da O.S. (cliente, local, serviço)
- Tabela com todas as entradas de funcionários
- Legenda das funções
- Observações
- Espaço para aprovação do cliente

## 🚀 Como Usar

### Fluxo Completo:

1. **Admin:** Fazer login como administrador
2. **Admin:** Cadastrar funcionários na tela "Funcionários"
3. **Admin:** Cadastrar ordens de serviço na tela "Ordens de Serviço"
4. **Supervisor:** Fazer login como supervisor
5. **Supervisor:** Clicar em "Criar Novo Timesheet"
6. **Supervisor:** Selecionar uma O.S.
7. **Supervisor:** Adicionar entradas de funcionários com horários
8. **Supervisor:** Salvar o timesheet
9. **Supervisor/Admin:** Visualizar e baixar o PDF para impressão

## 📊 Dados de Teste

### Funcionários Pré-cadastrados:
- Carlos Mendes (Engenheiro - E)
- Pedro Santos (Técnico - T)
- José Oliveira (Mecânico - M)

### Ordens de Serviço Pré-cadastradas:
- OS-2025-001 - Petrobrás - Macaé - RJ
- OS-2025-002 - Vale S.A. - Belo Horizonte - MG

## 🔧 Tecnologias Utilizadas

### Backend:
- FastAPI
- MongoDB
- JWT Authentication
- ReportLab (Geração de PDF)

### Frontend:
- React Native / Expo
- Expo Router (Navegação)
- Axios (API calls)
- AsyncStorage (Token storage)

## 🌐 URLs

- **Frontend:** https://report-pdf-engine.preview.emergentagent.com
- **Backend API:** https://report-pdf-engine.preview.emergentagent.com/api

## 📱 Acesso Mobile

Para testar no celular via Expo Go:
1. Instale o app Expo Go na sua App Store/Play Store
2. Escaneie o QR code gerado pelo Expo
3. Use as credenciais fornecidas acima

## 🎨 Design

- Interface mobile-first
- Design clean e profissional
- Cores da marca TWAS REPAIR (azul #1a237e)
- Ícones intuitivos
- Feedback visual em todas as ações
