"""
GeoAdmin Pro — Integração com FreeCAD para geração de peças técnicas
=====================================================================
backend/integracoes/freecad/__init__.py

Módulo principal da integração com FreeCAD para:
- Gerar plantas técnicas em DWG/DXF conforme NBR 13.133 e NBR 14.166
- Preencher carimbo/tabela de dados automaticamente via Magic Link
- Exportar para PDF, DWG e DWF com elementos gráficos padronizados

Requisitos:
    - FreeCAD 1.0+ instalado no sistema
    - pythonOCC ou CadQuery para operações CAD
    - ezdxf já incluído no requirements.txt

Uso:
    from integracoes.freecad import gerar_planta_tecnica
    
    resultado = gerar_planta_tecnica(
        projeto_id="uuid-do-projeto",
        supabase=client,
        formato_saida=["dwg", "pdf"],
        incluir_carimbo=True,
        escala="1:500"
    )
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
import io
import tempfile
import subprocess
import os
import sys

logger = logging.getLogger("geoadmin.freecad")

# Evita abertura de janelas de console no Windows (background)
creation_flags = 0
if sys.platform == "win32":
    try:
        creation_flags = subprocess.CREATE_NO_WINDOW
    except AttributeError:
        creation_flags = 0x08000000



@dataclass
class ConfiguracaoFreeCAD:
    """Configurações para geração de peças técnicas no FreeCAD."""
    
    # Caminho para executável do FreeCAD
    freecad_path: str = "freecad"
    
    # Template de desenho (Arquivo .FCStd com layout pré-configurado)
    template_path: Optional[str] = None
    
    # Escala padrão da planta
    escala_padrao: str = "1:500"
    
    # Sistema de coordenadas
    srid: int = 9187  # SIRGAS 2000 / UTM zone 23S (padrão GO)
    
    # Unidades
    unidade: str = "metro"
    
    # Precisão decimal
    precisao: int = 3
    
    # Opções de saída
    formatos_saida: List[str] = field(default_factory=lambda: ["dwg", "pdf"])
    
    # Incluir elementos
    incluir_carimbo: bool = True
    incluir_norte: bool = True
    incluir_legenda: bool = True
    incluir_malha: bool = False
    incluir_confrontantes: bool = True
    incluir_curvas_nivel: bool = False
    
    # Estilo NBR
    cor_linha_perimetro: str = "#000000"
    espessura_linha_perimetro: float = 0.5  # mm
    cor_texto: str = "#000000"
    fonte_padrao: str = "ISOCP.TTF"
    tamanho_texto_principal: float = 2.5  # mm
    tamanho_texto_secundario: float = 1.8  # mm


@dataclass
class DadosPlantaTecnica:
    """Dados completos para geração da planta técnica."""
    
    # Identificação do projeto
    projeto_id: str
    projeto_nome: str
    numero_job: Optional[str]
    
    # Dados do imóvel
    nome_imovel: str
    municipio: str
    estado: str
    matricula: str
    comarca: str
    area_ha: float
    area_m2: float
    perimetro_m: float
    
    # Coordenadas e geometria
    vertices: List[Dict[str, Any]]
    centroide: Dict[str, float]
    bbox: Dict[str, float]
    
    # Cliente
    cliente_nome: str
    cliente_cpf: str
    cliente_documento: str
    
    # Técnico responsável
    tecnico_nome: str
    tecnico_crt: str
    tecnico_crea: str
    tecnico_cpf: str
    tecnico_codigo_incra: str
    
    # Confrontantes
    confrontantes: List[Dict[str, Any]]
    
    # Pontos de amarração
    pontos_ammarracao: List[Dict[str, Any]]
    
    # Datum e projeção
    datum: str = "SIRGAS2000"
    fuso_horario: str = "-3"
    zona_utm: str = "23S"
    meridiano_central: str = "-45°"
    
    # Informações complementares (campos sem default devem vir primeiro)
    data_levantamento: str = ""
    data_processamento: str = ""
    observacoes: str = ""
    
    # Configurações de saída
    configuracao: ConfiguracaoFreeCAD = field(default_factory=ConfiguracaoFreeCAD)


def _verificar_freecad_disponivel(config: ConfiguracaoFreeCAD) -> bool:
    """
    Verifica se o FreeCAD está instalado e acessível.
    
    Returns:
        bool: True se FreeCAD estiver disponível, False caso contrário.
    """
    try:
        result = subprocess.run(
            [config.freecad_path, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=creation_flags
        )
        if result.returncode == 0:
            logger.info(f"FreeCAD detectado: {result.stdout.strip()}")
            return True
        else:
            logger.warning(f"FreeCAD retornou código {result.returncode}")
            return False
    except FileNotFoundError:
        logger.error(f"FreeCAD não encontrado em '{config.freecad_path}'")
        return False
    except subprocess.TimeoutExpired:
        logger.error("Timeout ao verificar FreeCAD")
        return False
    except Exception as e:
        logger.error(f"Erro ao verificar FreeCAD: {e}")
        return False


def _buscar_dados_planta(supabase, projeto_id: str) -> DadosPlantaTecnica:
    """
    Busca todos os dados necessários para gerar a planta técnica.
    
    Args:
        supabase: Cliente Supabase
        projeto_id: UUID do projeto
        
    Returns:
        DadosPlantaTecnica com todos os dados preenchidos
        
    Raises:
        ValueError: Se projeto não for encontrado
    """
    from integracoes.integracao_metrica import _buscar_pontos, _buscar_projeto
    from routes.perimetros import buscar_perimetro_ativo
    from integracoes.referencia_cliente import obter_geometria_referencia
    
    # Buscar projeto
    projeto = _buscar_projeto(supabase, projeto_id)
    if not projeto:
        raise ValueError(f"[ERRO-401] Projeto {projeto_id} não encontrado.")
    
    # Buscar pontos
    pontos = _buscar_pontos(supabase, projeto_id)
    
    # Buscar perímetro ativo
    perimetro = buscar_perimetro_ativo(projeto_id, supabase=supabase)
    if not perimetro:
        raise ValueError(f"[ERRO-402] Nenhum perímetro ativo encontrado para {projeto_id}.")
    
    vertices = perimetro.get("vertices", [])
    if not vertices:
        raise ValueError(f"[ERRO-403] Perímetro sem vértices para {projeto_id}.")
    
    # Calcular métricas
    area_ha = float(projeto.get("area_ha") or 0)
    area_m2 = area_ha * 10000
    
    # Calcular perímetro aproximado
    perimetro_m = 0.0
    if len(vertices) >= 2:
        for i in range(len(vertices)):
            v1 = vertices[i]
            v2 = vertices[(i + 1) % len(vertices)]
            dx = float(v2.get("x", 0)) - float(v1.get("x", 0))
            dy = float(v2.get("y", 0)) - float(v1.get("y", 0))
            perimetro_m += (dx**2 + dy**2)**0.5
    
    # Calcular bounding box e centroide
    coords_x = [float(v.get("x", 0)) for v in vertices]
    coords_y = [float(v.get("y", 0)) for v in vertices]
    
    bbox = {
        "min_x": min(coords_x),
        "max_x": max(coords_x),
        "min_y": min(coords_y),
        "max_y": max(coords_y),
    }
    
    centroide = {
        "x": sum(coords_x) / len(coords_x),
        "y": sum(coords_y) / len(coords_y),
    }
    
    # Buscar cliente
    cliente = None
    cliente_id = projeto.get("cliente_id")
    if cliente_id:
        res = supabase.table("clientes").select("*").eq("id", cliente_id).maybe_single().execute()
        cliente = res.data
    
    # Buscar técnico
    tec_res = supabase.table("tecnico").select("*").eq("ativo", True).limit(1).execute()
    tecnico = tec_res.data[0] if tec_res.data else {}
    
    # Buscar confrontantes
    conf_res = supabase.table("confrontantes").select("*").eq("projeto_id", projeto_id).is_("deleted_at", "null").execute()
    confrontantes = conf_res.data or []
    
    # Converter pontos para lista de dicionários
    pontos_lista = []
    for p in pontos:
        pontos_lista.append({
            "nome": p.nome,
            "codigo": p.codigo,
            "norte": p.norte,
            "este": p.este,
            "elevacao": p.elevacao,
        })
    
    # Determinar datas
    from datetime import datetime
    data_atual = datetime.now().strftime("%d/%m/%Y")
    
    return DadosPlantaTecnica(
        projeto_id=projeto_id,
        projeto_nome=projeto.get("projeto_nome", ""),
        numero_job=projeto.get("numero_job"),
        nome_imovel=projeto.get("nome_imovel") or projeto.get("projeto_nome", ""),
        municipio=projeto.get("municipio", ""),
        estado=projeto.get("estado", "GO"),
        matricula=projeto.get("matricula", ""),
        comarca=projeto.get("comarca", ""),
        area_ha=area_ha,
        area_m2=area_m2,
        perimetro_m=perimetro_m,
        vertices=vertices,
        centroide=centroide,
        bbox=bbox,
        cliente_nome=cliente.get("nome", "") if cliente else "",
        cliente_cpf=cliente.get("cpf", "") if cliente else "",
        cliente_documento=cliente.get("rg", "") if cliente else "",
        tecnico_nome=tecnico.get("nome", ""),
        tecnico_crt=tecnico.get("crt", ""),
        tecnico_crea=tecnico.get("crea", ""),
        tecnico_cpf=tecnico.get("cpf", ""),
        tecnico_codigo_incra=tecnico.get("codigo_incra", ""),
        confrontantes=confrontantes,
        pontos_ammarracao=pontos_lista,
        datum="SIRGAS2000",
        zona_utm=projeto.get("zona_utm", "23S"),
        data_levantamento=data_atual,
        data_processamento=data_atual,
        observacoes=projeto.get("observacoes", ""),
    )


def gerar_script_freecad(dados: DadosPlantaTecnica) -> str:
    """
    Gera script Python para execução no FreeCAD.
    
    Este script cria:
    1. Geometria do perímetro
    2. Carimbo com dados do projeto
    3. Tabela de coordenadas dos vértices
    4. Seta de norte verdadeiro
    5. Legenda e informações complementares
    
    Args:
        dados: Dados completos da planta técnica
        
    Returns:
        Script Python formatado para execução no FreeCAD
    """
    config = dados.configuracao
    
    # Preparar dados para o script
    vertices_str = str([
        {"x": v.get("x", 0), "y": v.get("y", 0), "z": v.get("z", 0)}
        for v in dados.vertices
    ])
    
    confrontantes_str = str([{
        "lado": c.get("lado", ""),
        "nome": c.get("nome", ""),
        "documento": c.get("cpf", ""),
    } for c in dados.confrontantes])
    
    script = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script gerado automaticamente pelo GeoAdmin Pro
Projeto: {dados.projeto_nome}
Gerado em: {dados.data_processamento}
"""

import FreeCAD
import Part
import Draft
import Drawing
from FreeCAD import Vector
import math

# Configurações do documento
doc = FreeCAD.newDocument("Plana_Tecnica_{dados.projeto_id[:8]}")
FreeCAD.setActiveDocument(doc.Name)

# ============================================================
# PARÂMETROS DO PROJETO
# ============================================================

PROJETO_ID = "{dados.projeto_id}"
PROJETO_NOME = "{dados.projeto_nome}"
NUMERO_JOB = "{dados.numero_job or 'N/A'}"
NOME_IMOVEL = "{dados.nome_imovel}"
MUNICIPIO = "{dados.municipio}"
ESTADO = "{dados.estado}"
MATRICULA = "{dados.matricula}"
COMARCA = "{dados.comarca}"
AREA_HA = {dados.area_ha:.4f}
AREA_M2 = {dados.area_m2:.2f}
PERIMETRO_M = {dados.perimetro_m:.2f}

CLIENTE_NOME = "{dados.cliente_nome}"
CLIENTE_CPF = "{dados.cliente_cpf}"

TECNICO_NOME = "{dados.tecnico_nome}"
TECNICO_CRT = "{dados.tecnico_crt}"
TECNICO_CREA = "{dados.tecnico_crea}"

DATUM = "{dados.datum}"
ZONA_UTM = "{dados.zona_utm}"
DATA_LEVANTAMENTO = "{dados.data_levantamento}"

ESCALA = "{config.escala_padrao}"
UNIDADE = "{config.unidade}"

# Vértices do perímetro (coordenadas UTM)
VERTICES = {vertices_str}

# Confrontantes
CONFRONTANTES = {confrontantes_str}

# Centroide e Bounding Box
CENTROIDE_X = {dados.centroide['x']:.3f}
CENTROIDE_Y = {dados.centroide['y']:.3f}
BBOX_MIN_X = {dados.bbox['min_x']:.3f}
BBOX_MAX_X = {dados.bbox['max_x']:.3f}
BBOX_MIN_Y = {dados.bbox['min_y']:.3f}
BBOX_MAX_Y = {dados.bbox['max_y']:.3f}

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def criar_linha(p1, p2, cor=(0.0, 0.0, 0.0), espessura=0.5):
    """Cria uma linha entre dois pontos."""
    line = Part.makeLine(Vector(p1[0], p1[1], 0), Vector(p2[0], p2[1], 0))
    shape = Part.Shape([line])
    obj = doc.addObject("Part::Feature", "Line")
    obj.Shape = shape
    obj.ViewObject.LineColor = cor
    obj.ViewObject.LineWidth = espessura
    return obj

def criar_poligono(vertices, fechado=True, cor=(0.0, 0.0, 0.0), espessura=0.5, nome="Polygon"):
    """Cria um polígono a partir de uma lista de vértices."""
    if len(vertices) < 2:
        return None
    
    edges = []
    for i in range(len(vertices)):
        p1 = vertices[i]
        p2 = vertices[(i + 1) % len(vertices)] if fechado else vertices[i + 1]
        edge = Part.makeLine(
            Vector(p1.get('x', 0), p1.get('y', 0), 0),
            Vector(p2.get('x', 0), p2.get('y', 0), 0)
        )
        edges.append(edge)
    
    if fechado and len(edges) > 2:
        wire = Part.Wire(edges)
        face = Part.Face(wire)
        shape = Part.Shape([face])
    else:
        wire = Part.Wire(edges)
        shape = Part.Shape([wire])
    
    obj = doc.addObject("Part::Feature", nome)
    obj.Shape = shape
    obj.ViewObject.LineColor = cor
    obj.ViewObject.LineWidth = espessura
    return obj

def criar_texto(texto, posicao, altura=2.5, cor=(0.0, 0.0, 0.0), nome="Text"):
    """Cria um objeto de texto."""
    text_obj = doc.addObject("App::AnnotationLabel", nome)
    text_obj.Label = texto
    text_obj.Placement.Base = Vector(posicao[0], posicao[1], 0)
    text_obj.ViewObject.FontSize = altura
    text_obj.ViewObject.TextColor = cor
    return text_obj

def criar_tabela_coordenadas(vertices, posicao_base, altura_linha=5.0, largura_colunas=None):
    """Cria tabela de coordenadas dos vértices."""
    if largura_colunas is None:
        largura_colunas = [15.0, 40.0, 40.0, 40.0, 40.0]  # Código, X, Y, Z, Dist
    
    x_base, y_base = posicao_base
    
    # Cabeçalho
    cabecalho = ["CÓDIGO", "COORD. X (m)", "COORD. Y (m)", "COTA (m)", "DISTÂNCIA (m)"]
    for idx, col in enumerate(cabecalho):
        x = x_base + sum(largura_colunas[:idx])
        criar_texto(col, (x, y_base), altura=2.0, nome=f"Header_{{idx}}")
    
    y_atual = y_base - altura_linha
    
    # Linhas de dados
    for idx, v in enumerate(vertices):
        codigo = v.get('codigo', f'V{{idx+1:03d}}')
        x = v.get('x', 0)
        y = v.get('y', 0)
        z = v.get('z', 0)
        
        # Calcular distância para próximo vértice
        if idx < len(vertices) - 1:
            dx = vertices[idx+1].get('x', 0) - x
            dy = vertices[idx+1].get('y', 0) - y
            dist = math.sqrt(dx**2 + dy**2)
        else:
            dx = vertices[0].get('x', 0) - x
            dy = vertices[0].get('y', 0) - y
            dist = math.sqrt(dx**2 + dy**2)
        
        dados_linha = [
            codigo,
            f"{{x:.3f}}",
            f"{{y:.3f}}",
            f"{{z:.3f}}",
            f"{{dist:.3f}}"
        ]
        
        for j, valor in enumerate(dados_linha):
            x = x_base + sum(largura_colunas[:j])
            criar_texto(valor, (x, y_atual), altura=1.8, nome=f"Vertex_{{idx}}_Col{{j}}")
        
        y_atual -= altura_linha
    
    return y_atual

def criar_carimbo(posicao_inferior_direita, largura=180, altura=45):
    """Cria carimbo padrão NBR 10.582."""
    x0, y0 = posicao_inferior_direita
    
    # Bordas do carimbo
    criar_linha((x0, y0), (x0 + largura, y0), espessura=0.7)  # Inferior
    criar_linha((x0, y0), (x0, y0 + altura), espessura=0.7)  # Esquerda
    criar_linha((x0 + largura, y0), (x0 + largura, y0 + altura), espessura=0.3)  # Direita
    criar_linha((x0, y0 + altura), (x0 + largura, y0 + altura), espessura=0.3)  # Superior
    
    # Divisões internas
    y1 = y0 + 10
    y2 = y0 + 20
    y3 = y0 + 30
    
    criar_linha((x0, y1), (x0 + largura, y1), espessura=0.3)
    criar_linha((x0, y2), (x0 + largura, y2), espessura=0.3)
    criar_linha((x0, y3), (x0 + largura, y3), espessura=0.3)
    
    x_div = x0 + largura * 0.6
    criar_linha((x_div, y0), (x_div, y0 + altura), espessura=0.3)
    
    # Preenchimento do carimbo
    # Linha 1 - Nome do projeto
    criar_texto(f"PROJETO: {{PROJETO_NOME}}", (x0 + 2, y0 + 22), altura=2.0)
    
    # Linha 2 - Imóvel e município
    criar_texto(f"IMÓVEL: {{NOME_IMOVEL}}", (x0 + 2, y0 + 12), altura=1.8)
    criar_texto(f"MUNICÍPIO: {{MUNICIPIO}}/{{ESTADO}}", (x0 + 2, y0 + 2), altura=1.8)
    
    # Coluna direita - Técnico
    criar_texto(f"TÉCNICO:", (x_div + 2, y0 + 42), altura=1.5)
    criar_texto(f"{{TECNICO_NOME}}", (x_div + 2, y0 + 35), altura=1.8)
    criar_texto(f"CRT: {{TECNICO_CRT}} | CREA: {{TECNICO_CREA}}", (x_div + 2, y0 + 27), altura=1.5)
    criar_texto(f"DATA: {{DATA_LEVANTAMENTO}}", (x_div + 2, y0 + 17), altura=1.5)
    criar_texto(f"ESCALA: {{ESCALA}}", (x_div + 2, y0 + 7), altura=1.5)
    
    # Área e perímetro
    criar_texto(f"ÁREA: {{AREA_HA:.4f}} ha ({{AREA_M2:.2f}} m²)", (x0 + 2, y0 + 32), altura=1.8)
    
    return (x0, y0 + altura)

def criar_seta_norte(posicao, tamanho=20):
    """Cria seta de norte verdadeiro."""
    x, y = posicao
    
    # Criar triângulo da seta
    pontos_seta = [
        {{'x': x, 'y': y}},
        {{'x': x - tamanho/3, 'y': y - tamanho*0.8}},
        {{'x': x + tamanho/3, 'y': y - tamanho*0.8}},
    ]
    criar_poligono(pontos_seta, fechado=True, cor=(0.0, 0.0, 0.0), espessura=0.5, nome="Norte_Seta")
    
    # Linha vertical
    criar_linha((x, y), (x, y - tamanho*0.8), espessura=0.5)
    
    # Texto "N"
    criar_texto("N", (x - 2, y + 2), altura=3.0, nome="Norte_Texto")
    
    # Símbolo de norte verdadeiro (círculo com cruz)
    circulo = Part.makeCircle(tamanho*0.6, Vector(x, y - tamanho*0.4, 0))
    circulo_obj = doc.addObject("Part::Feature", "Norte_Simbolo")
    circulo_obj.Shape = Part.Shape([circulo])
    
    return (x, y + tamanho + 5)

def criar_legenda(posicao, confrontantes):
    """Cria legenda com informações dos confrontantes."""
    x, y = posicao
    
    criar_texto("LEGENDA:", (x, y), altura=2.5, nome="Legenda_Titulo")
    y -= 5
    
    criar_texto("——— PERÍMETRO DO IMÓVEL", (x, y), altura=1.8, nome="Legenda_Perimetro")
    y -= 4
    
    for i, conf in enumerate(confrontantes[:5]):  # Limitar a 5 confrontantes
        lado = conf.get('lado', f'Lado {{i+1}}')
        nome = conf.get('nome', 'Não informado')
        criar_texto(f"→ {{lado}}: {{nome}}", (x, y), altura=1.8, nome=f"Legenda_Conf_{{i}}")
        y -= 4
    
    return (x, y - 5)

# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print(f"Geração de Planta Técnica - {{PROJETO_NOME}}")
    print("=" * 60)
    
    # Normalizar coordenadas para origem local (evitar valores muito grandes)
    offset_x = CENTROIDE_X
    offset_y = CENTROIDE_Y
    
    vertices_normalizados = []
    for v in VERTICES:
        vertices_normalizados.append({{
            'x': v['x'] - offset_x,
            'y': v['y'] - offset_y,
            'z': v.get('z', 0)
        }})
    
    print(f"Normalizando coordenadas (offset: {{offset_x:.1f}}, {{offset_y:.1f}})")
    print(f"Total de vértices: {{len(VERTICES)}}")
    
    # 1. Criar perímetro do imóvel
    print("Criando perímetro do imóvel...")
    perimetro = criar_poligono(
        vertices_normalizados,
        fechado=True,
        cor=(0.0, 0.0, 0.0),
        espessura={config.espessura_linha_perimetro},
        nome="Perimetro_Imovel"
    )
    
    # 2. Criar carimbo no canto inferior direito
    print("Criando carimbo...")
    # Posicionar carimbo baseado no bounding box normalizado
    largura_desenho = BBOX_MAX_X - BBOX_MIN_X
    altura_desenho = BBOX_MAX_Y - BBOX_MIN_Y
    
    margem_direita = largura_desenho * 0.05
    margem_inferior = altura_desenho * 0.05
    
    pos_carimbo = (
        largura_desenho - 180 + margem_direita,
        margem_inferior
    )
    criar_carimbo(pos_carimbo)
    
    # 3. Criar tabela de coordenadas
    print("Criando tabela de coordenadas...")
    pos_tabela = (margem_direita, altura_desenho * 0.6)
    criar_tabela_coordenadas(vertices_normalizados, pos_tabela)
    
    # 4. Criar seta de norte
    print("Criando seta de norte...")
    pos_norte = (largura_desenho * 0.9, altura_desenho * 0.9)
    criar_seta_norte(pos_norte)
    
    # 5. Criar legenda
    print("Criando legenda...")
    pos_legenda = (margem_direita, altura_desenho * 0.4)
    criar_legenda(pos_legenda, CONFRONTANTES)
    
    # 6. Salvar documento
    caminho_saida = "/tmp/planta_tecnica_{dados.projeto_id[:8]}.FCStd"
    doc.saveAs(caminho_saida)
    print(f"Documento FreeCAD salvo em: {{caminho_saida}}")
    
    # Manter documento aberto para exportação
    FreeCAD.setActiveDocument(doc.Name)
    
    print("=" * 60)
    print("Geração concluída com sucesso!")
    print("=" * 60)
'''
    
    return script


def executar_script_freecad(
    script: str,
    dados: DadosPlantaTecnica,
    formato_saida: List[str] = None
) -> Dict[str, bytes]:
    """
    Executa script no FreeCAD e retorna arquivos gerados.
    
    Args:
        script: Script Python para execução
        dados: Dados da planta técnica
        formato_saida: Lista de formatos desejados ['dwg', 'pdf', 'dwf']
        
    Returns:
        Dicionário com nome do arquivo e conteúdo em bytes
    """
    if formato_saida is None:
        formato_saida = dados.configuracao.formatos_saida
    
    resultados = {}
    
    # Verificar disponibilidade do FreeCAD
    if not _verificar_freecad_disponivel(dados.configuracao):
        logger.warning("FreeCAD não disponível. Usando fallback para DXF.")
        return _gerar_fallback_dxf(dados, formato_saida)
    
    # Criar diretório temporário
    with tempfile.TemporaryDirectory() as tmpdir:
        # Salvar script
        script_path = Path(tmpdir) / "gerar_planta.py"
        script_path.write_text(script, encoding='utf-8')
        
        # Preparar comando FreeCAD
        cmd = [
            dados.configuracao.freecad_path,
            "--console",
            str(script_path)
        ]
        
        try:
            # Executar FreeCAD
            logger.info(f"Executando FreeCAD: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=tmpdir,
                creationflags=creation_flags
            )
            
            if result.returncode != 0:
                logger.error(f"FreeCAD falhou: {result.stderr}")
                return _gerar_fallback_dxf(dados, formato_saida)
            
            logger.info(f"FreeCAD output: {result.stdout}")
            
            # Exportar para formatos solicitados
            arquivo_base = Path(tmpdir) / f"planta_tecnica_{dados.projeto_id[:8]}"
            
            for formato in formato_saida:
                formato = formato.lower().strip()
                
                if formato in ['dwg', 'dxf']:
                    # Exportar via ezdxf (já que FreeCAD pode não ter suporte nativo a DWG)
                    conteudo = _exportar_para_dxf(dados)
                    extensao = 'dwg' if formato == 'dwg' else 'dxf'
                    resultados[f"planta_tecnica.{extensao}"] = conteudo
                    
                elif formato == 'pdf':
                    # Tentar exportar PDF via FreeCAD Drawing workbench
                    pdf_path = arquivo_base.with_suffix('.pdf')
                    # Nota: Exportação PDF requer configuração adicional no script
                    # Por enquanto, usamos fallback
                    logger.warning("Exportação PDF requer configuração adicional")
                    
                elif formato == 'dwf':
                    logger.warning("Formato DWF não suportado diretamente")
            
            # Ler arquivo FCStd se necessário
            fcstd_path = arquivo_base.with_suffix('.FCStd')
            if fcstd_path.exists():
                resultados["planta_tecnica.FCStd"] = fcstd_path.read_bytes()
                
        except subprocess.TimeoutExpired:
            logger.error("Timeout na execução do FreeCAD")
            return _gerar_fallback_dxf(dados, formato_saida)
        except Exception as e:
            logger.error(f"Erro na execução do FreeCAD: {e}")
            return _gerar_fallback_dxf(dados, formato_saida)
    
    return resultados


def _gerar_fallback_dxf(dados: DadosPlantaTecnica, formatos: List[str]) -> Dict[str, bytes]:
    """
    Gera arquivo DXF como fallback quando FreeCAD não está disponível.
    Usa biblioteca ezdxf já incluída no projeto.
    """
    import ezdxf
    from ezdxf import units
    
    resultados = {}
    
    # Criar documento DXF
    doc = ezdxf.new(setup=True)
    doc.units = units.M  # Usar 'M' para metros ao invés de 'METER'
    
    msp = doc.modelspace()
    
    # Adicionar camada para perímetro (lineweight em unidades DXF: 35 = 0.35mm)
    doc.layers.add('PERIMETRO', color=7, lineweight=50)  # 0.50mm
    doc.layers.add('TEXTOS', color=7, lineweight=25)     # 0.25mm
    doc.layers.add('COTAS', color=8, lineweight=25)      # 0.25mm
    doc.layers.add('CARIMBO', color=7, lineweight=35)    # 0.35mm
    
    # Normalizar coordenadas
    offset_x = dados.centroide['x']
    offset_y = dados.centroide['y']
    
    vertices_norm = []
    for v in dados.vertices:
        vertices_norm.append((
            float(v.get('x', 0)) - offset_x,
            float(v.get('y', 0)) - offset_y,
            float(v.get('z', 0))
        ))
    
    # Desenhar perímetro
    if len(vertices_norm) >= 2:
        msp.add_lwpolyline(
            [(x, y) for x, y, z in vertices_norm],
            close=True,
            dxfattribs={'layer': 'PERIMETRO'}
        )
    
    # Adicionar números dos vértices
    for i, (x, y, z) in enumerate(vertices_norm):
        codigo = dados.vertices[i].get('codigo', f'V{i+1:03d}')
        msp.add_text(
            codigo,
            dxfattribs={
                'height': 2.5,
                'layer': 'TEXTOS',
            }
        ).set_placement((x + 2, y + 2))
    
    # Adicionar carimbo simplificado
    x_carimbo = dados.bbox['max_x'] - offset_x - 180
    y_carimbo = dados.bbox['min_y'] - offset_y
    
    # Bordas do carimbo
    msp.add_lwpolyline([
        (x_carimbo, y_carimbo),
        (x_carimbo + 180, y_carimbo),
        (x_carimbo + 180, y_carimbo + 45),
        (x_carimbo, y_carimbo + 45),
        (x_carimbo, y_carimbo),
    ], dxfattribs={'layer': 'CARIMBO'})
    
    # Textos do carimbo
    textos_carimbo = [
        (f"PROJETO: {dados.projeto_nome}", (x_carimbo + 2, y_carimbo + 35)),
        (f"IMÓVEL: {dados.nome_imovel}", (x_carimbo + 2, y_carimbo + 25)),
        (f"ÁREA: {dados.area_ha:.4f} ha", (x_carimbo + 2, y_carimbo + 15)),
        (f"TÉCNICO: {dados.tecnico_nome}", (x_carimbo + 100, y_carimbo + 35)),
        (f"CRT: {dados.tecnico_crt}", (x_carimbo + 100, y_carimbo + 25)),
        (f"DATA: {dados.data_levantamento}", (x_carimbo + 100, y_carimbo + 15)),
    ]
    
    for texto, pos in textos_carimbo:
        msp.add_text(
            texto,
            dxfattribs={'height': 2.0, 'layer': 'TEXTOS'}
        ).set_placement(pos)
    
    # Exportar DXF
    texto_buffer = io.StringIO()
    doc.write(texto_buffer)
    dxf_bytes = texto_buffer.getvalue().encode("utf-8")
    resultados["planta_tecnica.dxf"] = dxf_bytes
    
    # Se solicitado DWG, usar mesmo conteúdo (na prática precisaria de conversor)
    if 'dwg' in formatos:
        resultados["planta_tecnica.dwg"] = dxf_bytes
    
    return resultados


def gerar_planta_tecnica(
    supabase,
    projeto_id: str,
    formatos_saida: List[str] = None,
    configuracao: ConfiguracaoFreeCAD = None
) -> Dict[str, bytes]:
    """
    Função principal para geração de planta técnica.
    
    Args:
        supabase: Cliente Supabase
        projeto_id: UUID do projeto
        formatos_saida: Lista de formatos ['dwg', 'dxf', 'pdf', 'dwf']
        configuracao: Configurações opcionais de geração
        
    Returns:
        Dicionário com arquivos gerados {nome_arquivo: bytes}
        
    Example:
        >>> arquivos = gerar_planta_tecnica(supabase, "uuid-projeto")
        >>> for nome, conteudo in arquivos.items():
        ...     with open(f"/tmp/{nome}", "wb") as f:
        ...         f.write(conteudo)
    """
    if formatos_saida is None:
        formatos_saida = ["dxf", "dwg"]
    
    if configuracao is None:
        configuracao = ConfiguracaoFreeCAD()
    
    configuracao.formatos_saida = formatos_saida
    
    # Buscar dados do projeto
    dados = _buscar_dados_planta(supabase, projeto_id)
    dados.configuracao = configuracao
    
    logger.info(f"Gerando planta técnica para projeto {dados.projeto_nome}")
    logger.info(f"Formatos solicitados: {formatos_saida}")
    
    # ─── Tentar processar remotamente no VERTEXROSEA (CAD Engine Stateless) ─────
    try:
        import asyncio
        import httpx
        from integracoes.vertex_client import vertex_client
        
        async def chamar_vertex():
            # Converte vértices para o formato esperado pelo Vertex
            vertices_payload = [
                {
                    "codigo": v.get("codigo", f"V{idx+1:02d}"),
                    "x": float(v.get("x") or 0.0),
                    "y": float(v.get("y") or 0.0),
                    "z": float(v.get("z") or 0.0)
                }
                for idx, v in enumerate(dados.vertices)
            ]
            
            logger.info("Enviando job FreeCAD para VERTEXROSEA...")
            job_info = await vertex_client.disparar_job_freecad(
                project_id=dados.projeto_id,
                codigo_projeto=dados.projeto_nome,
                vertices=vertices_payload
            )
            
            job_id = job_info.get("job_id")
            if not job_id:
                raise ValueError("Job ID não retornado pelo VERTEXROSEA")
                
            logger.info("Job %s submetido com sucesso. Aguardando conclusão no Vertex...", job_id)
            
            # Polling rápido (máximo de 15 segundos para fins síncronos)
            for _ in range(15):
                await asyncio.sleep(1.0)
                status_info = await vertex_client.obter_status_job(job_id)
                status = status_info.get("status")
                
                if status == "done":
                    artifacts = status_info.get("artifacts", [])
                    logger.info("Job %s concluído pelo VERTEXROSEA com %d artefatos.", job_id, len(artifacts))
                    
                    # Baixa os arquivos resultantes em bytes para manter compatibilidade
                    arquivos_bytes = {}
                    async with httpx.AsyncClient() as client:
                        for art in artifacts:
                            url_download = art.get("url")
                            kind = art.get("kind")
                            if url_download and kind:
                                resp = await client.get(url_download)
                                if resp.status_code == 200:
                                    ext = "fcstd" if kind.lower() == "fcstd" else kind.lower()
                                    arquivos_bytes[f"planta_tecnica.{ext}"] = resp.content
                    
                    if arquivos_bytes:
                        return arquivos_bytes
                    raise ValueError("Nenhum arquivo de artefato pôde ser baixado com sucesso")
                    
                elif status == "failed":
                    warnings = status_info.get("warnings", [])
                    raise RuntimeError(f"Job falhou no VERTEXROSEA: {warnings}")
            
            raise TimeoutError("Tempo limite esgotado para o job no VERTEXROSEA")

        # Executa no event loop de forma isolada e segura
        try:
            loop = asyncio.new_event_loop()
            resultados = loop.run_until_complete(chamar_vertex())
            loop.close()
        except Exception:
            resultados = asyncio.run(chamar_vertex())
            
        logger.info(f"Plantas geradas via VERTEXROSEA com sucesso: {list(resultados.keys())}")
        return resultados

    except Exception as e:
        logger.warning(
            "Conexão com VERTEXROSEA indisponível ou falhou (%s). Usando processamento local como fallback...",
            e,
            exc_info=True
        )

    # ─── Fallback Legado: Geração de Script e Execução Local ──────────────────
    # Gerar script FreeCAD
    script = gerar_script_freecad(dados)
    
    # Executar e obter resultados
    resultados = executar_script_freecad(script, dados, formatos_saida)
    
    logger.info(f"Plantas geradas via Fallback Local: {list(resultados.keys())}")
    
    return resultados


# ============================================================
# TESTES E VALIDAÇÃO
# ============================================================

def _testar_geracao_mock():
    """Testa geração com dados mock."""
    from dataclasses import replace
    
    dados_mock = DadosPlantaTecnica(
        projeto_id="test-001",
        projeto_nome="Fazenda Teste",
        numero_job="JOB-001",
        nome_imovel="Fazenda Teste",
        municipio="Pirenópolis",
        estado="GO",
        matricula="12345",
        comarca="Pirenópolis",
        area_ha=45.6789,
        area_m2=456789.0,
        perimetro_m=2500.0,
        vertices=[
            {"x": 800000, "y": 8200000, "z": 1172, "codigo": "V01"},
            {"x": 800050, "y": 8200000, "z": 1171, "codigo": "V02"},
            {"x": 800050, "y": 8200050, "z": 1170, "codigo": "V03"},
            {"x": 800000, "y": 8200050, "z": 1171, "codigo": "V04"},
        ],
        centroide={"x": 800025, "y": 8200025},
        bbox={"min_x": 800000, "max_x": 800050, "min_y": 8200000, "max_y": 8200050},
        cliente_nome="João da Silva",
        cliente_cpf="123.456.789-00",
        cliente_documento="1234567",
        tecnico_nome="Hugo Desenrola",
        tecnico_crt="CRT-GO-1234",
        tecnico_crea="",
        tecnico_cpf="987.654.321-00",
        tecnico_codigo_incra="INCRA-001",
        confrontantes=[
            {"lado": "Norte", "nome": "Pedro Confrontante", "cpf": "111.222.333-44"},
            {"lado": "Sul", "nome": "Maria Vizinha", "cpf": "555.666.777-88"},
        ],
        pontos_ammarracao=[],
        data_levantamento="24/05/2025",
        data_processamento="24/05/2025",
    )
    
    print("\n" + "=" * 60)
    print("TESTE - Geração de Planta Técnica (Mock)")
    print("=" * 60)
    
    # Gerar script
    script = gerar_script_freecad(dados_mock)
    print(f"\nScript gerado: {len(script)} caracteres")
    print("Primeiras linhas do script:")
    print("-" * 40)
    for linha in script.split('\n')[:20]:
        print(linha)
    print("-" * 40)
    
    # Testar fallback DXF
    print("\nTestando fallback DXF...")
    resultados = _gerar_fallback_dxf(dados_mock, ["dxf", "dwg"])
    
    for nome, conteudo in resultados.items():
        print(f"  [OK] {nome}: {len(conteudo)} bytes")
    
    print("\n" + "=" * 60)
    print("TESTE CONCLUÍDO")
    print("=" * 60 + "\n")
    
    return True


if __name__ == "__main__":
    sucesso = _testar_geracao_mock()
    exit(0 if sucesso else 1)
