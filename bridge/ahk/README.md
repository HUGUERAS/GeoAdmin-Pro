# AutoHotkey Fallback

Esta pasta fica reservada para o plano C do fluxo GeoAdmin -> Métrica.

## Quando usar

Somente quando a abertura por arquivo e o preparo do workspace nao forem suficientes e ainda for necessario automatizar etapas repetitivas da interface do Métrica TOPO.

Exemplos:

- abrir a rotina de importacao de pontos
- selecionar automaticamente o TXT/CSV preparado pelo bridge
- abrir o DXF na pasta `02_cad`
- confirmar dialogos previsiveis

## Regra importante

AutoHotkey deve ser adaptador de interface, nao regra principal de negocio.

Toda a inteligencia continua no GeoAdmin e no bridge. Os scripts AHK so executam cliques e atalhos mecanicos.
