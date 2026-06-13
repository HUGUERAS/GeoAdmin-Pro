from .base import ChannelProviderBase
from .whatsapp import WhatsAppProvider
from .hermes import HermesProvider

def get_channel_provider(canal: str) -> ChannelProviderBase:
    if canal.lower() == 'hermes':
        return HermesProvider()
    elif canal.lower() == 'whatsapp':
        return WhatsAppProvider()
    raise ValueError(f"Canal nao suportado: {canal}")
