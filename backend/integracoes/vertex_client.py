"""
GeoAdmin Pro - Cliente de Integração com VERTEXROSEA

Implementa o canal de comunicação via HTTP/REST com a Engine Técnica de CAD (stateless).
Permite validar DXF, extrair pontos, analisar TXT e orquestrar Jobs assíncronos do FreeCAD.
"""

import logging
from typing import Dict, Any, List, Optional
import httpx
from core import settings

logger = logging.getLogger("geoadmin.integracoes.vertex")

class VertexClient:
    """Cliente HTTP para comunicação com o microserviço VERTEXROSEA."""

    def __init__(self):
        self.base_url = settings.VERTEXROSEA_API_URL.rstrip("/")
        self.api_key = settings.VERTEXROSEA_API_KEY
        self.headers = {}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
        logger.info("VertexClient inicializado apontando para %s", self.base_url)

    async def _request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        timeout: float = 10.0
    ) -> Dict[str, Any]:
        """Executa requisições HTTP de forma resiliente."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        
        async with httpx.AsyncClient(headers=self.headers, timeout=timeout) as client:
            try:
                if method.upper() == "POST":
                    logger.debug("POST request para %s com json: %s, data: %s, files: %s", url, json_data, data, files)
                    response = await client.post(url, json=json_data, data=data, files=files)
                else:
                    logger.debug("GET request para %s", url)
                    response = await client.get(url)
                
                # Se o status code for 4xx ou 5xx, dispara httpx.HTTPStatusError
                response.raise_for_status()
                return response.json()
            
            except httpx.ConnectError as e:
                logger.error("Erro de conexão ao tentar falar com o VERTEXROSEA em %s: %s", url, e)
                raise ConnectionError(f"Não foi possível conectar ao VERTEXROSEA em {url}.")
            except httpx.TimeoutException as e:
                logger.error("Timeout na chamada ao VERTEXROSEA (%s): %s", url, e)
                raise TimeoutError(f"A requisição ao VERTEXROSEA em {url} excedeu o tempo limite de {timeout}s.")
            except httpx.HTTPStatusError as e:
                logger.error(
                    "VERTEXROSEA respondeu com erro HTTP %d em %s: %s",
                    e.response.status_code,
                    url,
                    e.response.text,
                )
                raise ValueError(
                    f"Erro retornado pela Engine do VERTEXROSEA: {e.response.status_code} - {e.response.text}"
                )
            except Exception as e:
                logger.error("Erro desconhecido ao chamar VERTEXROSEA: %s", e, exc_info=True)
                raise RuntimeError(f"Falha na integração com VERTEXROSEA: {e}")

    async def validar_dxf(self, conteudo: bytes, filename: str, layer: Optional[str] = None) -> Dict[str, Any]:
        """
        Solicita validação técnica de um DXF no VERTEXROSEA enviando os bytes via multipart.
        
        Retorna dicionário informando se é válido, avisos e metadados.
        """
        files = {"arquivo": (filename, conteudo, "application/octet-stream")}
        data = {}
        if layer:
            data["layer"] = layer
        return await self._request("POST", "/cad/dxf/validar", files=files, data=data)

    async def extrair_pontos_dxf(self, conteudo: bytes, filename: str, fuso: str, hemisferio: str, layer: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Solicita extração das coordenadas dos pontos de um DXF enviando os bytes via multipart.
        """
        files = {"arquivo": (filename, conteudo, "application/octet-stream")}
        data = {"fuso": fuso, "hemisferio": hemisferio}
        if layer:
            data["layer"] = layer
        resultado = await self._request("POST", "/cad/dxf/pontos", files=files, data=data)
        return resultado.get("pontos", [])

    async def parse_txt_coletora(self, conteudo: bytes, filename: str, fuso: Optional[str] = None, hemisferio: Optional[str] = None, formato: str = "metrica_topo") -> Dict[str, Any]:
        """
        Faz o parseamento e normalização técnica de arquivo de coletora (LandStar/Métrica) via multipart.
        """
        files = {"arquivo": (filename, conteudo, "application/octet-stream")}
        data = {"formato": formato}
        if fuso:
            data["fuso"] = fuso
        if hemisferio:
            data["hemisferio"] = hemisferio
        return await self._request("POST", "/cad/txt/parse", files=files, data=data)

    async def disparar_job_freecad(self, contrato_vertex: Dict[str, Any], project_ref: str, save_fcstd: bool = True, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Inicia um heavy job assíncrono para geração de peças técnicas via FreeCAD no VERTEXROSEA.
        """
        payload = {
            "contrato_vertex": contrato_vertex,
            "project_ref": project_ref,
            "save_fcstd": save_fcstd
        }
        if output_dir:
            payload["output_dir"] = output_dir
            
        # O timeout para criação do job é baixo, pois o processamento é delegado assincronamente
        return await self._request("POST", "/cad/jobs/freecad", json_data=payload, timeout=5.0)

    async def obter_status_job(self, job_id: str) -> Dict[str, Any]:
        """
        Faz o polling de status de um job assíncrono.
        """
        return await self._request("GET", f"/cad/jobs/{job_id}", timeout=5.0)

# Instância única global do cliente
vertex_client = VertexClient()
