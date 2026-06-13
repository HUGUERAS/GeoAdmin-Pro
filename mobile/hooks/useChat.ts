import { useState, useCallback, useEffect } from 'react';
import { apiPost, apiGet } from '../lib/api';
import { ChatMessage, ChatResponse, ChatRequest } from '../types/chat';

export function useChat(projetoId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessaoId, setSessaoId] = useState<string | null>(null);

  useEffect(() => {
    if (!projetoId) return;
    
    setLoading(true);
    // Tenta buscar o historico recente se a sessao for null
    apiGet<{sessao_id: string, mensagens: any[]}>(`/chat/sessoes/recente/mensagens?projeto_id=${projetoId}`)
      .then((data) => {
        setSessaoId(data.sessao_id);
        const mapped = data.mensagens.map(m => ({
          id: m.id || Math.random().toString(),
          role: m.role,
          content: m.conteudo,
          timestamp: m.criado_em || new Date().toISOString(),
        }));
        setMessages(mapped);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [projetoId]);

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim()) return;

    const userMessage: ChatMessage = {
      id: Math.random().toString(36).substring(7),
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);
    setError(null);

    try {
      const payload: ChatRequest = {
        projeto_id: projetoId,
        mensagem: text,
      };
      if (sessaoId) payload.sessao_id = sessaoId;

      const response = await apiPost<ChatResponse>('/chat', payload);

      if (response.sessao_id && !sessaoId) {
        setSessaoId(response.sessao_id);
      }

      const botMessage: ChatMessage = {
        id: Math.random().toString(36).substring(7),
        role: 'bot',
        content: response.resposta,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (err: any) {
      setError(err.message || 'Erro ao enviar mensagem.');
    } finally {
      setLoading(false);
    }
  }, [projetoId, sessaoId]);

  return {
    messages,
    sendMessage,
    loading,
    error,
  };
}
