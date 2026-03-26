import Constants from 'expo-constants';
import { Platform } from 'react-native';

type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

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

export function getApiBaseUrl(): string {
  const explicitUrl = process.env.EXPO_PUBLIC_API_BASE_URL?.trim();
  if (explicitUrl) {
    return explicitUrl.replace(/\/+$/, '');
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

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`);
  return parseResponse<T>(response);
}

export async function apiPost<T>(path: string, body: JsonValue): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  return parseResponse<T>(response);
}

export async function apiPostFormData<T>(path: string, body: FormData): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: 'POST',
    body,
  });

  return parseResponse<T>(response);
}

export async function apiPatch<T>(path: string, body: JsonValue): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  return parseResponse<T>(response);
}

export async function apiDelete<T>(path: string): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: 'DELETE',
  });

  return parseResponse<T>(response);
}
