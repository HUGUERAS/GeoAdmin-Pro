import { Platform } from 'react-native';

const DEFAULT_API_BASE_URL = 'https://geoadmin-pro-api-njpsk7knsa-rj.a.run.app';

export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

// Token de autenticação do Supabase — defina via definirToken()
let _authToken: string | null = null;

export function definirToken(token: string | null): void {
  _authToken = token;
}

function getExplicitApiBaseUrl(): string | null {
  const explicitUrl = process.env.EXPO_PUBLIC_API_BASE_URL?.trim();
  return explicitUrl ? explicitUrl.replace(/\/+$/, '') : null;
}

function getApiBaseUrlWeb(): string {
  const explicitUrl = getExplicitApiBaseUrl();
  if (explicitUrl) {
    return explicitUrl;
  }

  // Detecção dinâmica de localhost em desenvolvimento Web
  if (typeof window !== 'undefined' && window.location) {
    const hostname = window.location.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname.startsWith('192.168.')) {
      return 'http://localhost:8000';
    }
  }

  return DEFAULT_API_BASE_URL;
}

export function getApiBaseUrl(): string {
  const explicitUrl = getExplicitApiBaseUrl();
  if (explicitUrl) {
    return explicitUrl;
  }

  if (Platform.OS === 'web') {
    return getApiBaseUrlWeb();
  }

  // Fallback seguro em desenvolvimento local para emuladores
  if (__DEV__) {
    // 10.0.2.2 é o IP padrão do host no emulador Android
    return 'http://10.0.2.2:8000';
  }

  return DEFAULT_API_BASE_URL;
}

function formatErrorDetail(detail: JsonValue | undefined): string {
  if (!detail) {
    return 'Falha na comunicação com o backend.';
  }

  if (typeof detail === 'string') {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail.map((item) => formatErrorDetail(item)).join(' | ');
  }

  if (typeof detail === 'object') {
    if (typeof detail.erro === 'string') {
      return detail.erro;
    }

    return Object.entries(detail)
      .map(([key, value]) => `${key}: ${formatErrorDetail(value)}`)
      .join(' | ');
  }

  return String(detail);
}

/**
 * Envoltório para fetch com timeout automático.
 * Aborta a requisição se ultrapassar timeoutMs.
 */
function fetchComTimeout(
  url: string,
  opcoes?: RequestInit,
  timeoutMs = 15000
): Promise<Response> {
  const controlador = new AbortController();
  const timer = setTimeout(() => controlador.abort(), timeoutMs);

  return fetch(url, { ...opcoes, signal: controlador.signal }).finally(() =>
    clearTimeout(timer)
  );
}

async function parseResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get('content-type') ?? '';
  const payload = contentType.includes('application/json')
    ? ((await response.json()) as JsonValue)
    : ((await response.text()) as JsonValue);

  if (!response.ok) {
    if (typeof payload === 'object' && payload && 'detail' in payload) {
      throw new Error(formatErrorDetail(payload.detail as JsonValue));
    }

    throw new Error(formatErrorDetail(payload));
  }

  return payload as T;
}

/**
 * Mapeia erros de timeout e abort para mensagens amigáveis.
 */
function tratarErroFetch(erro: unknown): Error {
  if (erro instanceof DOMException && erro.name === 'AbortError') {
    return new Error('Requisição expirou — o servidor levou muito tempo para responder.');
  }
  if (erro instanceof Error) {
    return erro;
  }
  return new Error(String(erro));
}

export async function apiGet<T>(path: string): Promise<T> {
  try {
    const headers: Record<string, string> = {
      'Bypass-Tunnel-Reminder': 'true'
    };
    if (_authToken) {
      headers['Authorization'] = `Bearer ${_authToken}`;
    }
    const response = await fetchComTimeout(`${getApiBaseUrl()}${path}`, {
      headers,
    });
    return parseResponse<T>(response);
  } catch (erro) {
    throw tratarErroFetch(erro);
  }
}

export async function apiPost<T>(path: string, body: JsonValue): Promise<T> {
  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (_authToken) {
      headers['Authorization'] = `Bearer ${_authToken}`;
    }
    const response = await fetchComTimeout(`${getApiBaseUrl()}${path}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });

    return parseResponse<T>(response);
  } catch (erro) {
    throw tratarErroFetch(erro);
  }
}

export async function apiPostFormData<T>(path: string, body: FormData): Promise<T> {
  try {
    const headers: Record<string, string> = {
      'Bypass-Tunnel-Reminder': 'true'
    };
    if (_authToken) {
      headers['Authorization'] = `Bearer ${_authToken}`;
    }
    const response = await fetchComTimeout(`${getApiBaseUrl()}${path}`, {
      method: 'POST',
      headers,
      body,
    });

    return parseResponse<T>(response);
  } catch (erro) {
    throw tratarErroFetch(erro);
  }
}

export async function apiPatch<T>(path: string, body: JsonValue): Promise<T> {
  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (_authToken) {
      headers['Authorization'] = `Bearer ${_authToken}`;
    }
    const response = await fetchComTimeout(`${getApiBaseUrl()}${path}`, {
      method: 'PATCH',
      headers,
      body: JSON.stringify(body),
    });

    return parseResponse<T>(response);
  } catch (erro) {
    throw tratarErroFetch(erro);
  }
}

export async function apiDelete<T>(path: string): Promise<T> {
  try {
    const headers: Record<string, string> = {
      'Bypass-Tunnel-Reminder': 'true'
    };
    if (_authToken) {
      headers['Authorization'] = `Bearer ${_authToken}`;
    }
    const response = await fetchComTimeout(`${getApiBaseUrl()}${path}`, {
      method: 'DELETE',
      headers,
    });

    return parseResponse<T>(response);
  } catch (erro) {
    throw tratarErroFetch(erro);
  }
}


export async function enviarMensagemChat(projetoId: string, mensagem: string): Promise<{ resposta: string }> {
  return apiPost<{ resposta: string }>('/chat/', { projeto_id: projetoId, mensagem });
}
