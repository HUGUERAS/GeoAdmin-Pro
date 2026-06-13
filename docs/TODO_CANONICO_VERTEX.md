# TODO CANONICO - VERTEX (COMPLETO)

> Estado consolidado de execucao para evitar perda de contexto.

## A) Ja concluido (historico importante)

- Ambiente live definido (Cloud Run + Supabase alvo).
- Endpoint de lead/magic link implementado e em uso.
- Integracao bot -> link de cadastro implementada.
- Formulario oficial `/formulario/cliente` mantido como principal.
- Bloco de fotos de documentos incluido no formulario oficial.
- OCR integrado como complemento interno.
- Ajustes de comportamento do bot e formulario alinhados ao fluxo comercial.

## B) Em aberto agora (prioridade alta)

1. Validar mapa simples no live contra a referencia do GeoAdmin:
   - sempre visivel na etapa do cliente;
   - funcional como apoio de descricao minima;
   - sem bloquear envio.
2. Fechar validacao live ponta a ponta:
   - WhatsApp (intencoes variadas) -> link;
   - abertura do formulario;
   - envio de fotos;
   - exibicao do mapa simples;
   - submissao final sem coordenadas obrigatorias.

## C) Regras de trabalho (obrigatorias)

- Nao reabrir item fechado sem pedido explicito.
- Nao iniciar item novo sem reportar status do item atual.
- Toda mudanca deve referenciar `CONTEXTO_LOGICA_VERTEX.md`.
