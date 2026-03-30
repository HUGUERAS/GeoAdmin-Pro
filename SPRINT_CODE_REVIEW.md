# Sprint Code Review — Distribuição por Agentes

**Origem:** Code Review completo do GeoAdmin-Pro (26/03/2026)
**Objetivo:** Resolver todos os achados do review distribuindo tarefas pelos 6 agentes definidos no `AGENTS.md`
**Estimativa total:** ~3 a 5 sessões de trabalho focado

---

## Ordem de Execução (dependências entre agentes)

```
FASE 1 — Fundação (sem dependências, podem rodar em paralelo)
├── Agente 4: Arquiteto de Dados   → RLS, auth, .gitignore
├── Agente 5: Revisor/Auditor      → CORS, sanitização, validação ZIP
│
FASE 2 — Backend (depende da Fase 1)
├── Agente 2: Engenheiro Geográfico → corretude de cálculos, testes
├── Agente 3: Mestre da Automação   → performance de exportação, bridge
│
FASE 3 — Frontend (depende da Fase 2 para auth)
├── Agente 1: Arquiteto UI/UX       → timeout, erro handling, bluetooth
│
FASE 4 — Validação (depende de todas as anteriores)
├── Agente 6: Agente RAG/INCRA      → verificar que nada quebrou nos fluxos legais
```

---

## FASE 1 — Fundação de Segurança

### Agente 4: Arquiteto de Dados
> **Prompt:** "Agente Dados, resolva as vulnerabilidades de segurança na camada de dados."

| # | Task | Arquivo(s) | Severidade | Prompt sugerido |
|---|------|-----------|------------|-----------------|
| 4.1 | Adicionar `backend/.env` e `mobile/credentials.json` ao `.gitignore` | `.gitignore` | 🔴 Crítico | "Agente Dados, adicione backend/.env e mobile/credentials.json ao .gitignore. Verifique que não há outras credenciais rastreadas no repo." |
| 4.2 | Criar middleware de autenticação JWT via Supabase Auth | `backend/middleware/auth.py` (novo) | 🔴 Crítico | "Agente Dados, crie um middleware FastAPI `Depends(verificar_token)` que valida o JWT do Supabase Auth. O token vem no header `Authorization: Bearer <token>`. Use a lib `jose` ou `supabase.auth.get_user()`. Aplique em TODOS os routers exceto `/health`." |
| 4.3 | Revisar políticas RLS — `topografo_acesso_total` é permissiva demais | `infra/supabase/migrations/` | 🟠 Alto | "Agente Dados, revise as policies RLS. A policy `topografo_acesso_total` deve filtrar por `auth.uid()` para que cada topógrafo veja apenas seus projetos. Crie uma nova migration." |
| 4.4 | Separar `anon key` (mobile) de `service_role` (backend) | `.env`, `mobile/constants/` | 🟠 Alto | "Agente Dados, garanta que o mobile use apenas a `anon_key` do Supabase e o backend use `service_role`. Documente a diferença no CLAUDE.md." |

**Critério de conclusão:** Nenhuma credencial no git, auth middleware funcionando, RLS restritiva.

---

### Agente 5: Revisor / Auditor
> **Prompt:** "Agente Auditor, feche as vulnerabilidades de segurança no código."

| # | Task | Arquivo(s) | Severidade | Prompt sugerido |
|---|------|-----------|------------|-----------------|
| 5.1 | Restringir CORS para domínios reais | `backend/main.py` L39-44 | 🔴 Crítico | "Agente Auditor, substitua `allow_origins=['*']` por uma lista de domínios permitidos: `['https://geoadmin-pro.vercel.app', 'http://localhost:8081', 'http://localhost:19006']`. Use variável de ambiente `ALLOWED_ORIGINS` para prod vs dev." |
| 5.2 | Corrigir path traversal no ZIP do bridge | `bridge/geoadmin_bridge.py` L217 | 🔴 Crítico | "Agente Auditor, antes do `extractall()` em `extrair_pacote`, valide que nenhum membro do ZIP contém `..` ou caminhos absolutos. Rejeite o pacote inteiro se encontrar." |
| 5.3 | Sanitizar prompt do RAG | `backend/routes/rag.py` | 🟠 Alto | "Agente Auditor, adicione sanitização no input do usuário antes de enviar à API OpenAI no endpoint `/rag/consultar`. Limite o tamanho a 500 caracteres e remova caracteres de controle." |
| 5.4 | Prevenir XXE no parser KML | `backend/integracoes/referencia_cliente.py` | 🟠 Alto | "Agente Auditor, use `defusedxml.ElementTree` em vez de `xml.etree.ElementTree` para parsear KML. Adicione `defusedxml` ao requirements.txt." |
| 5.5 | Limitar tamanho de upload | `backend/routes/importar.py` | 🟠 Alto | "Agente Auditor, adicione limite de 10MB no upload de arquivos em `/importar`. Use `python-multipart` com validação de `Content-Length`." |
| 5.6 | Fixar versões no requirements.txt | `backend/requirements.txt` | 🟡 Médio | "Agente Auditor, fixe todas as versões de dependências com `==` no requirements.txt para evitar supply chain attacks. Rode `pip freeze` para capturar as versões atuais." |

**Critério de conclusão:** Nenhum achado 🔴 restante, `bandit` (SAST) sem warnings críticos.

---

## FASE 2 — Corretude e Performance do Backend

### Agente 2: Engenheiro Geográfico
> **Prompt:** "Agente Geográfico, corrija os problemas de corretude nos cálculos."

| # | Task | Arquivo(s) | Severidade | Prompt sugerido |
|---|------|-----------|------------|-----------------|
| 2.1 | Remover `calcular_inverso` duplicado do main.py | `backend/main.py` L63-160 | 🟡 Médio | "Agente Geográfico, o endpoint `/geo/inverso` está duplicado: existe no `main.py` (implementação simplificada) e no `routes/geo.py` (implementação correta com pyproj). Remova a versão do main.py — a do geo.py já é registrada via router." |
| 2.2 | Validar polígonos degenerados em `/geo/subdivisao` | `backend/routes/geo.py` | 🟡 Médio | "Agente Geográfico, adicione validação no endpoint de subdivisão: rejeitar polígonos com área zero, auto-intersecção ou menos de 3 vértices. Use `shapely.validation.make_valid()` se possível." |
| 2.3 | Substituir `datetime.utcnow()` deprecado | `backend/routes/documentos.py` | 🟡 Médio | "Agente Geográfico, substitua todas as ocorrências de `datetime.utcnow()` por `datetime.now(timezone.utc)` no backend. O utcnow está deprecado desde Python 3.12." |
| 2.4 | Logar erros de correção geóide em vez de `except: pass` | `backend/routes/pontos.py` | 🟡 Médio | "Agente Geográfico, na função de correção geoidal, o `except Exception: pass` está engolindo erros. Adicione `logging.warning()` com o id do ponto e a exceção. Erros de geóide não devem impedir o salvamento, mas precisam ser rastreáveis." |
| 2.5 | Adicionar testes para os edge cases encontrados | `backend/tests/` | 🟡 Médio | "Agente Geográfico, crie testes para: polígono com área zero na subdivisão, coordenadas nos limites de fuso UTM na conversão, e pontos coincidentes no inverso (distância zero)." |

**Critério de conclusão:** `pytest` 100% verde, nenhum `except: pass` nos cálculos.

---

### Agente 3: Mestre da Automação
> **Prompt:** "Agente Automação, resolva os gargalos de performance nas exportações e no bridge."

| # | Task | Arquivo(s) | Severidade | Prompt sugerido |
|---|------|-----------|------------|-----------------|
| 3.1 | Adicionar paginação em `/projetos` e `/clientes` | `backend/routes/projetos.py`, `clientes.py` | 🟠 Alto | "Agente Automação, adicione parâmetros `?limit=50&offset=0` nos endpoints de listagem de projetos e clientes. O Supabase suporta `.range(offset, offset+limit-1)`. Atualize o mobile para carregar com scroll infinito." |
| 3.2 | Corrigir N+1 na sincronização de pontos | `backend/routes/pontos.py` | 🟠 Alto | "Agente Automação, a função `sincronizar_pontos` faz 1 query por ponto para checar duplicatas. Substitua por uma query batch: busque todos os `local_id` existentes com `IN (...)` em uma única chamada, depois faça o insert em batch." |
| 3.3 | Consolidar queries do perímetro ativo | `backend/routes/perimetros.py` | 🟡 Médio | "Agente Automação, `buscar_perimetro_ativo` faz 3 queries sequenciais (uma por tipo de geometria). Consolide em uma única query com `OR` e `ORDER BY tipo`." |
| 3.4 | Corrigir log O(n²) no bridge | `bridge/geoadmin_bridge.py` L115-116 | 🟡 Médio | "Agente Automação, `_registrar_log` lê o arquivo inteiro para adicionar uma linha. Substitua por `open(path, 'a', encoding='utf-8')` com modo append." |
| 3.5 | Refatorar `routes/exportacao.py` (535 linhas) | `backend/routes/exportacao.py` | 🟡 Médio | "Agente Automação, divida exportacao.py em módulos: `exportacao_dxf.py`, `exportacao_kml.py`, `exportacao_geojson.py`, `exportacao_zip.py`. Mantenha o router principal importando de cada um." |
| 3.6 | Refatorar `routes/clientes.py` (853 linhas) | `backend/routes/clientes.py` | 🟡 Médio | "Agente Automação, divida clientes.py em: `clientes.py` (CRUD), `confrontantes.py` (operações de confrontantes), `resumos.py` (geração de resumos)." |

**Critério de conclusão:** Nenhuma query N+1, tempos de resposta < 500ms para listagens, arquivos < 300 linhas.

---

## FASE 3 — Mobile

### Agente 1: Arquiteto UI/UX
> **Prompt:** "Agente UI/UX, melhore a robustez e a experiência offline do app."

| # | Task | Arquivo(s) | Severidade | Prompt sugerido |
|---|------|-----------|------------|-----------------|
| 1.1 | Adicionar timeout nas chamadas fetch | `mobile/lib/api.ts` | 🟡 Médio | "Agente UI/UX, adicione timeout de 15 segundos em todas as chamadas fetch do api.ts usando `AbortController`. Mostre mensagem amigável 'Sem conexão com o servidor' ao estourar." |
| 1.2 | Adicionar auth header no api.ts | `mobile/lib/api.ts` | 🟠 Alto | "Agente UI/UX, após o Agente Dados criar o middleware de auth, adicione o header `Authorization: Bearer <token>` em todas as chamadas do api.ts. O token vem do `supabase.auth.session()`." |
| 1.3 | Proteger JSON.parse no cache SQLite | `mobile/lib/db.ts` | 🟡 Médio | "Agente UI/UX, envolva todos os `JSON.parse()` em `getCachedProjetos` e `getCachedProjetoDetalhe` com try/catch. Se o JSON estiver corrompido, retorne `[]` ou `null` e delete o registro corrompido." |
| 1.4 | Corrigir race condition no bluetooth | `mobile/lib/bluetooth.ts` | 🟡 Médio | "Agente UI/UX, adicione um guard no `iniciarLeitura`: se `_leituraAtiva` já for true, retorne sem fazer nada. Considere encapsular o estado global em uma classe `BluetoothManager` para facilitar testes." |
| 1.5 | Agrupar updates de sync em transação | `mobile/lib/sync.ts` | 🟡 Médio | "Agente UI/UX, no `sincronizar`, ao invés de chamar `marcarSincronizado` em loop para cada ponto, agrupe tudo em uma transação SQLite: `db.execAsync('BEGIN'); ... db.execAsync('COMMIT');`" |
| 1.6 | Extrair tipo `PontoLocal` para arquivo compartilhado | `mobile/lib/db.ts`, `db.web.ts` | 🟢 Baixo | "Agente UI/UX, extraia a interface `PontoLocal` e `SyncStatus` para `mobile/types/ponto.ts`. Importe em db.ts e db.web.ts para eliminar a duplicação." |

**Critério de conclusão:** App não trava em condições de rede ruim, auth integrado, sem duplicação de tipos.

---

## FASE 4 — Validação Final

### Agente 6: RAG / INCRA
> **Prompt:** "Agente RAG, valide que as alterações não quebraram os fluxos de regularização."

| # | Task | Arquivo(s) | Severidade | Prompt sugerido |
|---|------|-----------|------------|-----------------|
| 6.1 | Testar fluxo completo de geração de documentos | Todos | 🟡 Médio | "Agente RAG, execute o fluxo completo: criar projeto → adicionar pontos → gerar documentos GPRF → exportar para Métrica. Verifique que o auth novo não bloqueia o fluxo e que os documentos saem corretos." |
| 6.2 | Verificar que o memorial descritivo está correto | `backend/integracoes/gerador_documentos.py` | 🟡 Médio | "Agente RAG, verifique que a função `_preencher()` não faz substituições parciais quando um valor contém texto de outro placeholder. Teste com nomes de proprietário que contenham strings como 'NOME' ou 'CPF'." |

**Critério de conclusão:** Fluxo de regularização ponta-a-ponta funcionando com autenticação.

---

## Resumo Quantitativo

| Agente | Tasks | Críticas | Altas | Médias | Baixas |
|--------|-------|----------|-------|--------|--------|
| 4. Arquiteto de Dados | 4 | 2 | 2 | 0 | 0 |
| 5. Revisor/Auditor | 6 | 2 | 3 | 1 | 0 |
| 2. Eng. Geográfico | 5 | 0 | 0 | 5 | 0 |
| 3. Mestre Automação | 6 | 0 | 2 | 4 | 0 |
| 1. Arquiteto UI/UX | 6 | 0 | 1 | 4 | 1 |
| 6. RAG/INCRA | 2 | 0 | 0 | 2 | 0 |
| **Total** | **29** | **4** | **8** | **16** | **1** |

---

## Como Usar Este Documento

Para cada task, copie o **prompt sugerido** e passe ao agente correspondente (via Claude Code, Cursor, ou similar). Siga a ordem das fases — a Fase 1 é pré-requisito das demais.

Exemplo de prompt completo para iniciar:

```
Agente Auditor, substitua allow_origins=['*'] por uma lista de domínios
permitidos no backend/main.py linha 39-44. Use:
allow_origins=['https://geoadmin-pro.vercel.app', 'http://localhost:8081', 'http://localhost:19006']
Torne configurável via variável de ambiente ALLOWED_ORIGINS (separado por vírgula).
```


---

## Rodada 30/03/2026 — Soluções propostas para próximos pontos

### Pontos já corrigidos nesta rodada
- Bandeja cartográfica agora prioriza **Supabase Storage** e só usa disco local como contingência.
- Magic link legado deixou de escolher “o projeto mais recente” quando há ambiguidade; agora exige **novo link individual**.
- Reenvio do formulário do cliente passou a **sincronizar confrontantes**, em vez de duplicar registros.
- Criação de projeto ganhou **reversão compensatória** para evitar projeto parcial salvo com erro na resposta.

### Próximos pontos recomendados
1. **Migrar arquivos cartográficos antigos do disco local para o Supabase Storage**
   - Criar script de migração que leia `arquivos_projeto.storage_path` local, envie o binário ao bucket e atualize o registro para `supabase://bucket/path`.
   - Isso fecha a janela entre as versões antigas e a persistência nova.

2. **Encerrar o legado de token em `clientes.magic_link_token`**
   - O caminho mais seguro é migrar tudo para `projeto_clientes.magic_link_token`.
   - Depois da migração, o token legado pode virar compatibilidade temporária com prazo de expiração operacional.

3. **Criar trilha de auditoria para promoção de arquivo a base oficial**
   - Tabela sugerida: `eventos_cartograficos`.
   - Guardar: quem promoveu, quando, qual arquivo, de qual classificação saiu e para qual uso oficial foi promovido.
   - Isso reforça a regra de ouro: nenhum arquivo altera perímetro oficial sem ação explícita do topógrafo.

4. **Separar copropriedade por área de participação no projeto**
   - Hoje `projeto_clientes` resolve bem participantes do projeto.
   - Próximo passo natural: tabela `area_clientes` para representar coproprietários reais em áreas específicas sem sobrecarregar `areas_projeto`.

5. **APP_URL pública no ambiente publicado**
   - Sem isso, o magic link continua saindo com URL local em alguns ambientes.
   - Tratar como checklist obrigatório de deploy.
