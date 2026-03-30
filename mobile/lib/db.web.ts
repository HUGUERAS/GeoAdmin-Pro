/**
 * mobile/lib/db.web.ts
 * Stub para web — usa localStorage no lugar de SQLite.
 * Metro resolve este arquivo automaticamente na plataforma web.
 */

import { SyncStatus, PontoLocal } from '../types/ponto'

export { SyncStatus, PontoLocal }

export async function initDB(): Promise<void> {}

export async function salvarPonto(_p: Omit<PontoLocal, 'sync_status' | 'sync_tentativas'>): Promise<string> {
  return _p.id
}

export async function listarPendentes(_projeto_id?: string): Promise<PontoLocal[]> { return [] }
export async function listarPorProjeto(_projeto_id: string): Promise<PontoLocal[]> { return [] }
export async function marcarSincronizado(_id: string): Promise<void> {}
export async function marcarErro(_id: string): Promise<void> {}
export async function contarPendentes(_projeto_id?: string): Promise<number> { return 0 }
export async function ultimoNomePonto(_projeto_id: string): Promise<string> { return 'PT0001' }
export async function initAppConfig(): Promise<void> {}

export async function marcarResultadosBatch(_sincronizados: string[], _erros: string[]): Promise<void> {}
export async function contarErros(_projeto_id?: string): Promise<number> { return 0 }
export async function resetarErros(_projeto_id?: string): Promise<void> {}

export async function salvarUltimoProjetoMapa(projeto_id: string): Promise<void> {
  try { localStorage.setItem('ultimo_projeto_mapa', projeto_id) } catch {}
}

export async function obterUltimoProjetoMapa(): Promise<string | null> {
  try { return localStorage.getItem('ultimo_projeto_mapa') } catch { return null }
}

// ── Cache de projetos via localStorage ───────────────────────────────────────

export async function initProjetosCache(): Promise<void> {}

export async function cacheProjetos(projetos: any[]): Promise<void> {
  try { localStorage.setItem('projetos_cache', JSON.stringify(projetos)) } catch {}
}

export async function getCachedProjetos(): Promise<any[]> {
  try {
    const raw = localStorage.getItem('projetos_cache')
    return raw ? JSON.parse(raw) : []
  } catch { return [] }
}

export async function cacheProjetoDetalhe(id: string, projeto: any): Promise<void> {
  try { localStorage.setItem(`projeto_cache_${id}`, JSON.stringify(projeto)) } catch {}
}

export async function getCachedProjetoDetalhe(id: string): Promise<any | null> {
  try {
    const raw = localStorage.getItem(`projeto_cache_${id}`)
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}

