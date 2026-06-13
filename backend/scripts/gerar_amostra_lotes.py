import json
import math
from pathlib import Path

def gerar_amostra_120_lotes():
    # Coordenadas centrais aproximadas de Pirenópolis, GO
    lat_centro = -15.8500
    lon_centro = -48.9600
    
    features = []
    
    # Grid de 10 quadras (A a J), cada uma com 12 lotes (1 a 12)
    # Total = 120 lotes
    quadras = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
    lotes_por_quadra = 12
    
    # Tamanho aproximado de cada lote em graus
    # ~20m de largura por ~30m de profundidade
    largura_lote_graus = 0.00018  # aprox 20m
    profundidade_lote_graus = 0.00027  # aprox 30m
    
    # Espaçamento entre quadras (ruas)
    largura_rua_graus = 0.00010
    
    for q_idx, quadra_nome in enumerate(quadras):
        # Cada quadra terá uma linha de 12 lotes ao longo da longitude (leste-oeste)
        # E as quadras serão empilhadas ao longo da latitude (norte-sul)
        
        y_base = lat_centro + q_idx * (profundidade_lote_graus + largura_rua_graus)
        
        for l_idx in range(lotes_por_quadra):
            x_base = lon_centro + l_idx * largura_lote_graus
            
            # Cantos do polígono do lote (retângulo simples)
            c1 = [x_base, y_base]
            c2 = [x_base + largura_lote_graus, y_base]
            c3 = [x_base + largura_lote_graus, y_base + profundidade_lote_graus]
            c4 = [x_base, y_base + profundidade_lote_graus]
            # Fechamento
            c5 = [x_base, y_base]
            
            feature = {
                "type": "Feature",
                "properties": {
                    "codigo_lote": f"{l_idx + 1:02d}",
                    "quadra": quadra_nome,
                    "setor": "Setor Residencial Sol",
                    "nome": f"Lote {quadra_nome}-{l_idx + 1:02d}",
                    "proprietario_nome": f"Proprietário Lote {quadra_nome}-{l_idx + 1:02d}",
                    "municipio": "Pirenópolis",
                    "estado": "GO",
                    "comarca": "Pirenópolis",
                    "matricula": f"M-{quadra_nome}-{l_idx + 1:03d}",
                    "status_operacional": "cliente_vinculado",
                    "status_documental": "pendente",
                    "recebe_magic_link": True
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[c1, c2, c3, c4, c5]]
                }
            }
            features.append(feature)
            
    geojson_data = {
        "type": "FeatureCollection",
        "features": features
    }
    
    # Caminho final
    output_dir = Path(__file__).resolve().parents[1] / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "amostra_120_lotes.geojson"
    
    output_file.write_text(json.dumps(geojson_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Sucesso: Gerado arquivo com {len(features)} lotes em {output_file}")

if __name__ == "__main__":
    gerar_amostra_120_lotes()
