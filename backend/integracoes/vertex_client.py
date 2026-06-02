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

    async def validar_dxf(self, conteudo: bytes, filename: str) -> Dict[str, Any]:
        """
        Solicita validação técnica de um DXF no VERTEXROSEA enviando os bytes via multipart.
        
        Retorna dicionário informando se é válido, avisos e metadados.
        """
        files = {"file": (filename, conteudo, "application/octet-stream")}
        return await self._request("POST", "/cad/dxf/validar", files=files)

    async def extrair_pontos_dxf(self, conteudo: bytes, filename: str) -> List[Dict[str, Any]]:
        """
        Solicita extração das coordenadas dos pontos de um DXF enviando os bytes via multipart.
        """
        files = {"file": (filename, conteudo, "application/octet-stream")}
        resultado = await self._request("POST", "/cad/dxf/pontos", files=files)
        return resultado.get("pontos", [])

    async def parse_txt_coletora(self, conteudo: bytes, filename: str, formato: str = "metrica_topo") -> Dict[str, Any]:
        """
        Faz o parseamento e normalização técnica de arquivo de coletora (LandStar/Métrica) via multipart.
        """
        files = {"file": (filename, conteudo, "application/octet-stream")}
        data = {"formato": formato}
        return await self._request("POST", "/cad/txt/parse", files=files, data=data)

    async def disparar_job_freecad(self, project_id: str, codigo_projeto: str, vertices: List[Dict[str, Any]], download_url_dxf: Optional[str] = None) -> Dict[str, Any]:
        """
        Inicia um heavy job assíncrono para geração de peças técnicas via FreeCAD.
        """
        payload = {
            "project_ref": {"id": project_id, "codigo": codigo_projeto},
            "perimeter": {
                "source": "client_confirmed",
                "vertices": vertices
            },
            "outputs": ["fcstd", "dxf", "report"]
        }
        if download_url_dxf:
            payload["source_files"] = [{"kind": "dxf", "download_url": download_url_dxf}]
            
        # O timeout para criação do job é baixo, pois o processamento é delegado assincronamente
        return await self._request("POST", "/cad/jobs/freecad", json_data=payload, timeout=5.0)

    async def obter_status_job(self, job_id: str) -> Dict[str, Any]:
        """
        Faz o polling de status de um job assíncrono.
        """
        return await self._request("GET", f"/cad/jobs/{job_id}", timeout=5.0)

# Instância única global do cliente
vertex_client = VertexClient()
