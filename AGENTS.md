# GeoAdmin Pro — Contexto para Codex

## O Projeto
Sistema de administração geoespacial para topografia, georreferenciamento e gestão de projetos rurais. MVP voltado para uso em campo (Android APK) e desktop (web futura).

## Stack
| Camada | Tecnologia | Diretório |
|---|---|---|
| Mobile | React Native (Expo 54 + Expo Router) | `mobile/` |
| Backend | FastAPI (Python) | `backend/` |
| Banco | Supabase + PostGIS | — |
| Integração | Métrica TOPO via `POST /metrica/txt` | `backend/integracoes/` |

## Arquitetura
- GeoAdmin-Pro é a **fonte única de verdade** — não replicar dados em múltiplos sistemas
- Credenciais **exclusivamente em `.env`** — nunca commitar
- URL do backend via `mobile/constants/Api.ts` (`API_URL`) — dev aponta para IP local, prod para Railway

## Backend (FastAPI)
**Entry point:** `backend/main.py`

Rotas:
- `GET /health` — healthcheck
- `GET /projetos` — lista projetos do Supabase
- `GET /projetos/{id}` — detalhe do projeto
- `POST /projetos/{id}/magic-link` — gera link WhatsApp para cliente
- `POST /projetos/{id}/gerar-documentos` — gera docs GPRF
- `POST /geo/inverso` — distância e azimute entre 2 pontos (UTM)
- `POST /geo/area` — área (m², ha) e perímetro de polígono UTM
- `POST /geo/converter/utm-geo` — UTM → Geográfico (SIRGAS 2000 / pyproj)
- `POST /geo/converter/geo-utm` — Geográfico → UTM (SIRGAS 2000 / pyproj)
- `POST /geo/intersecao` — interseção de duas semiretas (ponto + azimute)
- `POST /geo/distancia-ponto-linha` — distância perpendicular ponto-segmento
- `POST /geo/rotacao` — rotação de pontos UTM em torno de origem
- `POST /geo/subdivisao` — subdivisão de polígono por área alvo (bisseção)
- `POST /metrica/txt` — exportação para Métrica TOPO (recebe JSON, retorna TXT)

**Rotas de cálculo** definidas em `backend/routes/geo.py` e registradas em `main.py`.

**Deploy:** Railway — configurado via `backend/railway.json` e `backend/Procfile`

**Variáveis de ambiente necessárias:**
```
SUPABASE_URL=https://jrlrlsotwsiidglcbifo.supabase.co
SUPABASE_KEY=<service_key>
```

## Mobile (Expo)
**Navegação:** Expo Router com 4 tabs — Projetos, Cálculos, Mapa, Clientes

**Tabs ativas:**
- `Projetos` — lista + detalhe (`projeto/index.tsx`, `projeto/[id].tsx`)
- `Cálculos` — grade de ferramentas geodésicas (`calculos/index.tsx`)
- `Mapa` — Vista CAD + editor de perímetro (`mapa/[id].tsx`)

**Tabs placeholder:**
- `Clientes` — gestão de clientes

### Filosofia das Ferramentas de Cálculo

> **Todas as ferramentas da aba Cálculos existem para servir o ambiente CAD.**

Cada ferramenta é um auxílio ao trabalho topográfico dentro do editor de perímetro e da vista CAD. O fluxo esperado é:
- O topógrafo trabalha na **Vista CAD** (aba Mapa) editando vértices do perímetro
- Quando precisa de um cálculo auxiliar (azimute, área, irradiação, interseção etc.), acessa a **aba Cálculos**
- O resultado alimenta o trabalho de volta no CAD

Consequência direta: qualquer nova ferramenta deve ser projetada pensando em **como ela apoia a edição de vértices, perímetros e a vista CAD**. Ferramentas que calculam coordenadas de novos pontos (Irradiação, Interseção) devem, em versões futuras, permitir inserir o ponto resultante diretamente no perímetro ativo.

**Ferramentas implementadas** (`calculos/`):
| Ferramenta | Arquivo | Tipo | Endpoint |
|---|---|---|---|
| Inverso | `inverso.tsx` | backend | `POST /geo/inverso` |
| Área | `area.tsx` | backend | `POST /geo/area` |
| Conversão | `conversao.tsx` | backend | `POST /geo/converter/*` |
| Deflexão | `deflexao.tsx` | frontend | — |
| Interseção | `intersecao.tsx` | backend | `POST /geo/intersecao` |
| Dist. P-L | `distancia.tsx` | backend | `POST /geo/distancia-ponto-linha` |
| Rotação | `rotacao.tsx` | backend | `POST /geo/rotacao` |
| Média Pts | `media.tsx` | frontend | — |
| Irradiação | `irradiacao.tsx` | frontend | — |
| Subdivisão | `subdivisao.tsx` | backend | `POST /geo/subdivisao` |
| Normas INCRA | `rag.tsx` | backend | `POST /rag/consultar` |
| GNSS BT | `bluetooth.tsx` | nativo | — (Android only) |

**Componentes reutilizáveis:** `ProjetoCard`, `StatusBadge`, `FerramentaBtn`

**Constantes:** `Colors.ts` (paleta dark), `Api.ts` (URL do backend)

**EAS Build:**
- Perfil `preview` → APK Android para instalação direta
- Perfil `production` → AAB para Play Store
- `app.json` já configurado com `slug`, `android.package`, `extra.eas.projectId`, `owner`

**Build APK:**
```bash
cd mobile
npx eas-cli@latest build --platform android --profile preview
```

## Status dos Módulos
| Módulo | Status |
|---|---|
| Projetos (lista + detalhe) | ✅ Implementado |
| Cálculo Inverso | ✅ Implementado |
| Exportação Métrica TOPO | ✅ Implementado |
| Geração de Documentos GPRF | ✅ Implementado |
| Mapa / Vista CAD + editor de perímetro | ✅ Implementado |
| Ferramentas geodésicas (Área, Conversão, Deflexão, Interseção, Dist.P-L, Rotação, Média, Irradiação, Subdivisão) | ✅ Implementado |
| Versão web (browser) | ✅ Implementado |
| Gestão de Clientes | 🔜 Em breve |
| Integração Ferramentas → CAD (inserir ponto calculado direto no perímetro) | 🔜 Próxima fase |

## Convenções
- Tema: **dark only** — sempre usar `Colors.dark`
- Idioma do código: variáveis e funções em **português** (ex: `carregar`, `setProjetos`)
- Status dos projetos: `medicao`, `montagem`, `protocolado`, `aprovado`, `finalizado`
- Coordenadas: sistema UTM (Norte/Este em metros)
