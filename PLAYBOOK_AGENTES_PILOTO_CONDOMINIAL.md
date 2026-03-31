# Playbook de Agentes — Piloto Condominial 120 Lotes

**Base:**
- [PLANO_PILOTO_CONDOMINIAL_120_LOTES.md](C:/Users/User/OneDrive/Documentos/GeoAdmin-Pro/PLANO_PILOTO_CONDOMINIAL_120_LOTES.md)
- [BACKLOG_PILOTO_CONDOMINIAL.md](C:/Users/User/OneDrive/Documentos/GeoAdmin-Pro/BACKLOG_PILOTO_CONDOMINIAL.md)

**Objetivo:** deixar prontos os prompts, a ordem e a forma de trabalho dos 2 agentes principais para todas as sprints do piloto.

---

## 1. Os dois agentes fixos

## Agente A — Estrutura Condominial

**Foco:**
- migrations
- Supabase
- FastAPI
- regras de negócio
- isolamento por lote/participante
- contratos de dados

**Skills ideais:**
- `build-web-apps:supabase-postgres-best-practices`
- `security-best-practices`
- `github:gh-fix-ci`
- `github:gh-address-comments`

**Escopo padrão de escrita:**
- `infra/supabase/migrations/*`
- `backend/integracoes/*`
- `backend/routes/*`
- testes de backend

---

## Agente B — Operação por Lote

**Foco:**
- UX operacional
- painel por lote
- fluxo de projeto
- consumo da API
- validação visual e funcional

**Skills ideais:**
- `build-web-apps:frontend-skill`
- `build-web-apps:react-best-practices`
- `playwright`
- `vercel:verification`
- `test-android-apps:android-emulator-qa`

**Escopo padrão de escrita:**
- `mobile/app/*`
- `mobile/components/*`
- `mobile/lib/*` quando necessário para integração
- testes/validação de fluxo

---

## 2. Regra de operação entre agentes

1. O Agente A define schema, regras e shape da resposta.
2. O Agente B consome esse shape e monta a operação visual.
3. Os dois não devem editar o mesmo arquivo na mesma rodada.
4. O integrador final revisa contratos, conflitos e regressões.

---

## 3. Sprint 0 — Higiene e base de lançamento

### Ordem recomendada
- esta sprint deve ser feita centralmente, sem muita paralelização
- usar agentes só se houver subtarefas muito isoladas

### Agente A — Prompt
```text
Você é o Agente Estrutura Condominial do GeoAdmin Pro.

Objetivo da Sprint 0:
1. limpar a base local do repositório
2. remover artefatos locais rastreados por engano
3. reforçar ignores e higiene do backend
4. preparar a linha atual para merge e deploy seguro

Escopo:
- .gitignore
- backend/.gitignore
- docs de deploy e ambiente
- quaisquer ajustes mínimos de backend ligados ao lançamento

Regras:
- não reescrever histórico sem necessidade
- não remover arquivos úteis de documentação
- não mexer em lógica funcional do produto, só em higiene e base de lançamento

Entrega final:
- lista do que foi limpo
- arquivos rastreados removidos do git
- checklist mínimo de deploy
```

### Agente B — Prompt
```text
Você é o Agente Operação por Lote do GeoAdmin Pro.

Objetivo da Sprint 0:
1. verificar a experiência atual de lançamento e teste
2. apontar o que ainda trava uso operacional no app
3. preparar checklist de smoke test funcional

Escopo:
- rotas principais do app
- projeto, clientes, formulário e mapa
- documentação operacional de teste

Regras:
- não redesenhar telas nesta sprint
- foco total em validação e checklist de uso

Entrega final:
- checklist de smoke test
- riscos operacionais observados
- pontos críticos para homologação
```

---

## 4. Sprint 1 — Estrutura de dados do condomínio

### Ordem recomendada
1. Agente A
2. revisão do contrato de dados
3. Agente B
4. integração final

### Agente A — Prompt
```text
Você é o Agente Estrutura Condominial do GeoAdmin Pro.

Objetivo da Sprint 1:
1. criar a estrutura de vínculo por área (`area_clientes`)
2. enriquecer `areas_projeto` para operação por lote
3. criar visão agregada do empreendimento
4. manter compatibilidade com o fluxo atual

Escopo de escrita:
- infra/supabase/migrations/*
- backend/integracoes/areas_projeto.py
- backend/integracoes/projeto_clientes.py
- backend/routes/projetos.py
- backend/routes/documentos.py
- testes de backend

Regras:
- não quebrar endpoints atuais
- manter soft delete
- respeitar o isolamento por lote
- não inventar abstrações desnecessárias

Entrega final:
- migrations criadas
- shape das respostas novas
- testes criados
- riscos residuais
```

### Agente B — Prompt
```text
Você é o Agente Operação por Lote do GeoAdmin Pro.

Objetivo da Sprint 1:
1. transformar o detalhe do projeto em visão por lote
2. exibir status por lote/área
3. preparar a tela para crescer sem ficar confusa
4. manter linguagem operacional de topógrafo

Escopo de escrita:
- mobile/app/(tabs)/projeto/[id].tsx
- mobile/app/(tabs)/projeto/index.tsx
- mobile/components/ProjetoCard.tsx
- mobile/lib/* apenas se necessário para integração

Regras:
- não redesenhar o produto inteiro
- não mexer no backend do outro agente
- priorizar clareza, não decoração

Entrega final:
- fluxo visual por lote descrito
- arquivos alterados
- dependências para Sprint 2
```

---

## 5. Sprint 2 — Importação inicial e operação em lote

### Ordem recomendada
1. Agente A cria backend e contratos
2. Agente B monta fluxo visual e painel
3. integração e testes em lote

### Agente A — Prompt
```text
Você é o Agente Estrutura Condominial do GeoAdmin Pro.

Objetivo da Sprint 2:
1. permitir importação inicial de lotes/áreas
2. permitir criação em lote de vínculos entre áreas e participantes
3. permitir geração em lote de magic links
4. expor dados agregados para painel por lote

Escopo de escrita:
- backend/routes/projetos.py
- backend/integracoes/arquivos_projeto.py
- backend/integracoes/areas_projeto.py
- infra/supabase/migrations/*
- testes de backend

Regras:
- nenhum arquivo importado vira base oficial automaticamente
- manter compatibilidade com o fluxo manual
- tratar importação como operação assistida, não mágica

Entrega final:
- endpoints novos ou ampliados
- payloads de entrada/saída
- testes da importação e do lote
- riscos residuais
```

### Agente B — Prompt
```text
Você é o Agente Operação por Lote do GeoAdmin Pro.

Objetivo da Sprint 2:
1. criar o fluxo visual de importação de lotes
2. exibir painel operacional por lote
3. permitir seleção em lote e geração de links
4. fazer o topógrafo entender rapidamente o estado do empreendimento

Escopo de escrita:
- mobile/app/(tabs)/projeto/[id].tsx
- mobile/components/ProjetoCard.tsx
- componentes auxiliares de painel/lote

Regras:
- interface clara para alto volume
- sem excesso de complexidade visual
- não editar backend

Entrega final:
- fluxo de importação descrito
- fluxo de operação em lote descrito
- arquivos alterados
- pontos ainda dependentes da Sprint 3
```

---

## 6. Sprint 3 — Cliente escopado por lote e fim do legado

### Ordem recomendada
1. Agente A mata o legado e fecha contratos
2. Agente B refina o formulário e a leitura operacional
3. integração e teste ponta a ponta

### Agente A — Prompt
```text
Você é o Agente Estrutura Condominial do GeoAdmin Pro.

Objetivo da Sprint 3:
1. migrar totalmente para `projeto_clientes.magic_link_token`
2. remover dependência operacional de `clientes.magic_link_token`
3. escopar o formulário por participante e lote
4. registrar histórico de envio e reenvio

Escopo de escrita:
- backend/routes/documentos.py
- backend/integracoes/projeto_clientes.py
- migrations necessárias
- testes de backend

Regras:
- nenhum cliente pode cair em lote errado
- nenhum cliente pode acessar contexto global do projeto
- manter compatibilidade de transição só se for explicitamente controlada

Entrega final:
- estratégia de migração do legado
- shape final do contexto do formulário
- testes cobrindo ambiguidade e isolamento
```

### Agente B — Prompt
```text
Você é o Agente Operação por Lote do GeoAdmin Pro.

Objetivo da Sprint 3:
1. deixar o formulário claramente vinculado a um lote/unidade
2. mostrar papel do participante
3. melhorar leitura de envio/reenvio no detalhe do projeto
4. reforçar visualmente o recorte individual do cliente

Escopo de escrita:
- backend/static/formulario_cliente.html
- mobile/app/(tabs)/clientes/[id].tsx
- mobile/app/(tabs)/projeto/[id].tsx

Regras:
- cliente vê só o recorte dele
- linguagem clara para pessoa leiga
- não sobrecarregar o formulário

Entrega final:
- descrição do recorte visível ao cliente
- telas alteradas
- riscos de UX restantes
```

---

## 7. Sprint 4 — Governança da bandeja cartográfica

### Ordem recomendada
1. Agente A fecha storage, auditoria e promoção
2. Agente B monta a UX segura da bandeja
3. integração com mapa e projeto

### Agente A — Prompt
```text
Você é o Agente Estrutura Condominial do GeoAdmin Pro.

Objetivo da Sprint 4:
1. migrar arquivos antigos do fallback local para Supabase Storage
2. criar trilha de auditoria para promoção de arquivo a base oficial
3. expor ação explícita de promoção
4. manter rastreabilidade completa

Escopo de escrita:
- backend/integracoes/arquivos_projeto.py
- backend/routes/projetos.py
- infra/supabase/migrations/*
- scripts de migração se necessário
- testes de backend

Regras:
- promoção para base oficial sempre precisa de ação explícita do topógrafo
- auditar quem promoveu, quando e por quê

Entrega final:
- migration criada
- fluxo de promoção descrito
- estratégia de migração dos arquivos antigos
```

### Agente B — Prompt
```text
Você é o Agente Operação por Lote do GeoAdmin Pro.

Objetivo da Sprint 4:
1. tornar a bandeja cartográfica auditável e clara
2. exibir origem, classificação e status do arquivo
3. permitir promoção manual para base oficial
4. impedir qualquer percepção de automação indevida

Escopo de escrita:
- mobile/app/(tabs)/projeto/[id].tsx
- mobile/app/(tabs)/mapa/[id].tsx
- componentes de bandeja cartográfica

Regras:
- deixar muito claro o que é referência, esboço, perímetro técnico e documento
- não dar a entender que o sistema substituiu a base oficial sozinho

Entrega final:
- fluxo da bandeja descrito
- telas alteradas
- lacunas restantes
```

---

## 8. Sprint 5 — Confrontações e cartas em escala

### Ordem recomendada
1. Agente A fecha o modelo e a geração
2. Agente B cria UX de revisão
3. integração com projeto, clientes e documentos

### Agente A — Prompt
```text
Você é o Agente Estrutura Condominial do GeoAdmin Pro.

Objetivo da Sprint 5:
1. distinguir confrontações internas e externas
2. permitir confirmação antes da carta final
3. gerar cartas por seleção de lotes
4. harmonizar confrontantes manuais e detectados

Escopo de escrita:
- backend/integracoes/areas_projeto.py
- backend/integracoes/gerador_documentos.py
- backend/routes/projetos.py
- migrations se necessário
- testes de backend

Regras:
- confrontação automática é sugestão técnica, não decisão final automática
- preservar controle do topógrafo sobre a carta final

Entrega final:
- modelo de confrontação descrito
- fluxo de confirmação descrito
- testes cobrindo internos/externos
```

### Agente B — Prompt
```text
Você é o Agente Operação por Lote do GeoAdmin Pro.

Objetivo da Sprint 5:
1. exibir confrontações de forma revisável
2. separar internas e externas visualmente
3. permitir seleção de lotes para geração de cartas
4. não transformar o módulo em caixa-preta

Escopo de escrita:
- mobile/app/(tabs)/projeto/[id].tsx
- mobile/app/(tabs)/clientes/[id].tsx
- componentes visuais de confrontação

Regras:
- clareza antes de automação
- o topógrafo precisa entender o que o sistema detectou e por quê

Entrega final:
- UX de revisão descrita
- telas alteradas
- riscos de entendimento restantes
```

---

## 9. Sprint 6 — Lançamento assistido do piloto

### Ordem recomendada
1. Agente A fecha checklist técnico e ambiente
2. Agente B fecha leitura operacional e métricas
3. integração final e piloto assistido

### Agente A — Prompt
```text
Você é o Agente Estrutura Condominial do GeoAdmin Pro.

Objetivo da Sprint 6:
1. consolidar checklist técnico de lançamento
2. definir smoke test do fluxo principal
3. revisar variáveis de ambiente críticas
4. deixar critérios claros de rollback

Escopo de escrita:
- README.md
- documentação operacional
- scripts/checklists de smoke test
- backend apenas se precisar de suporte ao smoke

Regras:
- foco em operação real, não em documentação ornamental
- tudo precisa ser executável por uma pessoa do time

Entrega final:
- checklist de lançamento
- checklist de rollback
- dependências de ambiente
```

### Agente B — Prompt
```text
Você é o Agente Operação por Lote do GeoAdmin Pro.

Objetivo da Sprint 6:
1. preparar acompanhamento do piloto
2. destacar métricas mínimas do experimento
3. melhorar leitura de pendências reais no projeto
4. apoiar uso assistido nas primeiras semanas

Escopo de escrita:
- mobile/app/(tabs)/projeto/[id].tsx
- componentes de resumo/painel
- documentação operacional se necessário

Regras:
- priorizar métricas úteis, não vanity metrics
- o painel precisa ajudar a agir, não só enfeitar

Entrega final:
- métricas exibidas
- fluxo de acompanhamento descrito
- pendências para a fase pós-piloto
```

---

## 10. Como integrar ao fim de cada sprint

### Checklist do integrador
1. revisar contrato de dados entre backend e UI
2. rodar testes de backend
3. rodar TypeScript
4. testar fluxo principal manualmente
5. revisar riscos residuais
6. commitar com mensagem específica da sprint

### Regra de ouro do integrador
- se o Agente A mudou contrato, o Agente B só integra depois desse contrato estar estável
- se o Agente B percebe limitação do backend, isso volta como ajuste explícito, não como gambiarra na interface

---

## 11. Sequência recomendada para disparo real

### Melhor sequência prática
- Sprint 0: centralizada
- Sprint 1: Agente A → Agente B
- Sprint 2: Agente A → Agente B
- Sprint 3: Agente A → Agente B
- Sprint 4: Agente A → Agente B
- Sprint 5: Agente A → Agente B
- Sprint 6: Agente A → Agente B

### Quando rodar em paralelo de verdade
Só vale paralelizar quando:
- o Agente A já definiu schema/contrato
- e o Agente B vai tocar só interface e leitura desse contrato

---

## 12. Próximo passo sugerido

Se quisermos sair do planejamento para execução imediata, o ideal agora é:
1. abrir a Sprint 1
2. disparar primeiro o prompt do Agente A
3. revisar o contrato retornado
4. disparar o prompt do Agente B
5. integrar e validar
