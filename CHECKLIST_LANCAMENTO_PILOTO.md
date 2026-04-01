# Checklist de Lancamento — Piloto Condominial

## Objetivo
Lancar uma versao assistida do GeoAdmin Pro para um condominio real de 120 lotes, com foco em importacao inicial, acompanhamento por lote, magic link escopado, revisao de confrontacoes e base cartografica auditavel.

## Criterios de prontidao
- `APP_URL` publica configurada no backend.
- migrations `021`, `022`, `023` e `024` aplicadas no Supabase.
- importacao inicial de lotes validada com amostra real.
- pelo menos uma base oficial promovida manualmente pelo topografo.
- geração de magic links em lote funcionando.
- formulario do cliente exibindo apenas o recorte do participante/lote.
- confrontacoes com revisao explicita antes da geracao das cartas.

## Smoke test minimo
1. Criar ou abrir um projeto condominial.
2. Importar um arquivo de lotes.
3. Vincular participantes aos lotes principais.
4. Gerar magic links em lote.
5. Abrir um magic link e enviar formulario do cliente.
6. Confirmar se o formulario aparece somente para o lote correto.
7. Promover manualmente um arquivo para base oficial.
8. Revisar ao menos uma confrontacao como `confirmada`.
9. Gerar ZIP de cartas de confrontacao.
10. Confirmar no detalhe do projeto:
   - painel de lotes
   - historico de links
   - auditoria cartografica
   - prontidao do piloto

## Sinais de rollback
- projeto parcial criado sem participantes esperados.
- lote exibindo participante ou dados de outro lote.
- cliente enxergando outro imovel no magic link.
- arquivo promovido para base oficial sem acao explicita do topografo.
- cartas geradas a partir de confrontacoes descartadas.

## Rollback operacional
- suspender envio de novos links.
- manter o projeto no modo assistido.
- despromover a base oficial incorreta com novo upload correto e auditoria.
- revisar confrontacoes antes de novo pacote de cartas.
- reprocessar apenas os lotes afetados.

## Metricas minimas do piloto
- total de lotes
- lotes com participante vinculado
- formularios recebidos
- lotes com croqui/geometria
- lotes prontos
- confrontacoes confirmadas
- arquivos em base oficial
- documentos gerados

## Observacao de governanca
Nenhum arquivo importado altera automaticamente o perimetro oficial sem acao explicita do topografo.
O cliente nunca pode visualizar outros lotes, outros participantes ou o mapa global do empreendimento.
