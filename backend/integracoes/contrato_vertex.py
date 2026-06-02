"""
GeoAdmin Pro - Montador de Contrato para VERTEXROSEA

Normaliza todos os dados técnicos de um projeto (vértices, confrontantes, memorial descritivo, carimbo)
para a assinatura do contrato de geração CAD assíncrona.
"""

from typing import Dict, Any, List
from integracoes.freecad.generador_plantas import DadosPlantaTecnica

def montar_contrato_vertex(dados: DadosPlantaTecnica) -> Dict[str, Any]:
    """
    Monta a estrutura JSON ('Contrato') padronizada para o Job do FreeCAD na CAD Engine.
    """
    # 1. Normalizar vértices
    vertices_payload = []
    for idx, v in enumerate(dados.vertices):
        vertices_payload.append({
            "codigo": v.get("codigo") or f"V{idx+1:02d}",
            "x": float(v.get("x") or 0.0),
            "y": float(v.get("y") or 0.0),
            "z": float(v.get("z") or 0.0),
            "descricao": v.get("descricao") or ""
        })

    # 2. Normalizar confrontantes
    abutters_payload = []
    for idx, c in enumerate(dados.confrontantes):
        abutters_payload.append({
            "lado": c.get("lado") or f"Lado {idx+1}",
            "nome": c.get("nome") or "Não informado",
            "documento": c.get("cpf") or c.get("cpf_cnpj") or ""
        })

    # 3. Montar o payload final ("Contrato")
    contrato = {
        "project_ref": {
            "id": dados.projeto_id,
            "codigo": dados.projeto_nome,
            "numero_job": dados.numero_job or "N/A"
        },
        "property": {
            "nome": dados.nome_imovel,
            "municipio": dados.municipio,
            "estado": dados.estado,
            "matricula": dados.matricula,
            "comarca": dados.comarca,
            "area_ha": float(dados.area_ha or 0.0),
            "area_m2": float(dados.area_m2 or 0.0),
            "perimetro_m": float(dados.perimetro_m or 0.0)
        },
        "perimeter": {
            "source": "client_confirmed",
            "vertices": vertices_payload
        },
        "metadata": {
            "datum": dados.datum or "SIRGAS2000",
            "zona_utm": dados.zona_utm or "23S",
            "meridiano_central": dados.meridiano_central or "-45°",
            "escala": dados.configuracao.escala_padrao or "1:500"
        },
        "surveyor": {
            "nome": dados.tecnico_nome,
            "crt": dados.tecnico_crt,
            "crea": dados.tecnico_crea,
            "cpf": dados.tecnico_cpf,
            "codigo_incra": dados.tecnico_codigo_incra
        },
        "client": {
            "nome": dados.cliente_nome,
            "documento": dados.cliente_cpf or dados.cliente_documento
        },
        "abutters": abutters_payload,
        "outputs": dados.configuracao.formatos_saida or ["fcstd", "dxf", "pdf"]
    }

    return contrato
