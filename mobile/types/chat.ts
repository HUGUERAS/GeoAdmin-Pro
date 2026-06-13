export interface ChatMessage {
  id: string;
  role: 'user' | 'bot';
  content: string;
  timestamp: string;
}

export interface ChatRequest {
  mensagem: string;
  projeto_id: string;
  sessao_id?: string;
}

export interface ChatResponse {
  sessao_id: string;
  resposta: string;
  agente_id?: string | null;
  metadados?: any;
}
