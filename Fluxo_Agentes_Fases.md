# GeoAdmin Pro — Fluxo Automático por Agente e Fase

Objetivo: permitir que, **se você for executando os prompts em ordem**, os agentes
consigam levar o projeto **da Fase 0 até a Fase 3** sem ficar perdido em o que vem depois.

Abaixo está o fluxo organizado: **ordem recomendada de execução dos prompts**
por fase, já indicando **qual agente** chamar e **quando parar**.

---

## Fase 0 — Validação (antes de telas e app)

1. **Engenheiro Geográfico — Gabarito**
   - Prompt:
     - *"Agente Geográfico, use o arquivo `Master_Plan_v2.md` e crie
        `backend/tests/gabarito_geodesico.py` com todos os casos de teste
        descritos na Fase 0 (Inverso, Área, Conversão), já em formato de
        testes pytest."*

2. **Arquiteto de Dados — Supabase/PostGIS**
   - Prompt:
     - *"Agente Dados, revise e complete `database/migrations/001_base_estrutura.sql`
        conforme a Task 0.3 do `Master_Plan_v2.md`, adicionando o que faltar
        para usar no Supabase com PostGIS e escrevendo um pequeno guia em
        `docs/banco_supabase.md` explicando como rodar a migration."*

3. **Engenheiro Geográfico — Parser NMEA (quando tiver receptor)**
   - Prompt:
     - *"Agente Geográfico, crie `docs/hardware/receptor_gnss.md` com os campos
        sugeridos na Task 0.2 e implemente `backend/geo/nmea_parser.py` que
        lê um .txt com sentenças NMEA do receptor e extrai latitude, longitude,
        altitude, HDOP, número de satélites e status de fix."*

➡ **Só avance para a Fase 1 quando:**
- `pytest backend/tests/` rodar e o gabarito estiver completo (mesmo que a
  implementação ainda seja simples).
- Você tiver a migration do banco pronta e entendida.

---

## Fase 1 — Núcleo Técnico (MVP Real)

### Bloco A — Backend primeiro

4. **Engenheiro Geográfico — API /geo/inverso**
   - Prompt:
     - *"Agente Geográfico, implemente o endpoint POST `/geo/inverso` em
        `backend/main.py` com PyProj/Shapely, SIRGAS 2000 SRID 4674, 6 casas
        decimais e testes em `backend/tests/test_inverso.py` usando o gabarito.
        Proibido try/except vazio."*

5. **Engenheiro Geográfico — API /geo/area**
   - Prompt:
     - *"Agente Geográfico, implemente o endpoint POST `/geo/area` em
        `backend/main.py` calculando área em m² e perímetro em metros, validando
        `shape.is_valid`, com testes em `backend/tests/test_area.py` baseados
        no gabarito."*

6. **Engenheiro Geográfico — API /geo/converter**
   - Prompt:
     - *"Agente Geográfico, implemente o endpoint POST `/geo/converter` em
        `backend/main.py` para converter SIRGAS 2000 lat/lon em UTM Zona 23S
        (SRID 4674), com testes em `backend/tests/test_converter.py`."*

7. **Revisor (Auditor) — Revisão da API**
   - Prompt:
     - *"Agente Auditor, revise `backend/main.py` e os testes em `backend/tests/`
        garantindo que:
        (1) não há try/except vazio,
        (2) erros retornam JSON {erro, codigo},
        (3) precisão está dentro da tolerância do gabarito."*

### Bloco B — Mobile e navegação

8. **Arquiteto UI/UX — Projeto Expo + abas**
   - Prompt:
     - *"Agente UI/UX, transforme a pasta `mobile/` em um projeto Expo pronto para rodar,
        configurando Expo Router com as abas Projeto, Mapa, Cálculos e Clientes
        usando os arquivos existentes em `mobile/app/(tabs)/`. Tema dark +
        laranja (#EF9F27)."*

9. **Arquiteto UI/UX — Tela de Cálculo Inverso**
   - Prompt:
     - *"Agente UI/UX, crie `mobile/app/calculos/inverso.tsx` com o formulário
        descrito no Master Plan v2, chamando o endpoint `/geo/inverso` do backend
        e exibindo resultado com boa legibilidade em campo."*

10. **Arquiteto de Dados — Modo offline (modelo)**
    - Prompt:
      - *"Agente Dados, defina o schema de sync offline para pontos (SQLite/WatermelonDB)
         e crie `database/migrations/002_sync_offline.sql` com a tabela de fila
         de sincronização, garantindo que não haja duplicatas ao enviar para o
         Supabase."*

11. **Arquiteto UI/UX + Engenheiro Geográfico — Fluxo completo Inverso**
    - Prompt:
      - *"Agente UI/UX e Agente Geográfico, garantam juntos que a tela de Cálculo
         Inverso chama corretamente o backend, apresenta mensagens de erro claras
         e salva o resultado no Supabase via API."*

➡ **Concluir Fase 1 quando:**
- `pytest backend/tests/` 100% verde.
- App Expo abre no celular, navega nas 4 abas e executa o cálculo de Inverso
  com o caso de teste do gabarito.
- Modo offline desenhado e com schema pronto (mesmo que o sync ainda seja simples).

---

## Fase 2 — Campo (GNSS + CAD simplificado)

12. **Engenheiro Geográfico — Bluetooth GNSS**
    - Prompt:
      - *"Agente Geográfico, crie o módulo de leitura GNSS em React Native usando
         `react-native-ble-plx` ou `react-native-bluetooth-serial`, conectando ao
         receptor definido em `docs/hardware/receptor_gnss.md` e exibindo posição,
         HDOP, satélites e status em tempo real."*

13. **Arquiteto UI/UX — Tela de coleta em campo**
    - Prompt:
      - *"Agente UI/UX, desenhe e implemente a tela de coleta em campo mostrando
         posição GNSS em tempo real, precisão e um botão grande 'Registrar ponto',
         integrado ao esquema de armazenamento offline."*

14. **Mestre da Automação — Import/Export CSV, DXF, KML**
    - Prompt:
      - *"Agente Automação, implemente importadores e exportadores em
         `backend/geo/importadores.py` e `backend/geo/exportadores.py` para CSV,
         TXT (Topograph), DXF (Métrica TOPO) e KML (Google Earth), expondo
         endpoints REST no backend."*

15. **Arquiteto UI/UX — Vista CAD**
    - Prompt:
      - *"Agente UI/UX, implemente a vista CAD simplificada na aba Mapa usando
         `react-native-svg` ou similar para plotar pontos, linhas, zoom e pan,
         com opção de exportar a imagem como PNG."*

➡ **Concluir Fase 2 quando:**
- App coleta pontos GNSS reais com precisão aceitável.
- Vista CAD mostra os pontos e polígonos corretamente.
- Exportação DXF abre no Métrica TOPO com coordenadas corretas.

---

## Fase 3 — Administrativo, Portal do Cliente e Memorial

16. **Arquiteto de Dados + UI/UX — CRM de processos**
    - Prompt:
      - *"Agente Dados e Agente UI/UX, implementem o módulo de CRM de processos
         (tabelas e telas) conforme a Task 3.1 do Master Plan v2, com status,
         datas, observações e vínculo cliente → projeto → processo."*

17. **Arquiteto de Dados — Portal do Cliente (magic link)**
    - Prompt:
      - *"Agente Dados, configure o fluxo de magic link usando Supabase Auth para
         que um cliente possa receber um link único, ver o status do processo e
         baixar documentos sem login tradicional."*

18. **Mestre da Automação — Memorial Descritivo**
    - Prompt:
      - *"Agente Automação, implemente o gerador de memorial descritivo em PDF
         usando Jinja2 + ReportLab, conforme Task 3.3 do Master Plan v2, usando
         dados reais de um projeto salvo no banco."*

19. **Agente RAG — Validação legal**
    - Prompt:
      - *"Agente RAG, valide o memorial descritivo gerado e o fluxo de documentos
         com base nas normas e leis em `docs/normas/`, apontando ajustes
         necessários para conformidade com o INCRA e Lei 13.465/2017."*

➡ **Concluir Fase 3 quando:**
- Um processo real foi registrado do início ao fim.
- Cliente real acessou o portal via magic link e baixou documentos.
- Memorial passou na validação do Agente RAG.

---

## Como usar este fluxo na prática

1. Abra o repositório `GeoAdmin-Pro` no Cursor.
2. Mantenha abertos:
   - `Master_Plan_v2.md`
   - `.cursorrules`
   - `Comandos_Agentes.md`
   - `Fluxo_Agentes_Fases.md` (este arquivo).
3. Vá seguindo **os itens em ordem** (1, 2, 3, ...), copiando e colando o prompt
   correspondente no chat do Cursor, garantindo que o agente mencionado esteja atuando.
4. Não avance para a próxima fase enquanto os critérios de aceitação da fase atual
   não estiverem claramente atendidos.

