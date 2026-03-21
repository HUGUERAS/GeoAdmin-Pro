# Registro da Base Estável

## Objetivo da leva

Estabilizar a base do GeoAdmin-Pro sem entrar ainda em multiárea ou painel do cliente.

O foco desta leva foi:

- corrigir a persistência visual e lógica do perímetro editado;
- alinhar contratos entre banco, backend e mobile;
- impedir perda permanente de pontos no sync offline;
- unificar a origem da URL da API no app;
- fechar o erro de build do mobile.

## Problemas corrigidos

### 1. Perímetro salvo não virava a geometria principal do projeto

Antes:

- a tela de mapa/CAD sempre reconstruía o polígono a partir de `data.pontos`;
- o perímetro salvo em `/perimetros/` não era reaproveitado como geometria oficial;
- ao sair e voltar da tela, a edição podia parecer “sumir”.

Agora:

- `GET /projetos/{id}` retorna `perimetro_ativo`;
- a regra de prioridade do polígono ativo é:
  - `definitivo`
  - `editado`
  - `original`
  - fallback para `pontos`
- o mobile separa `pontos` de `polygonVerts`;
- vértices que existem apenas no perímetro também passam a aparecer como pontos visíveis no mapa/CAD;
- ao salvar a edição, o app atualiza o perímetro local e continua exibindo a geometria salva.

### 2. Sync offline podia perder pontos

Antes:

- qualquer falha de rede movia o ponto para `error`;
- a busca por pendências considerava apenas `pending`;
- isso tirava os pontos da fila de retry;
- em sucesso parcial, o app marcava tudo como sincronizado.

Agora:

- a fila de sync considera todo item com `sync_status != 'synced'`;
- erros continuam retryáveis;
- o backend retorna status por item (`sincronizado`, `duplicado`, `erro`);
- o mobile marca como sincronizado somente os `local_id` confirmados pelo backend.

### 3. Contratos de schema usados pelo backend não estavam versionados

Foi adicionada uma migration incremental para:

- `perimetros`;
- normalização de `criado_em`;
- colunas ausentes em `projetos`, `clientes` e `pontos`;
- compatibilização das views:
  - `vw_projetos_completo`
  - `vw_formulario_cliente`
  - `vw_pontos_geo`
  - `vw_pontos_utm`

### 4. Base URL da API estava hardcoded em produção

Antes:

- parte do app usava URL fixa da Railway;
- outra parte usava resolução dinâmica em `mobile/lib/api.ts`.

Agora:

- `mobile/constants/Api.ts` passou a usar `getApiBaseUrl()`;
- todos os pontos que ainda usam `API_URL` passam a compartilhar a mesma origem lógica da API.

### 5. Contrato do cálculo inverso estava inconsistente

Antes:

- backend retornava `azimute_graus_ms`;
- app e versão web já estavam preparados para `azimute_dms`.

Agora:

- o backend retorna `azimute_dms`.

### 6. Erro de build no ícone Bluetooth

Antes:

- `Feather` recebia `bluetooth-off`, que não existe no set tipado do pacote.

Agora:

- o ícone foi trocado para `bluetooth`.

## Mudanças de banco

Arquivo criado:

- `infra/supabase/migrations/015_base_estavel.sql`

Principais ajustes:

- adiciona e normaliza colunas faltantes em `projetos`;
- adiciona e normaliza colunas faltantes em `clientes`;
- ajusta `pontos` para o contrato atual do backend/mobile;
- cria `perimetros`;
- recria as views consumidas hoje pelo backend.

Observação:

- esta leva não executou a migration no banco remoto a partir desta sessão;
- a migration foi preparada e versionada no repositório.

## Mudanças de backend

Arquivos alterados:

- `backend/main.py`
- `backend/routes/perimetros.py`
- `backend/routes/pontos.py`
- `backend/routes/projetos.py`

Resumo:

- `GET /projetos/{id}` agora retorna `perimetro_ativo`;
- foi criado helper de resolução do perímetro ativo no backend;
- o sync de pontos agora retorna resultado por item e listas de `local_id` por status;
- o contrato do endpoint de inverso foi unificado para `azimute_dms`.

## Mudanças de mobile

Arquivos alterados diretamente nesta leva:

- `mobile/app/(tabs)/mapa/[id].tsx`
- `mobile/app/bluetooth.tsx`
- `mobile/constants/Api.ts`
- `mobile/lib/db.ts`
- `mobile/lib/sync.ts`

Resumo:

- o mapa/CAD agora diferencia marcadores (`pontos`) de geometria (`polygonVerts`);
- nenhum vértice do perímetro fica invisível fora do modo de edição;
- a edição parte do polígono ativo atual;
- ao salvar, o polígono salvo permanece como geometria exibida;
- a fila de sync não perde mais pontos após erro;
- o app inteiro passa a compartilhar a mesma base URL resolvida.

## Validações executadas

Validações que passaram:

- `npx tsc --noEmit` em `mobile/`
- compilação de sintaxe do backend com `python -m compileall backend`

Validações não executadas nesta sessão:

- smoke test contra Supabase com a migration aplicada;
- validação E2E real do fluxo de perímetro em dispositivo;
- validação E2E real do sync offline contra backend ativo.

## Riscos pendentes e próximos passos

### Pendências técnicas

- aplicar a migration `015_base_estavel.sql` no banco alvo;
- validar se o banco atual já contém algum desvio manual fora das migrations;
- testar o fluxo de projeto com:
  - sem perímetro salvo
  - perímetro `original`
  - perímetro `editado`
  - perímetro `definitivo`

### Escopo ainda fora desta leva

- multiárea;
- identificação de vizinhos;
- painel de acompanhamento do cliente;
- alinhamento da versão web ao mesmo comportamento do `perimetro_ativo`.

### Próxima recomendação

Depois de aplicar a migration no banco, fazer uma rodada curta de smoke test com:

1. criação/abertura de projeto;
2. edição e salvamento de perímetro;
3. reabertura da tela de mapa;
4. sync parcial de pontos com erro controlado;
5. geração de documento em projeto com dados mínimos válidos.
