# GeoAdmin Bridge

Utilitario Windows para preparar um projeto do GeoAdmin e entregar o workspace mastigado para o Métrica TOPO.

## O que faz no MVP

- baixa `POST /projetos/{id}/metrica/preparar`
- organiza o workspace em subpastas operacionais
- grava `99_bridge/bridge_status.json`
- grava log local em `99_bridge/logs/bridge.log`
- gera `ABRIR_NO_METRICA.bat`
- abre a pasta do projeto
- opcionalmente abre o Métrica TOPO

## Uso

```bash
python bridge/geoadmin_bridge.py ^
  --backend-url https://geoadmin-pro-production.up.railway.app ^
  --projeto-id 36510522-3544-46fe-bbe1-e6348dd708df ^
  --abrir-metrica ^
  --salvar-config
```

Ou consumindo um pacote local ja baixado:

```bash
python bridge/geoadmin_bridge.py ^
  --pacote-local C:\temp\GeoAdmin_sem-job_toguim.zip ^
  --nao-abrir-pasta
```

## Pasta padrao

```text
%USERPROFILE%\GeoAdmin\Metrica
```

## Estrutura do workspace

```text
{projeto}/
  01_entrada/
  02_cad/
  03_documentos/
  04_exportacoes/
  99_bridge/
  ABRIR_NO_METRICA.bat
  COMO_USAR_NO_METRICA.txt
```

## Conteudo esperado do pacote

- `manifesto.json`
- `COMO_USAR_NO_METRICA.txt`
- `dados/projeto.json`
- `dados/cliente.json`
- `dados/confrontantes.json`
- `dados/documentos.json`
- `dados/pontos.json`
- `dados/perimetro_ativo.geojson`
- `dados/referencia_cliente.geojson`
- `GeoAdmin_*.txt`
- `GeoAdmin_*.csv`
- `GeoAdmin_*.kml`
- `GeoAdmin_*.dxf`

## Manifesto dedicado

Para inspeção sem baixar o ZIP completo:

```text
GET /projetos/{id}/metrica/manifesto
```

## Observacao

No MVP o bridge nao escreve direto no banco interno do Métrica. Ele prepara o workspace local e abre o caminho para a proxima fase, que pode preencher um `PROJETO.ACCDB` de forma controlada.
