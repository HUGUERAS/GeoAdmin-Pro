import Constants from 'expo-constants';
import { Platform } from 'react-native';

type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

// Token de autenticação do Supabase — defina via definirToken()
let _authToken: string | null = null;
const API_PUBLICA_PADRAO = 'https://geoadmin-pro-production.up.railway.app';

export function definirToken(token: string | null): void {
  _authToken = token;
}

function extractHostFromExpoConfig(): string | null {
  const expoConfigHost =
    (Constants.expoConfig as { hostUri?: string } | null)?.hostUri ??
    (Constants as { manifest2?: { extra?: { expoGo?: { debuggerHost?: string } } } }).manifest2
      ?.extra?.expoGo?.debuggerHost ??
    (Constants as { manifest?: { debuggerHost?: string } }).manifest?.debuggerHost;

  if (!expoConfigHost) {
    return null;
  }

  return expoConfigHost.split(':')[0] ?? null;
}

function getApiBaseUrlWeb(): string {
  if (typeof window === 'undefined') {
    return API_PUBLICA_PADRAO;
  }

  const { hostname, origin, port, protocol } = window.location;

  const hostLocal =
    hostname === 'localhost' ||
    hostname === '127.0.0.1' ||
    hostname.startsWith('192.168.') ||
    hostname.startsWith('10.') ||
    /^172\.(1[6-9]|2\d|3[0-1])\./.test(hostname);

  if (hostLocal && port === '8000') {
    return origin.replace(/\/+$/, '');
  }

  if (hostLocal && hostname) {
    return `${protocol}//${hostname}:8000`;
  }

  // Produção (Vercel/CDN): usar proxy relativo para evitar CORS
  return '/proxy';
}

export function getApiBaseUrl(): string {
  const explicitUrl = process.env.EXPO_PUBLIC_API_BASE_URL?.trim();
  if (explicitUrl) {
    return explicitUrl.replace(/\/+$/, '');
  }

  if (Platform.OS === 'web') {
    return getApiBaseUrlWeb();
  }

  const host = extractHostFromExpoConfig();
  if (host) {
    return `http://${host}:8000`;
  }

  if (Platform.OS === 'android') {
    return 'http://10.0.2.2:8000';
  }

  return 'http://127.0.0.1:8000';
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
    const headers: Record<string, string> = {};
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
    const headers: Record<string, string> = {};
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
    const headers: Record<string, string> = {};
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

