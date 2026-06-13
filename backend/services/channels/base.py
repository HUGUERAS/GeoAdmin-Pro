import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ChannelProviderBase:
    """Classe abstrata para envio de mensagens em canais externos."""
    
    def __init__(self):
        self.provider_name = "base"

    def send_message(self, telefone: str, conteudo: str, dry_run: bool = True) -> Dict[str, Any]:
        """
        Envia (ou simula) a mensagem.
        Deve retornar dict com:
        - success: bool
        - provider_message_id: str (opcional)
        - error: str (se falhar)
        - payload_sent: dict (o que foi tentado)
        """
        raise NotImplementedError("Providers devem implementar send_message")
