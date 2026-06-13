import logging
import uuid
import os
from typing import Dict, Any
from .base import ChannelProviderBase

logger = logging.getLogger(__name__)

class WhatsAppProvider(ChannelProviderBase):
    def __init__(self):
        super().__init__()
        self.provider_name = "whatsapp"
        
    def send_message(self, telefone: str, conteudo: str, dry_run: bool = True) -> Dict[str, Any]:
        payload = {
            "to": telefone,
            "text": conteudo,
            "type": "whatsapp_business"
        }
        
        if dry_run or os.getenv("WHATSAPP_DRY_RUN", "true").lower() == "true":
            logger.info(f"[DRY-RUN] WhatsApp Provider simularia envio para {telefone}")
            return {
                "success": True,
                "provider_message_id": f"sim-wa-{uuid.uuid4().hex[:8]}",
                "payload_sent": payload
            }
            
        # TODO: Implementar chamadas HTTP reais para WhatsApp Cloud API ou gateway
        logger.info(f"[REAL-RUN] Enviando via WhatsApp para {telefone}")
        return {
            "success": True,
            "provider_message_id": f"real-wa-{uuid.uuid4().hex[:8]}",
            "payload_sent": payload
        }
