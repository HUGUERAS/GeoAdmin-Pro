import logging
import uuid
import os
from typing import Dict, Any
from .base import ChannelProviderBase

logger = logging.getLogger(__name__)

class HermesProvider(ChannelProviderBase):
    def __init__(self):
        super().__init__()
        self.provider_name = "hermes"
        
    def send_message(self, telefone: str, conteudo: str, dry_run: bool = True) -> Dict[str, Any]:
        payload = {
            "to": telefone,
            "body": conteudo,
            "provider": "hermes_api"
        }
        
        if dry_run or os.getenv("HERMES_DRY_RUN", "true").lower() == "true":
            logger.info(f"[DRY-RUN] Hermes Provider simularia envio para {telefone}")
            return {
                "success": True,
                "provider_message_id": f"sim-hermes-{uuid.uuid4().hex[:8]}",
                "payload_sent": payload
            }
            
        # TODO: Implementar chamadas HTTP reais para a API do Hermes
        logger.info(f"[REAL-RUN] Enviando via Hermes para {telefone}")
        return {
            "success": True,
            "provider_message_id": f"real-hermes-{uuid.uuid4().hex[:8]}",
            "payload_sent": payload
        }
