"""
GeoAdmin Pro - Modelos de Dados

Esquemas Pydantic e tipos compartilhados.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class DadosFormulario(BaseModel):
    """Dados do formulário do cliente."""
    nome: str
    cpf: str
    rg: str
    estado_civil: str
    profissao: Optional[str] = ""
    telefone: str
    email: Optional[str] = ""
    conjuge_nome: Optional[str] = ""
    conjuge_cpf: Optional[str] = ""
    endereco: str
    endereco_numero: Optional[str] = ""
    municipio: str
    cep: Optional[str] = ""
    nome_imovel: str
    municipio_imovel: str
    endereco_imovel: Optional[str] = ""
    endereco_imovel_numero: Optional[str] = ""
    cep_imovel: Optional[str] = ""
    comarca: Optional[str] = ""
    matricula: Optional[str] = ""
    tempo_posse_anos: Optional[int] = None
    confrontantes: list = []
    area_nome: Optional[str] = ""
    ccir: Optional[str] = ""
    car: Optional[str] = ""
    observacoes: Optional[str] = ""
    croqui_coords: Optional[str] = ""
    croqui_svg: Optional[str] = ""


class GerarMagicLinksLotePayload(BaseModel):
    """Payload para geração de magic links em lote."""
    projeto_cliente_ids: list[str] = Field(default_factory=list)
    area_ids: list[str] = Field(default_factory=list)
    codigo_lotes: list[str] = Field(default_factory=list)
    dias: int = 7
    canal: str = "whatsapp"
    autor: Optional[str] = None
    somente_habilitados: bool = True


class HealthCheck(BaseModel):
    """Resposta de health check."""
    status: str = "ok"


class ErrorResponse(BaseModel):
    """Resposta de erro padronizada."""
    erro: str
    codigo: int
    detalhes: Optional[dict] = None
