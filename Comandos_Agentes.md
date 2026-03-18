# GeoAdmin Pro — Tasks por Agente

Este arquivo lista **tasks sugeridas** para cada agente, alinhadas ao **Master Plan v2**.
Use estas frases diretamente no chat do Cursor/Windsurf, ajustando detalhes do contexto
quando necessário.

---

## 1. Arquiteto UI/UX (mobile React Native)

### Fase 1 — Núcleo Técnico

- **Task 1.2 — Estrutura de abas e navegação**
  - Prompt:
    - *"Agente UI/UX, crie o projeto Expo React Native para o app GeoAdmin Pro.
       Tema: dark mode + laranja (#EF9F27).
       4 abas: Projeto | Mapa | Cálculos | Clientes usando Expo Router (tabs).
       Use as telas esqueleto em `mobile/app/(tabs)/` como base."*

- **Task — Grade de ferramentas da aba Cálculos (3x6)**
  - Prompt:
    - *"Agente UI/UX, na tela `mobile/app/(tabs)/calculos.tsx`, implemente uma grade
       3x6 de botões grandes com ícones e textos inspirados nas imagens de
       `docs/referencias/` (LandStar). Garanta boa leitura sob luz solar
       direta e uso com luvas."*

- **Task — Tela de Cálculo Inverso (frontend)**
  - Prompt:
    - *"Agente UI/UX, crie a tela de Cálculo Inverso em `mobile/app/calculos/inverso.tsx`
       com campos: Nome P1, Norte P1, Este P1, Nome P2, Norte P2, Este P2,
       botão 'Calcular' chamando o backend `/geo/inverso` e um cartão grande
       exibindo Distância e Azimute."*

- **Task — Estado de erro e offline**
  - Prompt:
    - *"Agente UI/UX, adicione estados visuais de erro e modo offline às telas de cálculo,
       exibindo mensagens amigáveis com códigos de erro vindos do backend
       sem travar o app."*

### Fases 2 e 3 (esboço)

- **Tela de coleta GNSS em tempo real**
  - Prompt:
    - *"Agente UI/UX, desenhe a tela de coleta GNSS em tempo real, mostrando precisão
       (HDOP), número de satélites e um grande botão de 'Registrar ponto'
       adequado para uso em campo."*

- **Módulo CRM de processos**
  - Prompt:
    - *"Agente UI/UX, crie o fluxo de telas de CRM de processos na aba Clientes,
       permitindo visualizar status Medição → Montagem → Protocolado → Aprovado,
       com datas e observações por etapa."*

---

## 2. Engenheiro Geográfico (backend geodésico)

### Fase 0 — Gabarito

- **Task 0.1 — Gabarito de testes matemáticos**
  - Prompt:
    - *"Agente Geográfico, crie `backend/tests/gabarito_geodesico.py` com casos de teste
       para Inverso, Área (Gauss) e conversão SIRGAS 2000 → UTM Zona 23S
       usando os valores de referência do Master Plan v2."*

### Fase 1 — API de cálculos

- **Task 1.1 — Endpoint `/geo/inverso` com precisão certificada**
  - Prompt:
    - *"Agente Geográfico, refine a implementação do endpoint POST `/geo/inverso` em
       `backend/main.py` usando pyproj/shapely quando necessário, SRID 4674 (SIRGAS 2000),
       e garantindo 6 casas decimais em todas as saídas. Use os casos de
       teste do gabarito para validar com pytest."*

- **Task — Endpoint `/geo/area`**
  - Prompt:
    - *"Agente Geográfico, implemente o endpoint POST `/geo/area` em `backend/main.py`
       recebendo {pontos:[{x,y}]}, calculando área em m² e perímetro em metros
       com 6 casas decimais. Use Shapely, valide `shape.is_valid` e crie
       testes em `backend/tests/test_area.py` baseados no gabarito."*

- **Task — Endpoint `/geo/converter`**
  - Prompt:
    - *"Agente Geográfico, implemente o endpoint POST `/geo/converter` em `backend/main.py`
       recebendo {lat, lon, zona} e retornando {este, norte, zona, srid}
       usando pyproj para SIRGAS 2000 UTM Zona 23S (SRID 4674). Testes em
       `backend/tests/test_converter.py` com tolerância de 0.001m."*

---

## 3. Mestre da Automação (DXF, KML, memorial)

### Fase 2 — Importação e exportação

- **Task 2.3 — Importador CSV/TXT**
  - Prompt:
    - *"Agente Automação, crie `backend/geo/importadores.py` com funções para importar
       pontos a partir de CSV (Nome, Norte, Este, Cota) e TXT no formato
       Topograph, retornando listas de objetos Python prontos para salvar
       no banco."*

- **Task 2.3 — Exportador DXF/KML**
  - Prompt:
    - *"Agente Automação, crie `backend/geo/exportadores.py` usando ezdxf para gerar
       DXF compatível com Métrica TOPO e KML para Google Earth a partir
       de uma lista de pontos (Nome, Norte, Este, Cota)."*

### Fase 3 — Memorial Descritivo

- **Task 3.3 — Geração de memorial descritivo em PDF**
  - Prompt:
    - *"Agente Automação, crie um gerador de memorial descritivo em
       `backend/geo/memorial.py` usando Jinja2 + ReportLab. O memorial deve ter
       cabeçalho do imóvel, tabela de vértices, confrontações, área e
       perímetro, e rodapé com nome/CREA do responsável."*

---

## 4. Arquiteto de Dados (Supabase/PostGIS, RLS)

### Fase 0 — Configuração inicial

- **Task 0.3 — Estrutura base no Supabase**
  - Prompt:
    - *"Agente Dados, revise a migration `database/migrations/001_base_estrutura.sql`
       garantindo que as tabelas projetos, pontos e clientes estão corretas
       para uso com Supabase/PostGIS (SRID 4674) e adicione comentários SQL
       explicando cada coluna crítica."*

### Fase 1 — Modo offline e sync

- **Task — Modelo de sync local → Supabase**
  - Prompt:
    - *"Agente Dados, defina o modelo de dados para fila de sincronização de pontos
       (modo offline) e crie uma migration SQL em `database/migrations/002_sync_offline.sql`
       com tabela de pendências e campos necessários para evitar duplicatas."*

### Fase 3 — Segurança e portal do cliente

- **Task — Políticas de RLS**
  - Prompt:
    - *"Agente Dados, crie as políticas de Row Level Security (RLS) para que cada usuário
       autenticado no Supabase veja apenas seus clientes, projetos e pontos.
       Documente em `docs/rls_supabase.md` como as policies funcionam."*

---

## 5. Revisor (Auditor)

### Revisão contínua

- **Task — Revisão da API de área**
  - Prompt:
    - *"Agente Auditor, revise o endpoint `/geo/area` e seus testes para garantir que:
       (1) não há try/except vazio,
       (2) todos os erros retornam JSON com {erro, codigo},
       (3) os resultados estão dentro da tolerância definida no gabarito."*

- **Task — Auditoria de segurança do backend**
  - Prompt:
    - *"Agente Auditor, faça uma revisão de segurança em `backend/main.py` e rotas
       associadas, verificando tratamento de exceções, vazamento de stack trace
       e proteção básica contra inputs inválidos."*

### Conformidade legal

- **Task — Conformidade com Lei 13.465/2017 (visão geral)**
  - Prompt:
    - *"Agente Auditor, liste os pontos do sistema que podem impactar a conformidade com
       a Lei 13.465/2017 e indique quais partes do código precisam de atenção
       especial (ex.: cálculos de área, memorial descritivo, armazenamento
       de documentos)."*

---

## 6. Agente RAG (INCRA, SIGEF, normas)

> Importante: este agente só funciona bem quando os documentos oficiais
> estiverem salvos em `docs/normas/` (Norma Técnica, Manuais, Leis etc.).

- **Task — Configurar base de conhecimento**
  - Prompt:
    - *"Agente RAG, considerando os PDFs em `docs/normas/`, descreva como o Cursor deve
       indexar esses documentos para que você consiga validar memoriais
       descritivos e cálculos segundo as normas do INCRA."*

- **Task — Validação de memorial descritivo**
  - Prompt:
    - *"Agente RAG, valide o texto deste memorial descritivo gerado pelo sistema
       comparando com a Norma Técnica de Georreferenciamento de Imóveis Rurais
       (3ª ed.) e a Instrução Normativa INCRA nº 77/2013. Liste os pontos que
       precisam ser ajustados."*

- **Task — Checklist antes de envio ao SIGEF**
  - Prompt:
    - *"Agente RAG, crie um checklist de validação para o envio de um levantamento
       ao SIGEF, baseado nas normas disponíveis em `docs/normas/`, para ser
       usado pelo topógrafo antes de protocolar o processo."*

