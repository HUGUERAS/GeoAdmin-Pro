import { useEffect, useState, useRef } from 'react';

type EventType = 'inbound_received' | 'outbound_draft_created' | 'document_status_changed' | 'external_message_status_changed' | 'operational_summary_changed';

interface RealtimeEvent {
  type: EventType;
  project_id: string;
  data: any;
}

export function useProjetoRealtime(projetoId: string, token: string | null) {
  const [status, setStatus] = useState<'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error'>('disconnected');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  
  // Callbacks globais, podem ser refatorados para um EventEmitter ou Context
  const [lastEvent, setLastEvent] = useState<RealtimeEvent | null>(null);

  useEffect(() => {
    if (!projetoId || !token) return;

    let isMounted = true;
    let attempt = 0;

    const connect = () => {
      if (wsRef.current?.readyState === WebSocket.OPEN) return;
      
      setStatus(attempt === 0 ? 'connecting' : 'reconnecting');
      
      // Simulação da rota: em producao pegar variavel de ambiente
      // const wsUrl = `wss://api.meusistema.com/ws/projetos/${projetoId}/operacional?token=${token}`;
      const wsUrl = `ws://localhost:8000/ws/projetos/${projetoId}/operacional?token=${token}`;
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isMounted) return;
        setStatus('connected');
        attempt = 0;
      };

      ws.onmessage = (event) => {
        if (!isMounted) return;
        try {
          const data = JSON.parse(event.data);
          if (data.type) {
            setLastEvent(data);
          }
        } catch (e) {
          console.warn("Falha ao parsear WS payload", e);
        }
      };

      ws.onclose = (event) => {
        if (!isMounted) return;
        setStatus('disconnected');
        
        // 1008 = Policy Violation (token invalido, sem permissão, etc), não reconecta
        if (event.code !== 1008) {
          // Backoff exponencial para reconectar
          const delay = Math.min(1000 * Math.pow(2, attempt), 30000);
          attempt++;
          reconnectTimeout.current = setTimeout(connect, delay);
        } else {
          setStatus('error');
        }
      };

      ws.onerror = () => {
        if (!isMounted) return;
        // o `onclose` será chamado em seguida
      };
    };

    connect();

    // Cleanup unmount
    return () => {
      isMounted = false;
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      if (wsRef.current) {
        wsRef.current.close(1000, "Unmount");
      }
    };
  }, [projetoId, token]);

  return { status, lastEvent };
}
