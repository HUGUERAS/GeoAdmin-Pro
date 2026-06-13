# CONTEXTO LOGICO CANONICO - VERTEX (COMPLETO)

> Fonte unica de verdade do projeto neste chat.  
> Este documento cobre o historico completo acordado (nao so ultimas mensagens).  
> Se houver conflito entre codigo atual e este arquivo, seguir este arquivo.

## 1) Identidade do projeto

- Nome atual: **VERTEX** (base tecnica veio do GeoAdmin Pro).
- Dominio do atendimento: georreferenciamento rural e regularizacao fundiaria.
- Canal critico: WhatsApp via Hermes.
- Regra de contexto: toda mudanca deve considerar a heranca GeoAdmin antes da adaptacao VERTEX.

## 2) Objetivo de negocio

- Converter contato em cadastro real com o menor atrito possivel.
- Coletar dados minimos para triagem e proposta.
- Evitar perda de lead por formulario dificil.

## 3) Perfil do cliente (premissa fixa)

- Cliente muitas vezes simples, com baixa escolaridade tecnica.
- Fluxo tem que ser curto, direto e guiado.
- Nada de exigir termos tecnicos para iniciar.

## 4) Regras de atendimento do bot (ja combinadas)

1. Tom consultivo, tecnico-acessivel, firme comercialmente.
2. Pode usar contexto do contato quando necessario para controle de acesso/comandos.
3. Nao inventar informacao (preco, prazo, dados legais).
4. Mensagens curtas para WhatsApp.
5. Nao citar assentamento/edital de forma proativa (so quando perguntado).
6. Quando identificar intencao de servico/cadastro, entregar link de cadastro.
7. O cliente nao precisa saber frase exata para receber o link.

## 5) Arquitetura acordada (macro)

1. Bot envia CTA com link.
2. Backend gera magic link.
3. Cliente abre formulario oficial.
4. Cliente envia dados + fotos.
5. OCR roda em background como complemento.
6. Equipe interna assume etapa tecnica.

## 6) Regras do formulario (nao-negociaveis)

1. Formulario oficial: `/formulario/cliente`.
2. Deve ter bloco de fotos no formulario oficial.
3. OCR e complemento interno, nunca etapa separada para cliente.
4. Cliente nao precisa informar coordenadas para concluir cadastro.
5. Deve existir **mapa simples** para descricao minima da area.
6. O mapa **nao pode bloquear envio**.
7. O formulario e o inicio do funil: qualquer friccao que impeça envio e regressao.

## 7) Regras do mapa (interpretacao correta)

- O mapa simples no GeoAdmin e a referencia oficial que deve ser consultada antes de alterar este fluxo.
- Mapa e obrigatorio na experiencia (orientacao visual para o cliente).
- Mapa nao e criterio de bloqueio tecnico do cadastro.
- Cadastro inicial nao depende de levantamento topografico pronto.
- Etapa tecnica detalhada fica para o time interno, depois do envio.

## 8) Decisoes ja tomadas (nao reabrir sem aprovacao)

- Nome do app/atendimento: VERTEX.
- Fluxo principal usa formulario oficial.
- OCR permanece complementar.
- Evitar explicacoes tecnicas para o cliente final.

## 9) Erros recorrentes que nao podem se repetir

- Criar fluxo paralelo sem alinhamento.
- Sobrescrever decisao anterior.
- Tentar "forcar" logica tecnica antes de validar regra de negocio.
- Corrigir sintoma sem preservar o combinado do produto.

## 10) Protocolo obrigatorio de execucao

Antes de alterar qualquer arquivo:
1. Referenciar explicitamente qual item deste contexto a mudanca atende.
2. Descrever impacto no fluxo do cliente.
3. Alterar o minimo necessario.
4. Validar e reportar resultado objetivo.
5. Atualizar TODO canonico.

## 11) Politica de mudanca de escopo

Se for necessario mexer em qualquer regra acima, parar e pedir aprovacao explicita no chat antes de codar.
