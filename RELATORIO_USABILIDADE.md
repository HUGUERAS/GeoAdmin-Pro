# Relatório de Falhas de Usabilidade - GeoAdmin Pro

## 📋 Resumo Executivo

Foram identificadas **27 falhas de usabilidade** distribuídas em 5 categorias críticas que impactam significativamente a experiência do usuário e a eficiência operacional do sistema.

---

## 🔴 CRÍTICAS (Impacto Alto)

### 1. **Magic Link - Fluxo Confuso de Participantes vs Legado**
- **Localização**: `backend/services/magic_link/service.py` (linhas 139-186)
- **Problema**: O sistema alterna silenciosamente entre fluxo de participantes e legado sem feedback claro ao usuário
- **Impacto**: Usuários não entendem por que o comportamento muda entre projetos
- **Solução**: Implementar indicador visual claro do modo ativo e padronizar fluxos

### 2. **Formulário Cliente - Sem Validação em Tempo Real**
- **Localização**: `backend/static/formulario_cliente.html`
- **Problema**: Validação apenas no submit, sem feedback imediato de campos inválidos
- **Impacto**: Usuário preenche tudo e só descobre erros no final, causando frustração
- **Solução**: Adicionar validação on-blur e indicadores visuais de campo válido/inválido

### 3. **Mapa Web - Ferramentas de Edição Pouco Intuitivas**
- **Localização**: `backend/static/geoadmin_web.html` (linhas 1400-1550)
- **Problema**:
  - Ícones de ferramentas sem tooltips explicativos
  - Sem confirmação antes de deletar vértices críticos
  - Histórico de desfazer limitado (50 ações) sem indicador visual
- **Impacto**: Erros acidentais na edição de perímetros
- **Solução**: Adicionar tooltips, confirmações e barra de histórico visual

### 4. **Exportação DWG/DWF - Falta de Feedback de Progresso**
- **Localização**: Integração FreeCAD
- **Problema**: Processos longos de exportação sem barra de progresso ou estimativa
- **Impacto**: Usuário não sabe se o processo travou ou está rodando
- **Solução**: Implementar websocket para progresso em tempo real

### 5. **Navegação Mobile - Menu de Cálculos Sobrecarregado**
- **Localização**: `mobile/app/(tabs)/calculos/`
- **Problema**: 15+ ferramentas de cálculo listadas sem categorização ou busca
- **Impacto**: Dificuldade em encontrar ferramentas específicas em campo
- **Solução**: Agrupar por categoria (distâncias, ângulos, áreas, coordenadas) e adicionar busca

---

## 🟠 ALTAS (Impacto Médio-Alto)

### 6. **Feedback de API Intermitente**
- **Localização**: `geoadmin_web.html` (linhas 606-610)
- **Problema**: Indicador "Verificando API..." sem detalhes do erro quando falha
- **Solução**: Mostrar mensagem específica (timeout, auth, servidor) e botão de retry

### 7. **Busca de Projetos Sem Filtros Avançados**
- **Localização**: `geoadmin_web.html` (linhas 228-248)
- **Problema**: Apenas busca por texto, sem filtros por status, município, data
- **Solução**: Adicionar painel de filtros colapsável

### 8. **Toast Messages Genéricas**
- **Localização**: `geoadmin_web.html` (função `toast`, linha ~1690)
- **Problema**: Mensagens como "Erro ao salvar" sem contexto ou ação corretiva
- **Solução**: Mensagens específicas com sugestão de correção

### 9. **Carregamento de Lista de Projetos Sem Skeleton/Pagination**
- **Localização**: `geoadmin_web.html` (função `carregarProjetos`)
- **Problema**: Tela vazia ou spinner genérico durante carregamento longo
- **Solução**: Skeleton screens e paginação infinita

### 10. **Edição de Vértices Sem Snap/Grade**
- **Localização**: `geoadmin_web.html` (renderEditLayers)
- **Problema**: Difícil alinhar vértices precisamente sem snapping
- **Solução**: Implementar snap a vértices existentes e grade opcional

### 11. **Formulário Cliente - Campos Obrigatórios Não Marcados**
- **Localização**: `formulario_cliente.html`
- **Problema**: Usuário não sabe quais campos são obrigatórios até submeter
- **Solução**: Asterisco vermelho (*) em campos required e hint visual

### 12. **Sem Preview de Croqui Antes de Submeter**
- **Localização**: `formulario_cliente.html`
- **Problema**: Usuário desenha croqui mas não vê como ficará antes de enviar
- **Solução**: Modal de preview com zoom e opção de refazer

### 13. **Progresso do Formulário Não Persiste**
- **Localização**: `formulario_cliente.html`
- **Problema**: Se fechar aba, perde todo progresso
- **Solução**: Auto-save no localStorage e recuperação ao retornar

### 14. **Contrast Ratio Insuficiente**
- **Localização**: CSS global (`--muted: #7a7870` sobre `--bg: #111110`)
- **Problema**: Texto secundário com contraste abaixo de WCAG AA (4.5:1)
- **Solução**: Ajustar cores para mínimo 4.5:1

### 15. **Tooltips Ausentes em Ícones de Ação**
- **Localização**: Múltiplas telas
- **Problema**: Ícones como 📐, 📁, 🗺️ sem descrição textual
- **Solução**: Adicionar `title` attribute e tooltip customizado

---

## 🟡 MÉDIAS (Impacto Moderado)

### 16. **Ordenação de Listas Fixa**
- **Problema**: Projetos sempre ordenados por data, sem opção de ordenar por nome/status
- **Solução**: Cabeçalhos de coluna clicáveis para ordenação

### 17. **Sem Atalhos de Teclado**
- **Problema**: Usuários avançados não têm atalhos (Ctrl+S, Ctrl+Z, Delete)
- **Solução**: Implementar keyboard shortcuts com modal de ajuda (tecla ?)

### 18. **Scroll Horizontal em Tabelas Mobile**
- **Problema**: Tabelas quebram layout em telas pequenas
- **Solução**: Cards responsivos ou scroll horizontal com indicador

### 19. **Confirmação de Exclusão Genérica**
- **Problema**: "Tem certeza?" sem mostrar o que será excluído
- **Solução**: Modal com detalhes do item e consequência da ação

### 20. **Estado Vazio Sem Call-to-Action**
- **Localização**: `geoadmin_web.html` (classe `.empty`)
- **Problema**: Telas vazias apenas dizem "Nenhum projeto" sem botão de criar
- **Solução**: Adicionar botão primário de ação no estado vazio

### 21. **Zoom do Mapa Não Persiste**
- **Problema**: Ao recarregar, mapa volta ao zoom default
- **Solução**: Salvar zoom/center no localStorage ou URL params

### 22. **Mensagens de Erro Técnicas**
- **Problema**: Erros como "HTTP 422" ou "duplicate key value" expostos ao usuário
- **Solução**: Traduzir para linguagem do domínio ("Já existe cliente com este CPF")

### 23. **Loading Bloqueante**
- **Problema**: Spinner central bloqueia toda interação durante requests
- **Solução**: Loading não-bloqueante por componente (botão, tabela)

---

## 🟢 BAIXAS (Melhorias Incrementais)

### 24. **Paleta de Cores Muito Escura**
- **Problema**: Modo dark extremo pode cansar vista em ambientes claros
- **Solução**: Oferecer tema claro/escuro toggle

### 25. **Fontes Monoespaçadas em Dados Numéricos**
- **Problema**: Bom para alinhamento, mas reduz legibilidade para alguns usuários
- **Solução**: Testar com usuários e oferecer alternativa

### 26. **Animações Excessivamente Rápidas**
- **Localização**: CSS (`transition: all .15s`)
- **Problema**: Pode ser difícil para usuários com dificuldades cognitivas
- **Solução**: Respeitar `prefers-reduced-motion` e aumentar para 250-300ms

### 27. **Sem Indicador de Offline**
- **Problema**: Usuário mobile não sabe quando está offline
- **Solução**: Banner discreto quando conexão cair + fila de ações pendentes

---

## 📊 Matriz de Priorização

| ID | Falha | Impacto | Esforço | Prioridade |
|----|-------|---------|---------|------------|
| 1 | Fluxo Magic Link confuso | Alto | Médio | 🔴 P0 |
| 2 | Validação formulário | Alto | Baixo | 🔴 P0 |
| 3 | Edição de mapa | Alto | Médio | 🔴 P0 |
| 4 | Feedback exportação | Alto | Alto | 🟠 P1 |
| 5 | Menu cálculos mobile | Alto | Baixo | 🔴 P0 |
| 6 | Feedback API | Médio | Baixo | 🟠 P1 |
| 7 | Filtros projetos | Médio | Médio | 🟠 P1 |
| 11 | Campos obrigatórios | Alto | Baixo | 🔴 P0 |
| 13 | Persistência formulário | Médio | Médio | 🟠 P1 |
| 14 | Contraste | Alto | Baixo | 🔴 P0 |

---

## 🎯 Plano de Ação Recomendado

### Sprint 1 (Crítico - 1 semana)
- [ ] Corrigir contraste de cores (#14)
- [ ] Marcar campos obrigatórios no formulário (#11)
- [ ] Adicionar validação em tempo real (#2)
- [ ] Simplificar menu de cálculos mobile (#5)
- [ ] Melhorar mensagens de erro do Magic Link (#1)

### Sprint 2 (Alta Prioridade - 2 semanas)
- [ ] Implementar tooltips em ícones (#15)
- [ ] Adicionar filtros de projetos (#7)
- [ ] Persistir progresso do formulário (#13)
- [ ] Melhorar feedback da API (#6)
- [ ] Adicionar snapping na edição de mapa (#10)

### Sprint 3 (Média Prioridade - 2 semanas)
- [ ] Barra de progresso em exportações (#4)
- [ ] Atalhos de teclado (#17)
- [ ] Estado vazio com CTA (#20)
- [ ] Preview de croqui (#12)
- [ ] Ordenação de listas (#16)

---

## 🧪 Métricas de Sucesso

Após implementação:
- Reduzir taxa de abandono do formulário em 40%
- Diminuir tickets de suporte sobre "como usar" em 50%
- Aumentar NPS de usabilidade de X para Y
- Reduzir tempo médio para completar tarefas críticas em 30%

---

## 📝 Notas Adicionais

### Padrões de Design Violados
1. **Princípio de Menor Surpresa**: Comportamento inconsistente entre fluxos
2. **Feedback Imediato**: Atraso entre ação e resposta do sistema
3. **Prevenção de Erros**: Falta de confirmações e validações preventivas
4. **Acessibilidade**: Contraste e navegação por teclado insuficientes

### Recomendações Gerais
- Implementar design system com componentes reutilizáveis
- Criar testes de usabilidade com usuários reais (topógrafos, advogados)
- Adicionar analytics para identificar pontos de atrito
- Documentar padrões de UX para consistência futura

---

*Relatório gerado em: {{data_atual}}*
*Versão do código analisada: commit mais recente*
