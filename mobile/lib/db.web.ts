/**
 * mobile/lib/db.web.ts
 * Stub para web — usa localStorage no lugar de SQLite.
 * Metro resolve este arquivo automaticamente na plataforma web.
 */

export type SyncStatus = 'pending' | 'synced' | 'error'

export interface PontoLocal {
  id: string
  projeto_id: string
  nome: string
  lat: number
  lon: number
  norte: number
  este: number
  cota: number
  codigo: string
  status_gnss: string
  satelites: number
  pdop: number
  sigma_e: number
  sigma_n: number
  sigma_u: number
  origem: string
  coletado_em: string
  sync_status: SyncStatus
  sync_tentativas: number
  sync_em?: string
}

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
