# Backlog Executável — Piloto Condominial 120 Lotes

**Base:** [PLANO_PILOTO_CONDOMINIAL_120_LOTES.md](C:/Users/User/OneDrive/Documentos/GeoAdmin-Pro/PLANO_PILOTO_CONDOMINIAL_120_LOTES.md)  
**Objetivo:** transformar o plano do piloto em uma sequência implementável de sprints.

---

## Princípio de execução

A regra para este backlog é simples:
**não abrir muitas frentes ao mesmo tempo.**

A ordem foi montada para que cada sprint entregue uma capacidade operacional real e destrave a seguinte.

---

## Sprint 0 — Higiene e base de lançamento

**Objetivo:** deixar a linha atual limpa, estável e pronta para virar base do piloto.

### Entregas
- limpeza do repositório (`__pycache__`, logs locais, arquivos locais rastreados por engano)
- merge/review da linha atual
- checklist de deploy com `APP_URL` pública
- smoke test publicado do fluxo principal

### Tasks técnicas
1. parar de rastrear artefatos locais
2. fortalecer `.gitignore` / `backend/.gitignore`
3. garantir deploy estável com `APP_URL`
4. rodar smoke test pós-deploy

### Arquivos mais prováveis
- `.gitignore`
- `backend/.gitignore`
- `README.md`
- `SPRINT_CODE_REVIEW.md`

### Definição de pronto
- branch principal limpa
- ambiente publicado saudável
- magic link abrindo com URL pública

---

## Sprint 1 — Estrutura de dados do condomínio

**Objetivo:** dar ao sistema estrutura real para empreendimento com muitos lotes.

### Entregas
- modelagem de participantes por área
- status por lote/área
- dados mínimos do lote para operação em massa

### Tasks técnicas
1. criar tabela `area_clientes`
- função: vincular vários clientes/participantes a uma área
- campos mínimos sugeridos:
  - `id`
  - `area_id`
  - `cliente_id`
  - `papel`
  - `principal`
  - `recebe_magic_link`
  - `ordem`
  - `deleted_at`

2. enriquecer `areas_projeto`
- considerar adicionar ou padronizar:
  - `codigo_lote`
  - `quadra`
  - `setor`
  - `status_operacional`
  - `status_documental`

3. criar visão agregada por projeto
- quantos lotes existem
- quantos têm participante
- quantos estão com formulário ok
- quantos estão prontos

4. ajustar backend para ler esse modelo
- projeto → áreas → participantes por área
- sem quebrar o que já existe hoje

### Arquivos mais prováveis
- `infra/supabase/migrations/`
- `backend/integracoes/areas_projeto.py`
- `backend/integracoes/projeto_clientes.py`
- `backend/routes/projetos.py`
- `backend/routes/documentos.py`

### Dependência
- depende só da Sprint 0

### Definição de pronto
- o sistema representa corretamente um projeto com muitos lotes e múltiplos envolvidos por lote

---

## Sprint 2 — Importação inicial e operação em lote

**Objetivo:** permitir carregar e operar o empreendimento sem cadastro artesanal de 120 lotes na mão.

### Entregas
- importação inicial dos lotes/áreas
- vínculo em lote de participantes
- geração em lote de magic links
- painel de status por lote

### Tasks técnicas
1. importação inicial de lotes
- aceitar `CSV`, `GeoJSON`, `KML`, `SHP ZIP`
- classificar o conteúdo como áreas/lotes do empreendimento

2. criação em lote de vínculos
- associar participantes às áreas importadas
- permitir principal + adicionais

3. geração em lote de links
- selecionar várias áreas/participantes
- gerar e copiar lote de links ou mensagens

4. painel operacional por lote
- filtros como:
  - sem participante
  - sem formulário
  - sem croqui
  - sem confrontantes
  - pronto

### Arquivos mais prováveis
- `backend/routes/projetos.py`
- `backend/integracoes/arquivos_projeto.py`
- `mobile/app/(tabs)/projeto/[id].tsx`
- `mobile/components/ProjetoCard.tsx`
- futura tela web dedicada para operação em massa

### Dependência
- depende da Sprint 1

### Definição de pronto
- conseguimos subir o empreendimento e começar a operar dezenas de lotes sem processo artesanal

---

## Sprint 3 — Cliente escopado por lote e fim do legado

**Objetivo:** garantir isolamento correto do cliente e tornar o fluxo de formulário robusto para o piloto.

### Entregas
- extinção do legado `clientes.magic_link_token`
- magic link 100% por vínculo/participante
- contexto do formulário por lote/área
- histórico de envio/reenvio

### Tasks técnicas
1. migrar tudo para `projeto_clientes.magic_link_token`
2. remover o fallback legado quando não for mais necessário
3. melhorar o contexto do formulário
- mostrar projeto
- mostrar lote/unidade
- mostrar o papel do participante

4. registrar eventos de envio
- quem gerou
- quando gerou
- para qual lote/participante

### Arquivos mais prováveis
- `backend/routes/documentos.py`
- `backend/integracoes/projeto_clientes.py`
- `backend/static/formulario_cliente.html`
- `backend/tests/test_magic_link_participantes.py`

### Dependência
- depende da Sprint 1
- fica muito melhor quando a Sprint 2 já tiver importação/vínculo em lote

### Definição de pronto
- nenhum cliente consegue cair no lote errado ou enxergar contexto de outro participante

---

## Sprint 4 — Governança da bandeja cartográfica

**Objetivo:** deixar o mapa e os arquivos sob controle para o piloto real.

### Entregas
- migração dos arquivos antigos para Supabase Storage
- trilha de auditoria de promoção para base oficial
- ação explícita de promoção por topógrafo

### Tasks técnicas
1. script de migração dos arquivos antigos
2. tabela `eventos_cartograficos`
3. ação `promover para base oficial`
4. registro de autoria, data e origem da promoção

### Arquivos mais prováveis
- `backend/integracoes/arquivos_projeto.py`
- `infra/supabase/migrations/`
- `backend/routes/projetos.py`
- `mobile/app/(tabs)/projeto/[id].tsx`
- `mobile/app/(tabs)/mapa/[id].tsx`

### Dependência
- pode rodar em paralelo com Sprint 3, mas eu faria logo depois dela

### Definição de pronto
- a equipe confia que nenhum arquivo vira base oficial sem decisão humana registrada

---

## Sprint 5 — Confrontações e cartas em escala

**Objetivo:** fazer o módulo de confrontação suportar um empreendimento maior sem virar caixa-preta.

### Entregas
- distinção entre confrontações internas e externas
- confirmação operacional antes da carta final
- geração por seleção de lotes

### Tasks técnicas
1. marcar confrontação como `interna` ou `externa`
2. permitir revisão/aceite do topógrafo
3. gerar cartas por lote, bloco ou seleção
4. ajustar o modelo de confrontantes manuais para conviver bem com os detectados

### Arquivos mais prováveis
- `backend/integracoes/areas_projeto.py`
- `backend/routes/projetos.py`
- `backend/routes/clientes/`
- `backend/integracoes/gerador_documentos.py`

### Dependência
- depende de Sprints 1, 2 e 3 bem consolidadas

### Definição de pronto
- confrontação deixa de ser só “detecção automática” e vira ferramenta confiável de produção

---

## Sprint 6 — Lançamento assistido do piloto

**Objetivo:** colocar o cliente real usando sem perder o controle do experimento.

### Entregas
- ambiente publicado estável
- checklist de operação
- rotina de suporte inicial
- métricas do piloto

### Tasks técnicas e operacionais
1. smoke test publicado
2. checklist do primeiro envio de links
3. monitoramento dos primeiros retornos do formulário
4. painel simples de métricas do piloto

### Métricas mínimas
- lotes cadastrados
- lotes com participante
- lotes com formulário preenchido
- lotes com croqui recebido
- lotes com confrontantes ok
- lotes prontos

### Dependência
- depende da Sprint 3 no mínimo
- idealmente com Sprint 4 e 5 adiantadas

### Definição de pronto
- o sistema entra em uso real com risco controlado e critério claro de rollback

---

## Ordem recomendada de execução

### Ordem ideal
1. Sprint 0
2. Sprint 1
3. Sprint 2
4. Sprint 3
5. Sprint 4
6. Sprint 5
7. Sprint 6

### Ordem mínima para começar o piloto mais cedo
1. Sprint 0
2. Sprint 1
3. Sprint 2
4. Sprint 3
5. Sprint 6

Essa ordem mínima coloca o piloto em campo mais cedo, mas com menos governança cartográfica e menos maturidade nas confrontações.

---

## Minha recomendação prática

Se eu fosse conduzir isso com foco total em entrega, eu faria assim:

### Semana 1
- Sprint 0
- Sprint 1

### Semana 2
- Sprint 2
- Sprint 3

### Semana 3
- Sprint 4
- início da Sprint 5

### Semana 4
- finalizar Sprint 5
- Sprint 6
- início do piloto assistido

---

## Próximo movimento sugerido

Se quisermos sair deste documento para execução imediata, o melhor próximo passo é abrir agora:

1. **Sprint 1 detalhada**
2. tickets técnicos da Sprint 1
3. ordem de implementação por arquivo

Em termos práticos, eu começaria por:
- migration `area_clientes`
- leitura/escrita backend dessa tabela
- status por lote em `areas_projeto`
- detalhe do projeto com visão por lote
