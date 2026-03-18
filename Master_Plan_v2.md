Master Plan v2 — GeoAdmin Pro
=============================

Versão: 2.0 | Status: Em Desenvolvimento | Autor: Hugo (Desenrola Team)

Este documento substitui o Master_Plan.md original. Cada ponto fraco identificado foi
convertido em tasks concretas com critérios de aceitação. Nenhuma fase avança sem os
critérios da fase anterior estarem satisfeitos.

Decisão de Stack (Resolver Antes de Qualquer Código)
----------------------------------------------------

O projeto original foi planejado com Flutter e depois mudou para React Native sem
documentar o motivo. Esta decisão precisa ser feita agora, pois impacta tudo.

Recomendação resumida:
- Usar **React Native (Expo)** para o MVP (Fases 1 e 2).
- Se a renderização CAD travar ou a conexão GNSS não funcionar de forma confiável,
  migrar o módulo específico para Flutter — não o app inteiro.

Fase 0 — Validação (Antes de programar qualquer tela)
-----------------------------------------------------

Por que existe: erros de cálculo geodésico em produção podem invalidar escrituras no
INCRA. Esta fase cria a "muralha matemática" que protege todo o resto.

- **Task 0.1 — Gabarito de Testes Matemáticos**
  - Responsável: Hugo (revisão humana obrigatória) | Ferramenta: Python puro
  - Criar `backend/tests/gabarito_geodesico.py` com pares de entrada/saída
    calculados manualmente ou retirados de software certificado (Topograph, Métrica TOPO).
  - Critério de aceitação:
    - Cada função do backend deve passar em 100% dos casos do gabarito
      antes de ser integrada ao app.
    - Tolerância máxima:
      - ±0.001 m em distâncias
      - ±0.001" em ângulos

- **Task 0.2 — Decisão de Tecnologia GNSS**
  - Responsável: Hugo | Ferramenta: pesquisa + teste de hardware
  - Criar `docs/hardware/receptor_gnss.md` documentando:
    - Receptor GNSS utilizado.
    - Tipo de conexão (Bluetooth clássico ou BLE).
    - Sentenças NMEA padrão ou proprietárias.
    - Suporte a NTRIP ou rádio UHF.
  - Critério de aceitação:
    - Script Python standalone `backend/geo/nmea_parser.py` que lê um
      `.txt` com sentenças NMEA e extrai:
      latitude, longitude, altitude, HDOP, número de satélites e status de fix.

- **Task 0.3 — Configurar Supabase com PostGIS**
  - Responsável: Arquiteto de Dados | Ferramenta: Supabase + SQL
  - Usar migrations em `database/migrations/`.
  - Critério de aceitação:
    - Inserir e recuperar um ponto com coordenada real de Brasília e confirmar
      que o SRID 4674 está correto via `ST_SRID()`.

Fase 1 — Núcleo Técnico (MVP Real)
----------------------------------

Meta: um topógrafo consegue abrir o app, criar um projeto, digitar pontos
manualmente e ver o cálculo de Inverso e Área funcionando com precisão certificada.

- **Task 1.1 — Backend: API de Cálculos**
  - Agente: Engenheiro Geográfico | Ferramenta: FastAPI + Pyproj + Shapely
  - Endpoints obrigatórios:
    - `POST /geo/inverso` → `{x1,y1,x2,y2}` → `{distancia, azimute_decimal, azimute_graus_ms}`
    - `POST /geo/area` → `{pontos:[{x,y}]}` → `{area_m2, perimetro_m}`
    - `POST /geo/converter` → `{lat, lon, zona}` → `{este, norte, zona, srid}`
  - Regras:
    - 6 casas decimais em todas as saídas numéricas.
    - Proibido `try: except: pass`.
    - Rodar `shape.is_valid` antes de qualquer cálculo de área.
    - Cada função deve ter o gabarito da Task 0.1 como teste automatizado (`pytest`).
  - Critério de aceitação:
    - `pytest backend/tests/` com 100% de aprovação no gabarito geodésico.

- **Task 1.2 — Mobile: Estrutura de Abas e Navegação**
  - Agente: Arquiteto UI/UX | Ferramenta: React Native + Expo Router
  - Estrutura em `mobile/app/(tabs)/`:
    - `projeto.tsx` (lista de projetos)
    - `mapa.tsx`
    - `calculos.tsx` (grade 3x6 de ferramentas)
    - `clientes.tsx`
  - Critério de aceitação:
    - App abre via Expo Go, navega entre as 4 abas sem crash.
    - Grade de ferramentas com ícones e textos legíveis sob luz solar direta.

- **Task 1.3 — Mobile: Tela de Cálculo Inverso (integrada ao backend)**
  - Agentes: Arquiteto UI/UX + Engenheiro Geográfico
  - Campos:
    - Nome P1, Norte P1, Este P1
    - Nome P2, Norte P2, Este P2
    - Botão "Calcular" → chama `POST /geo/inverso`
    - Botão "Salvar no Projeto" → salva no Supabase.
  - Critério de aceitação:
    - Calcular o Caso 1 do gabarito (Task 0.1) via app e obter o mesmo resultado.
    - Testar sem internet (erro amigável, sem crash).

- **Task 1.4 — Modo Offline: Fila de Sincronização**
  - Agente: Arquiteto de Dados | Ferramenta: SQLite/WatermelonDB
  - Fluxo:
    - Coletar ponto → salvar local (`pendente_sync: true`).
    - Recuperar internet → enviar para Supabase → marcar `synced: true`.
    - Mostrar ícone de nuvem com contador de itens pendentes.
  - Critério de aceitação:
    - Coletar 10 pontos em modo avião e, ao ligar o Wi-Fi, todos chegarem ao Supabase
      sem duplicatas.

Fase 2 — Campo (Conexão GNSS Real)
----------------------------------

Pré-requisito: Task 0.2 concluída e receptor GNSS físico disponível.

- **Task 2.1 — Módulo GNSS: Leitura Bluetooth**
  - Agente: Engenheiro Geográfico
  - Ferramenta: `react-native-ble-plx` ou `react-native-bluetooth-serial`
  - Critério de aceitação:
    - Com receptor fixo em ponto conhecido, o app exibe coordenadas com erro < 3 cm
      (RTK fix) ou dentro da precisão do equipamento.

- **Task 2.2 — Vista CAD Simplificada**
  - Agente: Arquiteto UI/UX
  - Ferramenta: `react-native-svg` ou `react-native-canvas`
  - Funcionalidades mínimas:
    - Plotar pontos coletados como círculos com nome.
    - Ligar pontos em sequência formando linhas.
    - Zoom por pinça e pan por toque.
    - Exibir coordenada ao tocar em um ponto.
    - Exportar a vista como PNG.
  - Critério de aceitação:
    - Plotar vértices de área conhecida; polígono fecha corretamente; proporção visual
      condiz com o terreno real.

- **Task 2.3 — Importação/Exportação de Dados**
  - Agente: Mestre da Automação
  - Ferramentas: `ezdxf` (Python) + parser CSV
  - Formatos:
    - Entrada: CSV (Nome, Norte, Este, Cota), TXT (Topograph).
    - Saída: CSV, DXF (Métrica TOPO/AutoCAD), KML (Google Earth).
  - Critério de aceitação:
    - Exportar pontos de projeto real para DXF, abrir no Métrica TOPO e confirmar que
      coordenadas batem com as do app.

Fase 3 — Administrativo e Cliente
---------------------------------

Pré-requisito: Fases 0, 1 e 2 concluídas e app usado em pelo menos 1 levantamento real.

- **Task 3.1 — CRM de Processos**
  - Agentes: Arquiteto de Dados + UI/UX
  - Funcionalidades:
    - Cadastro de cliente com CPF/CNPJ, telefone, e-mail e documentos.
    - Vinculação cliente → projeto → processo.
    - Status com datas: Medição → Montagem → Protocolado no INCRA → Aprovado → Escritura.
    - Campo de observações por etapa.
    - Alerta de prazo (ex.: processo > 90 dias sem atualização).
  - Critério de aceitação:
    - Registrar um processo real do início ao fim, com upload do PDF da matrícula.

- **Task 3.2 — Portal do Cliente (Magic Link)**
  - Agentes: Arquiteto de Dados + UI/UX
  - Ferramenta: Supabase Auth + React Native Web ou PWA
  - Critério de aceitação:
    - Cliente real consegue abrir o link, ver status correto do processo e baixar o PDF
      sem pedir ajuda.

- **Task 3.3 — Geração de Memorial Descritivo**
  - Agente: Mestre da Automação + Agente RAG
  - Ferramentas: Jinja2 + ReportLab (Python)
  - Conteúdo mínimo:
    - Cabeçalho com dados do proprietário e do imóvel.
    - Tabela de vértices com Norte, Este, Cota e Descrição.
    - Descrição das confrontações (gerada automaticamente).
    - Área total e perímetro calculados pela API.
    - Rodapé com nome e CREA do responsável técnico.
  - Critério de aceitação:
    - Memorial de projeto real validado pelo Agente RAG contra Norma Técnica do INCRA.

Agente RAG — Configuração Obrigatória
-------------------------------------

- Documentos a indexar em `docs/normas/`:
  - Norma Técnica de Georreferenciamento de Imóveis Rurais (3ª ed.) — INCRA.
  - Manual Técnico de Limites e Divisas — INCRA.
  - Lei 13.465/2017 — Planalto.
  - Instrução Normativa INCRA nº 77/2013 — INCRA.
  - Manual do SIGEF — INCRA.

Critérios de Avanço entre Fases
-------------------------------

- Fase 0 → Fase 1:
  - Gabarito matemático criado e aprovado por humano.
- Fase 1 → Fase 2:
  - App funciona offline.
  - Cálculos passam 100% no `pytest`.
  - App testado em campo (celular físico).
- Fase 2 → Fase 3:
  - Pelo menos 1 levantamento real completo feito com o app.
  - Exportação DXF validada no Métrica TOPO.
- Fase 3 → Produção:
  - Memorial gerado passou na validação do Agente RAG.
  - Portal do cliente testado por cliente real.

