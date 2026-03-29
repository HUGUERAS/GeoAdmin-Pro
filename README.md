# GeoAdmin Pro

GeoAdmin Pro e um sistema de administracao geoespacial para topografia, georreferenciamento e gestao de projetos rurais. O foco do produto e operar bem no campo e destravar a documentacao de clientes, imoveis, areas e confrontantes sem espalhar os dados em varios sistemas.

## Stack

- `mobile/`: React Native com Expo 54 e Expo Router
- `backend/`: FastAPI em Python
- `bridge/`: utilitario Windows para preparar e abrir workspaces do Métrica TOPO
- banco: Supabase com PostGIS
- integracoes: exportacao para Métrica TOPO e fluxo documental por magic link

## Modulos principais

- `Projetos`: dashboard, novo projeto, detalhe, status e atalhos operacionais
- `Mapa / CAD`: visualizacao e edicao do perimetro tecnico
- `Calculos`: ferramentas geodesicas que apoiam o CAD
- `Clientes & Documentacao`: lista de clientes, detalhe documental, cadastro, projetos vinculados, reenviar magic link, checklist, alertas, timeline, confrontantes e geometria de referencia do cliente
- `Areas & Confrontacoes`: multiplas areas por projeto, geometria de esboco e deteccao inicial de confrontacoes

## Fluxo GeoRegular

Esta rodada aproximou o produto do fluxo real de regularizacao:

- dashboard de projetos com busca, filtros, metricas e progresso
- criacao de novo projeto com cliente principal e opcao de gerar magic link
- detalhe do projeto como hub operacional com secoes de `Visao`, `Areas`, `Clientes`, `Confrontacoes` e `Documentos`
- formulario publico do cliente em 4 etapas:
  - dados pessoais
  - dados do imovel
  - esboco simples da area + uploads
  - confrontantes e observacoes
- reaproveitamento de dados do cliente e da geometria de referencia para alimentar o processo tecnico
- deteccao inicial de confrontacoes entre areas do mesmo projeto
- geracao de cartas de confrontacao em ZIP

## Clientes & Documentacao

O modulo de clientes foi modelado como hub documental. Hoje ele cobre:

- lista e busca de clientes
- detalhe completo do cliente
- edicao de cadastro
- projetos vinculados
- reenvio de magic link
- status de formulario e documentos
- CRUD de confrontantes
- checklist documental por projeto
- alertas de pendencia
- timeline de atendimento
- geometria de referencia do cliente com:
  - desenho manual por coordenadas
  - importacao por conteudo `GeoJSON`, `KML`, `CSV` e `TXT`
  - importacao por arquivo `GeoJSON`, `KML`, `CSV`, `TXT` e `SHP` em `.zip`
  - preview comparativo com o perimetro tecnico

Importante:

- `referencia do cliente`: croqui ou importacao informal para orientar o processo
- `perimetro tecnico`: geometria oficial validada no CAD

## Estrutura

- `mobile/app/(tabs)/projeto`: lista e detalhe de projetos
- `mobile/app/(tabs)/projeto/novo.tsx`: criacao de novo projeto
- `mobile/app/(tabs)/mapa`: CAD e edicao de perimetro
- `mobile/app/(tabs)/calculos`: ferramentas geodesicas
- `mobile/app/(tabs)/clientes`: hub de clientes e documentacao
- `backend/routes`: rotas FastAPI
- `backend/integracoes`: integracoes e utilitarios de dominio
- `bridge/`: GeoAdmin Bridge para o fluxo GeoAdmin -> Métrica
- `infra/supabase/migrations`: migrations SQL

## Requisitos

- Node.js 18+
- npm
- Python 3.11+
- credenciais do Supabase no backend

## Variaveis de ambiente

Crie `backend/.env` com:

```env
SUPABASE_URL=https://jrlrlsotwsiidglcbifo.supabase.co
SUPABASE_KEY=seu_service_key_ou_anon_key
```

Opcional:

```env
PROJ_DATA=D:\coletoraprolanddd\outras biblioteecas\proj
EXPO_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

## Rodando localmente

### Backend

```bash
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Healthcheck:

```bash
curl http://127.0.0.1:8000/health
```

### Mobile / Web

```bash
cd mobile
npm install
npm run web
```

Rotas uteis na web:

- `http://127.0.0.1:8081/projeto`
- `http://127.0.0.1:8081/projeto/novo`
- `http://127.0.0.1:8081/calculos`
- `http://127.0.0.1:8081/clientes`

### Android

```bash
cd mobile
npm install
npx expo start --android
```

Se o `Expo Go` pedir login do Google no emulador, prefira o build local nativo:

```bash
cd mobile
npx expo run:android
```

Como o app usa `expo-document-picker`, alteracoes nessa parte exigem novo build nativo para distribuicao fora do ambiente de desenvolvimento.

## Build e deploy

### Android APK

```bash
cd mobile
npx eas-cli@latest build --platform android --profile preview
```

### Web

```bash
cd mobile
npm run build:web
```

### Backend

O backend esta preparado para deploy no Railway usando `backend/Procfile` e `backend/railway.json`.

### GeoAdmin Bridge

O MVP inicial do bridge prepara um workspace local para o Métrica TOPO:

```bash
python bridge/geoadmin_bridge.py --projeto-id 36510522-3544-46fe-bbe1-e6348dd708df
```

O pacote `POST /projetos/{id}/metrica/preparar` agora inclui:

- `manifesto.json`
- `dados/projeto.json`
- `dados/cliente.json`
- `dados/confrontantes.json`
- `dados/documentos.json`
- `dados/pontos.json`
- `dados/perimetro_ativo.geojson`
- `dados/referencia_cliente.geojson`
- arquivos `TXT`, `CSV`, `KML` e `DXF`

Tambem existe o manifesto puro para o bridge:

```text
GET /projetos/{id}/metrica/manifesto
```

## API GeoRegular

Principais rotas da camada nova:

- `POST /projetos`
- `GET /projetos/{id}`
- `GET /projetos/{id}/areas`
- `POST /projetos/{id}/areas`
- `PATCH /projetos/{id}/areas/{area_id}`
- `GET /projetos/{id}/confrontacoes`
- `GET /projetos/{id}/confrontacoes/cartas`
- `GET /formulario/cliente/contexto?token=...`
- `POST /formulario/cliente`

## Observacoes de persistencia

A geometria de referencia do cliente tenta persistir primeiro em `geometrias_referencia_cliente` no Supabase. Enquanto a migration ainda nao estiver aplicada, o backend usa fallback local em `backend/data/geometrias_referencia_cliente.json`.

A primeira versao de `areas` e `confrontacoes` do projeto usa store local em `backend/data/areas_projeto.json` para acelerar a rodada funcional. O proximo passo natural e migrar essa camada para banco real com PostGIS.

Para ativar a persistencia completa no banco, aplique:

- `infra/supabase/migrations/016_geometrias_referencia_cliente.sql`

## Status atual

- `Projetos`: implementado
- `Mapa / CAD`: implementado
- `Calculos geodesicos`: implementado
- `Clientes & Documentacao`: implementado em MVP avancado
- `Comparacao referencia do cliente x perimetro tecnico`: implementada
- `Importacao de referencia do cliente por arquivo`: implementada
- `Dashboard GeoRegular de projetos`: implementado
- `Novo projeto com cliente principal + magic link`: implementado
- `Formulario publico em etapas`: implementado
- `Areas por projeto`: implementado em primeira versao com store local
- `Confrontacoes entre areas do projeto`: implementado em primeira versao com deteccao e cartas ZIP
