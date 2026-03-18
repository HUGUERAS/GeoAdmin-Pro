# GeoAdmin Pro — Contexto para todas as sessões

Use este arquivo em novas conversas: abra ou referencie com `@CONTEXTO_PROJETO.md` para o assistente retomar o contexto rapidamente.

---

## Quem

- **Autor/Responsável:** Hugo (Desenrola Team)
- **Preferência:** Respostas sempre em **português**.

---

## O que é o projeto

- **GeoAdmin Pro:** sistema para topografia, georreferenciamento e gestão de projetos rurais (INCRA, SIGEF, memoriais).
- **Objetivo central:** uma única fonte de dados — digitar uma vez no app/backend e não repetir no Métrica TOPO, planilhas ou outros sistemas.

---

## Stack

- **Mobile:** React Native (Expo), 4 abas: Projeto | Mapa | Cálculos | Clientes. Tema dark + laranja `#EF9F27`.
- **Backend:** FastAPI (Python), em `C:\Users\User\Documents\GeoAdmin-Pro\backend\`.
- **Banco:** Supabase (Postgres + PostGIS). Projeto: `https://jrlrlsotwsiidglcbifo.supabase.co`.
- **Integração Métrica TOPO:** exportação de pontos em TXT (e depois CSV, DXF, KML) no formato que o Métrica importa.

---

## Estrutura do backend (resumo)

```
backend/
  main.py              ← app FastAPI, get_supabase(), /health, /geo/inverso
  .env                 ← SUPABASE_URL, SUPABASE_KEY (nunca commitar)
  .env.example         ← modelo sem valores reais
  requirements.txt    ← fastapi, uvicorn, supabase, python-dotenv, ezdxf
  integracoes/
    integracao_metrica.py   ← geradores TXT, CSV, DXF, KML (usa views do Supabase)
  routes/
    exportacao.py          ← GET/POST /projetos/{id}/metrica/... (depende do Supabase)
    metrica_simples.py      ← POST /metrica/txt (JSON → TXT, sem banco)
```

- **Rodar servidor:** `cd backend` e `python -m uvicorn main:app --reload`. API em `http://127.0.0.1:8000`.
- **Docs interativos:** `http://127.0.0.1:8000/docs`.

---

## Supabase

- **URL do projeto:** `https://jrlrlsotwsiidglcbifo.supabase.co`.
- **Chave:** usar a **anon public** (Settings → API no Dashboard). Colocar em `backend/.env` como `SUPABASE_KEY`.
- **Nunca** commitar `.env`; está em `backend/.gitignore`. No GitHub usar apenas Secrets para CI/deploy.
- **Views esperadas** pela integração completa: `vw_projetos_completo`, `vw_pontos_utm`. Se não existirem, o endpoint `GET /projetos/{id}/metrica/txt` pode retornar 500.

---

## Integração Métrica TOPO (como ficou)

- **Modo simples (funciona sem Supabase):**  
  `POST /metrica/txt` — envia JSON com `projeto_nome`, `numero_job`, `zona_utm`, `pontos[]`. Resposta: arquivo .txt pronto para importar no Métrica.
- **Modo completo (com Supabase):**  
  `GET /projetos/{id}/metrica/txt` (e preparar, csv, dxf, kml) — lê dados das views e gera os arquivos. Só funciona com banco e views configurados.
- **Formato TXT:** colunas Nome, Norte, Este, Cota, Código; cabeçalho com projeto/job; gerado por GeoAdmin Pro.

---

## Documentos de referência no repo

- `Master_Plan_v2.md` — fases 0 a 3, critérios de aceitação, tarefas por agente.
- `.cursorrules` — 6 agentes (UI/UX, Geográfico, Automação, Dados, Auditor, RAG) e regras de trabalho.
- `Comandos_Agentes.md` — prompts prontos por agente.
- `Fluxo_Agentes_Fases.md` — ordem de execução dos prompts por fase.

---

## Decisões importantes

- Fonte única de dados: GeoAdmin Pro; Métrica consome arquivos gerados pelo backend.
- Endpoint simples primeiro: `POST /metrica/txt` com JSON; depois conectar Supabase no GET por projeto.
- Favicon 404 na API é normal; ignorar. Erro 500 em `/projetos/.../metrica/txt` em geral é Supabase/views ou .env.

---

*Última atualização: contexto da sessão de março 2026. Ajuste este arquivo quando houver mudanças relevantes.*
