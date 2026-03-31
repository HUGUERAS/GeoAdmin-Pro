# Plano de Ação — Piloto Condominial com 120 Lotes

**Data:** 31/03/2026  
**Contexto:** preparação do GeoAdmin Pro para um piloto real de regularização fundiária com condomínio/loteamento de aproximadamente 120 lotes.  
**Objetivo deste documento:** preservar o contexto do produto, consolidar o estado atual e transformar a visão do piloto em partes implementáveis.

---

## 1. O que é o GeoAdmin Pro

O GeoAdmin Pro é o sistema operacional do trabalho do topógrafo.

Ele junta, no mesmo produto:
- gestão de projetos de regularização fundiária
- cadastro e reaproveitamento de clientes
- magic link para coleta de dados pelo cliente
- geometria informal do cliente via esboço/croqui
- múltiplas áreas por projeto
- detecção de confrontações
- geração de cartas e documentos do processo
- integração com o fluxo técnico do Métrica TOPO
- apoio de mapa/CAD e ferramentas geodésicas

A tese do produto é simples:
**o cliente contribui com informação; o topógrafo consolida a informação como base técnica oficial.**

---

## 2. Onde o produto está hoje

### 2.1 O que já existe e funciona

- `Projetos`: dashboard, criação, detalhe, status e visão operacional.
- `Clientes & Documentação`: cadastro, checklist, alertas, timeline, confrontantes e geometria de referência.
- `Magic link`: envio de formulário público para o cliente.
- `Formulário do cliente`: dados pessoais, imóvel, croqui/esboço, confrontantes e anexos.
- `Áreas do projeto`: múltiplas áreas por projeto, com geometria de esboço e geometria final.
- `Confrontações`: detecção inicial entre áreas do mesmo projeto.
- `Cartas de confrontação`: geração em ZIP.
- `Documentos`: geração do pacote documental principal.
- `Bandeja cartográfica`: upload de arquivos do projeto com origem e classificação.
- `Mapa/CAD`: base visual e operacional para o perímetro técnico.
- `Cálculos`: ferramentas que servem ao CAD.
- `Bridge`: integração GeoAdmin → Métrica.

### 2.2 O que foi reforçado na rodada mais recente

- múltiplos participantes por projeto
- magic link escopado por participante
- separação entre endereço residencial e localização do imóvel
- bandeja cartográfica com classificação controlada
- persistência da bandeja em **Supabase Storage**
- confronto de links legados ambíguos bloqueado
- reenvio do formulário sem duplicação cega de confrontantes
- reversão compensatória da criação do projeto quando uma etapa posterior falha

### 2.3 O que ainda não está no estado ideal

- ainda existe legado de `clientes.magic_link_token`
- falta migrar arquivos cartográficos antigos salvos em disco local para o Storage
- ainda não existe trilha formal de auditoria para promoção de arquivo a base oficial
- falta modelagem de copropriedade por área (`area_clientes`)
- a experiência para projeto condominial grande ainda não está especializada
- a operação publicada ainda depende de checklist de deploy bem disciplinado (`APP_URL`, ambientes, smoke tests)

---

## 3. O que queremos no piloto de 120 lotes

Queremos provar que o GeoAdmin consegue operar um caso real de condomínio/loteamento com volume, sem perder controle documental e espacial.

### 3.1 Objetivo do piloto

Validar o GeoAdmin Pro como hub central de operação para um projeto com:
- muitos lotes
- muitos clientes/participantes
- múltiplas áreas vinculadas
- confrontações internas e externas
- coleta documental via magic link
- organização técnica suficiente para produção de peças e cartas

### 3.2 Resultado esperado do piloto

Ao final do piloto, o sistema deve permitir:
- cadastrar o empreendimento/projeto principal
- registrar os 120 lotes como áreas organizadas
- vincular clientes/participantes aos lotes corretos
- enviar magic link individual sem vazamento entre lotes
- receber e organizar dados do cliente com segurança
- importar e manter base cartográfica do projeto
- detectar confrontações relevantes
- gerar cartas/documentos com coerência operacional
- exportar o necessário para o fluxo técnico do escritório

---

## 4. Princípios que não podem ser violados

1. **Nenhum arquivo importado altera automaticamente o perímetro oficial sem ação explícita do topógrafo.**
2. **O cliente nunca pode enxergar outros imóveis, outros clientes ou o mapa global do projeto.**
3. **O GeoAdmin é a fonte única de verdade.** Não espalhar o mesmo dado em planilhas e sistemas paralelos sem necessidade.
4. **Geometria do cliente é informativa; geometria do topógrafo é oficial.**
5. **Projeto condominial precisa de estrutura, não improviso.** O sistema deve refletir a hierarquia real: projeto → lotes/áreas → participantes → documentos → confrontações.

---

## 5. Leitura do piloto: que tipo de projeto é esse?

Para esse piloto, o GeoAdmin deixa de ser apenas “projeto rural com um cliente principal” e passa a precisar de um modo de operação mais próximo de:

- empreendimento com muitos lotes
- muitos participantes diferentes
- repetição massiva de fluxo documental
- necessidade de enxergar o todo e o recorte de cada unidade

Isso muda a prioridade do sistema.

### Antes
- bom para projeto unitário ou multiárea pequeno
- forte em operação artesanal e técnica

### Agora
- precisa continuar técnico, mas ganhar capacidade de **operação em lote**
- precisa de visão gerencial por lote/unidade
- precisa de automação de cadastros, vínculos, status e pendências

---

## 6. Escopo recomendado do piloto

### 6.1 O que deve entrar

- cadastro do projeto principal
- cadastro/importação dos lotes/áreas
- vínculo entre lote e participantes
- magic link por participante
- formulário do cliente com recorte individual
- bandeja cartográfica por projeto
- status operacional por lote
- confrontações
- cartas/documentos essenciais
- exportação mínima para continuidade técnica do trabalho

### 6.2 O que não deve entrar agora

- automação completa de todas as peças jurídicas possíveis
- visão pública do mapa completo para cliente
- substituição automática do perímetro oficial por arquivos importados
- workflow sofisticado de aprovações internas multiusuário
- polimento visual perfeito antes da validação operacional

---

## 7. Plano de ação em fases

## Fase 0 — Congelamento saudável do contexto

**Objetivo:** parar de perder contexto e estabilizar a linha de trabalho.

### Entregas
- documento do piloto condominial
- checklist do ambiente publicado
- definição clara do escopo do piloto
- backlog priorizado por fases

### Partes a codar
- documentação de contexto
- checklists operacionais de deploy e teste

### Critério de saída
- todos sabem o que o piloto é, o que entra, o que não entra e qual é a sequência de execução

---

## Fase 1 — Fundacão de dados para condomínio/loteamento

**Objetivo:** modelar corretamente a estrutura do empreendimento e dos lotes.

### O que precisa existir
- projeto principal
- áreas/lotes bem definidos
- participantes por projeto
- participantes por área quando houver copropriedade real

### Partes a codar
1. `area_clientes`
- nova tabela para representar coproprietários/participantes por área
- evita forçar tudo em `areas_projeto.cliente_id`

2. status por lote
- status operacional/documental por área
- exemplo: `aguardando_cliente`, `formulario_ok`, `croqui_recebido`, `confrontantes_ok`, `peca_pronta`

3. visão agregada por empreendimento
- totais por lote e por status
- quantos lotes prontos, pendentes, sem formulário, etc.

### Arquivos que provavelmente serão tocados
- `infra/supabase/migrations/`
- `backend/integracoes/areas_projeto.py`
- `backend/integracoes/projeto_clientes.py`
- `backend/routes/projetos.py`
- `backend/routes/documentos.py`
- `mobile/app/(tabs)/projeto/[id].tsx`

### Critério de saída
- o sistema consegue representar corretamente 120 lotes e múltiplos participantes sem colapso de modelagem

---

## Fase 2 — Operação em lote

**Objetivo:** deixar de operar lote por lote manualmente como se fosse tudo caso isolado.

### O que precisa existir
- importação inicial de lotes
- criação em massa de vínculos/participantes
- geração em lote de magic links
- painel de pendências por lote

### Partes a codar
1. importação em massa de áreas/lotes
- CSV/GeoJSON/KML/SHP ZIP
- classificação de cada item como lote/área do empreendimento

2. geração em lote de participantes e links
- selecionar várias áreas
- vincular participantes
- gerar links individualizados

3. painel de acompanhamento
- quadro por lote
- filtros: sem cliente, sem formulário, sem croqui, sem confrontante, pronto

### Arquivos que provavelmente serão tocados
- `backend/routes/projetos.py`
- `backend/integracoes/arquivos_projeto.py`
- `mobile/app/(tabs)/projeto/[id].tsx`
- `mobile/components/ProjetoCard.tsx`
- futuras telas web dedicadas

### Critério de saída
- o topógrafo ou escritório consegue mover dezenas de lotes sem operar tudo na unha

---

## Fase 3 — Bandeja cartográfica e governança do mapa

**Objetivo:** garantir que a base cartográfica fique organizada e auditável.

### O que precisa existir
- importação segura de arquivos
- classificação por uso
- promoção manual para base oficial
- histórico da promoção

### Partes a codar
1. migração dos arquivos antigos do fallback local para Supabase Storage
2. tabela de auditoria, por exemplo `eventos_cartograficos`
3. ação explícita `promover para base oficial`
4. registro de quem promoveu, quando e por quê

### Arquivos que provavelmente serão tocados
- `backend/integracoes/arquivos_projeto.py`
- `infra/supabase/migrations/`
- `backend/routes/projetos.py`
- `mobile/app/(tabs)/projeto/[id].tsx`
- `mobile/app/(tabs)/mapa/[id].tsx`

### Critério de saída
- nenhuma ambiguidade entre croqui do cliente, referência visual e perímetro oficial

---

## Fase 4 — Cliente, formulário e recorte de acesso

**Objetivo:** tornar o fluxo do cliente seguro, simples e escalável.

### O que precisa existir
- link por participante
- recorte por área/lote
- formulário sem vazamento entre vizinhos/lotes
- reenvio seguro e editável

### Partes a codar
1. matar o legado de `clientes.magic_link_token`
2. usar apenas `projeto_clientes.magic_link_token`
3. melhorar contexto do formulário para mostrar claramente o lote/unidade
4. registrar histórico de envio/reenvio de link

### Arquivos que provavelmente serão tocados
- `backend/routes/documentos.py`
- `backend/integracoes/projeto_clientes.py`
- `backend/static/formulario_cliente.html`
- `backend/tests/test_magic_link_participantes.py`

### Critério de saída
- cada cliente vê apenas o seu recorte e o escritório confia nesse isolamento

---

## Fase 5 — Confrontações e cartas em escala

**Objetivo:** sair do MVP de confrontação e chegar a algo operável para condomínio/loteamento.

### O que precisa existir
- confrontações internas entre lotes
- confrontações externas relevantes
- confirmação operacional das confrontações
- cartas por lote ou em lote

### Partes a codar
1. distinguir confrontação interna vs externa
2. permitir revisão/aceite do topógrafo antes da carta final
3. gerar cartas por seleção de lotes
4. melhorar o modelo dos confrontantes manuais para não conflitar com os detectados

### Arquivos que provavelmente serão tocados
- `backend/integracoes/areas_projeto.py`
- `backend/routes/projetos.py`
- `backend/routes/clientes/`
- `backend/integracoes/gerador_documentos.py`
- `mobile/app/(tabs)/projeto/[id].tsx`

### Critério de saída
- o sistema consegue apoiar o trabalho de confrontação sem virar caixa-preta perigosa

---

## Fase 6 — Documentos e fluxo técnico de produção

**Objetivo:** garantir que a operação documental acompanhe o volume do piloto.

### O que precisa existir
- pacote mínimo por lote
- geração documental repetível
- integração clara com o escritório/Métrica

### Partes a codar
1. revisar as peças para contexto condominial/loteamento
2. suportar geração por lote ou por grupo de lotes
3. melhorar o pacote de exportação para escritório
4. checklist técnico-documental por lote

### Arquivos que provavelmente serão tocados
- `backend/integracoes/gerador_documentos.py`
- `backend/routes/documentos.py`
- `backend/routes/exportacao/`
- `bridge/`

### Critério de saída
- o escritório recebe insumos organizados, sem retrabalho desnecessário

---

## Fase 7 — Lançamento controlado do piloto

**Objetivo:** testar em campo sem perder confiança no produto.

### O que precisa existir
- ambiente publicado estável
- `APP_URL` correta
- checklist de deploy
- smoke test pós-deploy
- critério claro de rollback

### Partes a codar / operar
1. script/checklist de smoke test do fluxo principal
2. revisão final do CORS e das variáveis de ambiente
3. observabilidade mínima de falhas críticas
4. ambiente de homologação e ambiente de produção, se possível

### Critério de saída
- dá para colocar cliente real usando o sistema sem “aposta cega”

---

## 8. Backlog priorizado para começar já

### Prioridade máxima
1. `area_clientes`
2. painel de status por lote
3. importação inicial de lotes/áreas
4. geração em lote de magic links
5. matar o legado de token em `clientes`

### Prioridade alta
6. migração dos arquivos antigos para Supabase Storage
7. auditoria da promoção de arquivos a base oficial
8. distinção entre confrontação interna e externa
9. revisão da geração documental para contexto condominial

### Prioridade média
10. visão web mais forte para operação em massa
11. melhorias de UX do detalhe do projeto para condomínio
12. métricas operacionais por lote e por participante

---

## 9. O que medir no piloto

- quantos lotes foram cadastrados
- quantos lotes têm participante vinculado
- quantos magic links foram enviados
- taxa de preenchimento do formulário
- quantos lotes têm croqui/esboço recebido
- quantos lotes estão com confrontantes ok
- quantos lotes estão com documentação pronta
- quantos erros operacionais ocorreram por semana

Essas métricas vão dizer se o produto está só “funcionando” ou se está realmente operando bem.

---

## 10. Definição de sucesso do piloto

O piloto será considerado bem-sucedido se o GeoAdmin conseguir, com estabilidade razoável:
- organizar o empreendimento inteiro
- operar os lotes com clareza
- isolar corretamente o recorte de cada cliente
- receber e organizar os dados dos participantes
- apoiar a confrontação e a documentação
- manter o topógrafo no controle da base técnica oficial

---

## 11. Próximo movimento recomendado

Se formos seguir com disciplina, a melhor sequência agora é:

1. limpar o repositório e o ambiente local
2. fechar o merge do estado atual que já está maduro
3. abrir uma sprint específica chamada **Piloto Condominial 120 Lotes**
4. começar pela fundação de dados:
   - `area_clientes`
   - status por lote
   - importação inicial de lotes
5. só depois ir para automações mais pesadas

---

## 12. Resumo em uma frase

**O GeoAdmin já tem cérebro técnico para esse piloto; o próximo passo é ganhar estrutura operacional para volume condominial sem perder o rigor topográfico.**
