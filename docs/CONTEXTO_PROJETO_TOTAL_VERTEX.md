# CONTEXTO TOTAL DO PROJETO - VERTEX

> Documento canônico de contexto completo do projeto.
> Objetivo: evitar perda de lógica, retrabalho e mudanças fora do combinado.
> Sempre ler este arquivo antes de alterar backend, formulário, bot ou deploy.

---

## 1) Visão geral

- Nome atual do app/produto: **VERTEX**.
- Base técnica original: GeoAdmin Pro.
- Domínio: georreferenciamento rural e regularização fundiária.
- Canal principal de entrada de leads: **WhatsApp via Hermes**.

## 1.1) Herança GeoAdmin -> VERTEX (obrigatório)

### O que o VERTEX herda do GeoAdmin
- Backend, rotas e fluxo base do formulário público.
- Lógica de submissão e persistência no banco.
- Padrão funcional de mapa simples para apoio de descrição do cliente.

### O que foi adaptado no VERTEX
- Persona e comunicação comercial no Hermes/WhatsApp.
- Entrada guiada com magic link para funil de cadastro.
- Complemento OCR para reduzir digitação manual no formulário.

### O que não pode divergir da referência GeoAdmin
- Funil sem fricção no formulário (não travar envio).
- Mapa simples como apoio visual ao cliente.
- Cadastro inicial separado da etapa técnica interna.

### Regra de implementação
- Antes de alterar formulário/mapa, comparar com a referência GeoAdmin e só então adaptar para VERTEX.

---

## 2) Objetivo de negócio

Converter lead em cadastro real com mínimo atrito, coletando informações suficientes para triagem e proposta, sem exigir conhecimento técnico do cliente.

---

## 3) Perfil de usuário final

- Cliente rural, frequentemente com baixa familiaridade digital.
- Precisa de experiência simples, direta, com pouco texto e orientação prática.
- Não deve ser obrigado a entender coordenadas, SIGEF ou fluxo técnico para iniciar.

---

## 4) Princípios de atendimento (Hermes/WhatsApp)

1. Tom consultivo, técnico-acessível e comercialmente firme.
2. Mensagens curtas para WhatsApp.
3. O bot pode usar contexto de contato quando necessário para controle de acesso/comandos.
4. Não inventar preço, prazo, lei ou dado técnico.
5. Não citar assentamento/edital de forma proativa (somente se o cliente perguntar).
6. Ao identificar intenção de serviço/cadastro, enviar link de formulário (não depender de frase única).

---

## 5) Arquitetura acordada (alto nível)

1. Cliente manda mensagem no WhatsApp.
2. Hermes responde com CTA + link.
3. Backend gera magic link e contexto de formulário.
4. Cliente abre formulário oficial.
5. Cliente preenche dados básicos e envia fotos.
6. OCR roda em background como complemento.
7. Equipe interna assume etapa técnica posterior.

---

## 6) Componentes principais

### Backend (FastAPI)
- `backend/main.py` (registro de rotas)
- `backend/routes/vertex_lead.py` (geração de lead + magic link)
- `backend/routes/documentos.py` (formulário oficial `/formulario/cliente` e submissão)
- `backend/services/ocr_vision.py` (OCR complementar)
- `backend/static/formulario_cliente.html` (formulário oficial)

### Infra
- Deploy em Google Cloud Run (`geoadmin-api`)
- Banco em Supabase (projeto live já definido no histórico)

### Bot
- Hermes com persona VERTEX e resposta com link de cadastro.

---

## 7) Regras funcionais não-negociáveis

1. Formulário principal é `/formulario/cliente`.
2. Deve existir bloco de **fotos de documentos** no formulário oficial.
3. OCR é **complemento interno**, nunca etapa separada para o cliente.
4. Cliente não precisa coordenadas para concluir cadastro inicial.
5. Deve existir **mapa simples** para orientar descrição mínima da área.
6. O mapa não pode bloquear envio (degradação segura).
7. O formulário é o começo do funil: não pode criar objeção que impeça envio.

---

## 8) Regra de mapa (interpretação correta)

- O mapa simples no GeoAdmin e a referencia oficial de implementacao para este fluxo.
- O mapa é obrigatório na experiência, mas simples.
- Serve para orientação e descrição mínima, não para validação técnica final.
- Cadastro inicial não depende de perímetro técnico pronto.

---

## 9) Estado consolidado do que já foi feito

- Integração bot -> geração de link de cadastro.
- Formulário oficial mantido como fluxo principal.
- Bloco de fotos adicionado no formulário oficial.
- OCR integrado no backend como complemento.
- GeoAdmin e a referencia obrigatoria para comportamento do mapa simples.
- Contextos canônicos criados em `docs/CONTEXTO_LOGICA_VERTEX.md` e `docs/TODO_CANONICO_VERTEX.md`.

---

## 10) Estado atual pendente (foco imediato)

1. Validar no live se o comportamento do mapa segue a referencia do GeoAdmin (sem regressão).
2. Garantir fim a fim:
   - intenções variadas de serviço -> link certo;
   - formulário abre;
   - mapa simples aparece;
   - fotos enviam;
   - envio conclui sem exigir coordenadas.

---

## 11) O que não fazer

- Não abrir fluxo paralelo sem aprovação.
- Não sobrescrever decisões já combinadas.
- Não ignorar comandos/acordos já definidos no chat.
- Não implementar mudança grande sem atualizar contexto e TODO canônicos.

---

## 12) Protocolo de execução obrigatório

Antes de qualquer mudança:
1. Declarar qual regra deste contexto está sendo atendida.
2. Informar quais arquivos serão alterados.
3. Fazer mudança mínima necessária.
4. Validar resultado objetivo.
5. Atualizar `docs/TODO_CANONICO_VERTEX.md`.

---

## 13) Critérios de aceite do fluxo de cadastro

- Cliente completa cadastro sem travamento técnico.
- Fotos de documentos entram no fluxo oficial.
- OCR falhando não impede envio.
- Mapa simples sempre disponível como apoio visual.
- Linguagem e UX continuam adequadas ao público-alvo.

---

## 14) Governança de escopo

Qualquer mudança que conflite com este contexto só pode ser feita com aprovação explícita no chat.
