# GeoAdmin Bridge

Utilitario Windows para preparar um projeto do GeoAdmin e entregar o workspace mastigado para o Métrica TOPO.

## O que faz no MVP

- baixa `POST /projetos/{id}/metrica/preparar`
- extrai o pacote em uma pasta local padrao
- grava `bridge_status.json`
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

## Observacao

No MVP o bridge nao escreve direto no banco interno do Métrica. Ele prepara o workspace local e abre o caminho para a proxima fase, que pode preencher um `PROJETO.ACCDB` de forma controlada.
