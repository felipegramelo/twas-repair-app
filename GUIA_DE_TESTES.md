# 🧪 Guia Completo de Testes - App Timesheet TWAS REPAIR

## 📋 Pré-requisitos

- Acesso à URL: https://report-pdf-engine.preview.emergentagent.com
- Credenciais fornecidas abaixo

## 🔐 Credenciais de Teste

### Administrador
- **Email:** admin@twasrepair.com
- **Senha:** admin123

### Supervisor
- **Email:** supervisor@twasrepair.com  
- **Senha:** super123

---

## ✅ TESTE 1: Login e Autenticação

### 1.1 Testar Login de Administrador
1. Acesse: https://report-pdf-engine.preview.emergentagent.com
2. Preencha:
   - Email: `admin@twasrepair.com`
   - Senha: `admin123`
3. Clique em "Entrar"
4. **Resultado esperado:** Redirecionamento para o Painel Administrativo

### 1.2 Testar Login de Supervisor
1. Faça logout (ícone vermelho no canto superior direito)
2. Preencha:
   - Email: `supervisor@twasrepair.com`
   - Senha: `super123`
3. Clique em "Entrar"
4. **Resultado esperado:** Redirecionamento para o Dashboard do Supervisor

### 1.3 Testar Login Inválido
1. Faça logout
2. Tente logar com senha incorreta
3. **Resultado esperado:** Mensagem de erro "Incorrect email or password"

---

## 👥 TESTE 2: Gerenciamento de Funcionários (Admin)

### 2.1 Visualizar Funcionários
1. Login como admin
2. Clique no card "Funcionários"
3. **Resultado esperado:** 
   - Lista com 3 funcionários pré-cadastrados
   - Carlos Mendes (E), Pedro Santos (T), José Oliveira (M)

### 2.2 Adicionar Novo Funcionário
1. Clique no botão "+" (azul, canto superior direito)
2. Preencha:
   - Nome: `Maria Silva`
   - Função: Selecione `W - Soldador`
3. Clique em "Salvar"
4. **Resultado esperado:** Modal fecha e nova funcionária aparece na lista

### 2.3 Editar Funcionário
1. Clique no ícone de lápis (editar) de Maria Silva
2. Altere a função para `SE - Especialista`
3. Clique em "Salvar"
4. **Resultado esperado:** Dados atualizados na lista

### 2.4 Excluir Funcionário
1. Clique no ícone de lixeira (excluir) de Maria Silva
2. Confirme a exclusão
3. **Resultado esperado:** Funcionária removida da lista

---

## 📄 TESTE 3: Gerenciamento de Ordens de Serviço (Admin)

### 3.1 Visualizar Ordens de Serviço
1. Volte ao dashboard (seta voltar)
2. Clique no card "Ordens de Serviço"
3. **Resultado esperado:** 
   - 2 O.S. pré-cadastradas
   - OS-2025-001 (Petrobrás) e OS-2025-002 (Vale S.A.)

### 3.2 Adicionar Nova O.S.
1. Clique no botão "+" 
2. Preencha:
   - Número da O.S.: `OS-2025-003`
   - Cliente: `Petrobras Distribuidora`
   - Local: `Rio de Janeiro - RJ`
   - Serviço: `Inspeção e manutenção de tanques de armazenamento`
3. Clique em "Salvar"
4. **Resultado esperado:** Nova O.S. aparece na lista

### 3.3 Editar O.S.
1. Clique no ícone de editar da OS-2025-003
2. Altere o local para `Duque de Caxias - RJ`
3. Clique em "Salvar"
4. **Resultado esperado:** Local atualizado na lista

### 3.4 Excluir O.S.
1. Clique no ícone de excluir da OS-2025-003
2. Confirme
3. **Resultado esperado:** O.S. removida

---

## ⏱️ TESTE 4: Criação de Timesheet (Supervisor)

### 4.1 Acessar Criação de Timesheet
1. Faça logout e login como supervisor
2. Clique em "Criar Novo Timesheet"
3. **Resultado esperado:** Tela de criação carregada

### 4.2 Selecionar Ordem de Serviço
1. Clique em "Selecionar O.S."
2. Escolha "OS-2025-001 - Petrobrás"
3. **Resultado esperado:** O.S. selecionada aparece no campo

### 4.3 Adicionar Primeira Entrada
1. Clique em "Adicionar" (ao lado de Entradas)
2. Preencha:
   - Data: `25/02/2026`
   - Funcionário: Clique e selecione `Carlos Mendes (E)`
   - Serviço - Início: `08:00`
   - Serviço - Fim: `17:00`
   - Viagem - Início: `07:00`
   - Viagem - Fim: `18:00`
3. Clique em "Adicionar"
4. **Resultado esperado:** Entrada aparece na lista com badge "E"

### 4.4 Adicionar Segunda Entrada (Mesmo Dia)
1. Clique em "Adicionar" novamente
2. Preencha:
   - Data: `25/02/2026`
   - Funcionário: `Pedro Santos (T)`
   - Serviço - Início: `08:30`
   - Serviço - Fim: `16:30`
   - (Deixe viagem em branco)
3. Clique em "Adicionar"
4. **Resultado esperado:** Segunda entrada adicionada

### 4.5 Adicionar Terceira Entrada (Outro Dia)
1. Adicione mais uma entrada:
   - Data: `26/02/2026`
   - Funcionário: `José Oliveira (M)`
   - Serviço - Início: `09:00`
   - Serviço - Fim: `18:00`
   - Viagem - Início: `08:00`
   - Viagem - Fim: `19:00`
3. **Resultado esperado:** 3 entradas visíveis

### 4.6 Adicionar Observações
1. Role para baixo até "Observações"
2. Digite:
   ```
   Trabalho realizado conforme cronograma.
   Equipamentos verificados e em perfeito estado.
   Próxima visita agendada para 01/03/2026.
   ```
3. **Resultado esperado:** Texto aparece no campo

### 4.7 Salvar Timesheet
1. Clique em "Salvar Timesheet"
2. Aguarde mensagem de sucesso
3. **Resultado esperado:** 
   - Mensagem "Timesheet criado com sucesso"
   - Redirecionamento para o dashboard

---

## 📥 TESTE 5: Visualização e Download de PDF

### 5.1 Visualizar Timesheet Criado
1. No dashboard do supervisor
2. **Resultado esperado:** Timesheet OS-2025-001 aparece na lista

### 5.2 Baixar PDF
1. Clique no card do timesheet (ou no ícone de download)
2. Aguarde a geração
3. **Resultado esperado:** 
   - Mensagem "Gerando PDF..."
   - PDF baixado/aberto com:
     - Logo TWAS REPAIR (se disponível)
     - Informações da O.S.
     - Tabela com as 3 entradas
     - Horários de serviço e viagem
     - Observações
     - Legenda de funções
     - Espaço para aprovação do cliente

---

## 👨‍💼 TESTE 6: Visualização Admin de Todos os Timesheets

### 6.1 Acessar como Admin
1. Logout e login como admin
2. Clique em "Timesheets"
3. **Resultado esperado:** 
   - Lista com TODOS os timesheets criados
   - Mostra supervisor responsável

### 6.2 Baixar PDF como Admin
1. Clique em um timesheet
2. **Resultado esperado:** PDF baixado com sucesso

---

## 🔄 TESTE 7: Edição de Timesheet

### 7.1 Editar Entrada
1. Login como supervisor
2. Clique em "Criar Novo Timesheet"
3. Adicione uma entrada de teste
4. Clique no ícone de lápis na entrada
5. Altere o horário
6. Clique em "Atualizar"
7. **Resultado esperado:** Entrada atualizada

### 7.2 Excluir Entrada
1. Clique no ícone de lixeira em uma entrada
2. Confirme
3. **Resultado esperado:** Entrada removida

---

## 📱 TESTE 8: Responsividade Mobile (Se testar no celular)

### 8.1 Testar em Diferentes Resoluções
1. Abra em celular ou redimensione o navegador
2. Teste todas as telas
3. **Verificar:**
   - ✅ Textos legíveis
   - ✅ Botões clicáveis (mínimo 44px)
   - ✅ Inputs funcionando com teclado mobile
   - ✅ Modais ocupando tela apropriadamente
   - ✅ Scroll funcionando em listas longas

---

## 🔐 TESTE 9: Segurança e Permissões

### 9.1 Verificar Restrições do Supervisor
1. Login como supervisor
2. Tente acessar diretamente (não há botão, mas teste via URL):
   - `/admin/employees`
   - `/admin/service-orders`
3. **Resultado esperado:** Sem acesso ou redirecionamento

### 9.2 Verificar Logout
1. Clique no ícone de logout
2. Tente voltar usando o botão "voltar" do navegador
3. **Resultado esperado:** Redirecionamento para tela de login

---

## 📊 TESTE 10: Performance e Usabilidade

### 10.1 Tempo de Carregamento
- ✅ Login: < 2 segundos
- ✅ Carregar lista de funcionários: < 1 segundo
- ✅ Criar timesheet: < 2 segundos
- ✅ Gerar PDF: < 3 segundos

### 10.2 Feedback Visual
- ✅ Loading indicators aparecem durante operações
- ✅ Mensagens de sucesso/erro são claras
- ✅ Botões desabilitados durante processamento

---

## ✅ Checklist Final

Use este checklist para garantir que testou tudo:

- [ ] Login de administrador funciona
- [ ] Login de supervisor funciona
- [ ] Adicionar funcionário funciona
- [ ] Editar funcionário funciona
- [ ] Excluir funcionário funciona
- [ ] Adicionar O.S. funciona
- [ ] Editar O.S. funciona
- [ ] Excluir O.S. funciona
- [ ] Criar timesheet com múltiplas entradas funciona
- [ ] Adicionar entrada de timesheet funciona
- [ ] Editar entrada de timesheet funciona
- [ ] Excluir entrada de timesheet funciona
- [ ] Observações aparecem no PDF
- [ ] PDF é gerado corretamente
- [ ] PDF contém logo da empresa
- [ ] PDF contém todas as informações
- [ ] Admin visualiza todos os timesheets
- [ ] Supervisor visualiza apenas seus timesheets
- [ ] Logout funciona
- [ ] Interface é responsiva
- [ ] Mensagens de erro são claras

---

## 🐛 Reportar Problemas

Se encontrar algum problema durante os testes, anote:
1. O que você estava fazendo
2. O que esperava que acontecesse
3. O que realmente aconteceu
4. Prints de tela (se possível)
5. Mensagens de erro (se houver)

---

## 📞 Suporte

Para dúvidas ou problemas:
- Verifique o arquivo `/app/README_APP.md`
- Consulte os logs do backend: `tail -f /var/log/supervisor/backend.out.log`
- Consulte os logs do frontend: `tail -f /var/log/supervisor/expo.out.log`
