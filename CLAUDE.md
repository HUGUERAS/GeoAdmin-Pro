# GeoAdmin Pro — Contexto para Claude Code

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
- `POST /geo/inverso` — calcula distância e azimute entre 2 pontos (UTM)
- `POST /metrica/txt` — exportação para Métrica TOPO (recebe JSON, retorna TXT)

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
- `Cálculos` — grade de ferramentas; só `Inverso` implementado (`calculos/inverso.tsx`)

**Tabs placeholder (Fase 2):**
- `Mapa` — Vista CAD
- `Clientes` — gestão de clientes

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
| Mapa / Vista CAD | 🔜 Fase 2 |
| Gestão de Clientes | 🔜 Em breve |
| Cálculos adicionais (Área, Subdivisão…) | 🔜 Em breve |

## Convenções
- Tema: **dark only** — sempre usar `Colors.dark`
- Idioma do código: variáveis e funções em **português** (ex: `carregar`, `setProjetos`)
- Status dos projetos: `medicao`, `montagem`, `protocolado`, `aprovado`, `finalizado`
- Coordenadas: sistema UTM (Norte/Este em metros)
