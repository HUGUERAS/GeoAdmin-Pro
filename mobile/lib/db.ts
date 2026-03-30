/**
 * mobile/lib/db.ts
 * SQLite local para coleta offline de pontos GNSS.
 * expo-sqlite v14 já vem no Expo SDK 54 — sem npm install.
 */

import * as SQLite from 'expo-sqlite'
import { SyncStatus, PontoLocal } from '../types/ponto'

export { SyncStatus, PontoLocal }

let _db: SQLite.SQLiteDatabase | null = null

function getDb(): SQLite.SQLiteDatabase {
  if (!_db) _db = SQLite.openDatabaseSync('geoadmin.db')
  return _db
}

export async function initDB(): Promise<void> {
  const db = getDb()
  await db.execAsync(`
    CREATE TABLE IF NOT EXISTS pontos_locais (
      id              TEXT PRIMARY KEY,
      projeto_id      TEXT NOT NULL,
      nome            TEXT NOT NULL,
      lat             REAL NOT NULL,
      lon             REAL NOT NULL,
      norte           REAL NOT NULL,
      este            REAL NOT NULL,
      cota            REAL NOT NULL,
      codigo          TEXT DEFAULT 'TP',
      status_gnss     TEXT DEFAULT 'Fixo',
      satelites       INTEGER DEFAULT 0,
      pdop            REAL DEFAULT 0,
      sigma_e         REAL DEFAULT 0,
      sigma_n         REAL DEFAULT 0,
      sigma_u         REAL DEFAULT 0,
      origem          TEXT DEFAULT 'bluetooth',
      coletado_em     TEXT NOT NULL,
      sync_status     TEXT DEFAULT 'pending',
      sync_tentativas INTEGER DEFAULT 0,
      sync_em         TEXT
    );
  `)
  await initProjetosCache()
  await initAppConfig()
}

export async function salvarPonto(p: Omit<PontoLocal, 'sync_status' | 'sync_tentativas'>): Promise<string> {
  const db = getDb()
  await db.runAsync(
    `INSERT INTO pontos_locais
      (id, projeto_id, nome, lat, lon, norte, este, cota, codigo, status_gnss,
       satelites, pdop, sigma_e, sigma_n, sigma_u, origem, coletado_em, sync_status, sync_tentativas)
     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'pending',0)`,
    [
      p.id, p.projeto_id, p.nome,
      p.lat, p.lon, p.norte, p.este, p.cota,
      p.codigo, p.status_gnss, p.satelites, p.pdop,
      p.sigma_e, p.sigma_n, p.sigma_u,
      p.origem, p.coletado_em,
    ]
  )
  return p.id
}

export async function listarPendentes(projeto_id?: string): Promise<PontoLocal[]> {
  const db = getDb()
  if (projeto_id) {
    return await db.getAllAsync<PontoLocal>(
      `SELECT * FROM pontos_locais WHERE sync_status != 'synced' AND projeto_id = ? ORDER BY coletado_em`,
      [projeto_id]
    )
  }
  return await db.getAllAsync<PontoLocal>(
    `SELECT * FROM pontos_locais WHERE sync_status != 'synced' ORDER BY coletado_em`
  )
}

export async function listarPorProjeto(projeto_id: string): Promise<PontoLocal[]> {
  const db = getDb()
  return await db.getAllAsync<PontoLocal>(
    `SELECT * FROM pontos_locais WHERE projeto_id = ? ORDER BY coletado_em DESC`,
    [projeto_id]
  )
}

export async function marcarSincronizado(id: string): Promise<void> {
  const db = getDb()
  await db.runAsync(
    `UPDATE pontos_locais SET sync_status = 'synced', sync_em = ? WHERE id = ?`,
    [new Date().toISOString(), id]
  )
}

export async function marcarErro(id: string): Promise<void> {
  const db = getDb()
  await db.runAsync(
    `UPDATE pontos_locais SET sync_status = 'error', sync_tentativas = sync_tentativas + 1, sync_em = NULL WHERE id = ?`,
    [id]
  )
}

/**
 * Atualiza o status de múltiplos pontos em uma única transação SQLite.
 * Mais eficiente do que chamar marcarSincronizado/marcarErro individualmente em loop.
 */
export async function marcarResultadosBatch(
  sincronizados: string[],
  erros: string[]
): Promise<void> {
  if (sincronizados.length === 0 && erros.length === 0) return
  const db = getDb()
  const agora = new Date().toISOString()
  await db.withTransactionAsync(async () => {
    for (const id of sincronizados) {
      await db.runAsync(
        `UPDATE pontos_locais SET sync_status = 'synced', sync_em = ? WHERE id = ?`,
        [agora, id]
      )
    }
    for (const id of erros) {
      await db.runAsync(
        `UPDATE pontos_locais SET sync_status = 'error', sync_tentativas = sync_tentativas + 1, sync_em = NULL WHERE id = ?`,
        [id]
      )
    }
  })
}

export async function contarPendentes(projeto_id?: string): Promise<number> {
  const db = getDb()
  const row = projeto_id
    ? await db.getFirstAsync<{ count: number }>(
        `SELECT COUNT(*) as count FROM pontos_locais WHERE sync_status != 'synced' AND projeto_id = ?`,
        [projeto_id]
      )
    : await db.getFirstAsync<{ count: number }>(
        `SELECT COUNT(*) as count FROM pontos_locais WHERE sync_status != 'synced'`
      )
  return row?.count ?? 0
}

export async function ultimoNomePonto(projeto_id: string): Promise<string> {
  const db = getDb()
  const row = await db.getFirstAsync<{ nome: string }>(
    `SELECT nome FROM pontos_locais WHERE projeto_id = ? ORDER BY coletado_em DESC LIMIT 1`,
    [projeto_id]
  )
  if (!row) return 'PT0001'
  const match = row.nome.match(/(\d+)$/)
  if (!match) return 'PT0001'
  const n = parseInt(match[1], 10) + 1
  return row.nome.replace(/\d+$/, String(n).padStart(match[1].length, '0'))
}


// ── Preferências simples do app ─────────────────────────────────────────────

export async function initAppConfig(): Promise<void> {
  const db = getDb()
  await db.execAsync(`
    CREATE TABLE IF NOT EXISTS app_config (
      chave         TEXT PRIMARY KEY,
      valor         TEXT,
      atualizado_em TEXT NOT NULL
    );
  `)
}

export async function salvarUltimoProjetoMapa(projeto_id: string): Promise<void> {
  const db = getDb()
  await db.runAsync(
    `INSERT OR REPLACE INTO app_config (chave, valor, atualizado_em) VALUES ('ultimo_projeto_mapa', ?, ?)`,
    [projeto_id, new Date().toISOString()]
  )
}

export async function obterUltimoProjetoMapa(): Promise<string | null> {
  const db = getDb()
  const row = await db.getFirstAsync<{ valor: string }>(
    `SELECT valor FROM app_config WHERE chave = 'ultimo_projeto_mapa'`
  )
  return row?.valor ?? null
}
// ── Cache de projetos ─────────────────────────────────────────────────────────

export async function initProjetosCache(): Promise<void> {
  const db = getDb()
  await db.execAsync(`
    CREATE TABLE IF NOT EXISTS projetos_cache (
      id          TEXT PRIMARY KEY,
      dados       TEXT NOT NULL,   -- JSON completo do projeto
      cached_em   TEXT NOT NULL
    );
  `)
}

export async function cacheProjetos(projetos: any[]): Promise<void> {
  const db = getDb()
  const agora = new Date().toISOString()
  for (const p of projetos) {
    await db.runAsync(
      `INSERT OR REPLACE INTO projetos_cache (id, dados, cached_em) VALUES (?, ?, ?)`,
      [p.id, JSON.stringify(p), agora]
    )
  }
}

export async function getCachedProjetos(): Promise<any[]> {
  const db = getDb()
  const rows = await db.getAllAsync<{ dados: string }>(
    `SELECT dados FROM projetos_cache ORDER BY cached_em DESC`
  )
  try {
    return rows.map(r => JSON.parse(r.dados))
  } catch (erro) {
    console.warn('Erro ao parsear projetos do cache:', erro)
    return []
  }
}

export async function cacheProjetoDetalhe(id: string, projeto: any): Promise<void> {
  const db = getDb()
  await db.runAsync(
    `INSERT OR REPLACE INTO projetos_cache (id, dados, cached_em) VALUES (?, ?, ?)`,
    [id, JSON.stringify(projeto), new Date().toISOString()]
  )
}

export async function getCachedProjetoDetalhe(id: string): Promise<any | null> {
  const db = getDb()
  const row = await db.getFirstAsync<{ dados: string }>(
    `SELECT dados FROM projetos_cache WHERE id = ?`,
    [id]
  )
  if (!row) return null
  try {
    return JSON.parse(row.dados)
  } catch (erro) {
    console.warn(`Erro ao parsear projeto ${id} do cache:`, erro)
    return null
  }
}

export async function contarErros(projeto_id?: string): Promise<number> {
  const db = getDb()
  const result = projeto_id
    ? await db.getFirstAsync<{ count: number }>(
        `SELECT COUNT(*) as count FROM pontos_locais WHERE sync_status = 'error' AND projeto_id = ?`,
        [projeto_id]
      )
    : await db.getFirstAsync<{ count: number }>(
        `SELECT COUNT(*) as count FROM pontos_locais WHERE sync_status = 'error'`
      )
  return result?.count ?? 0
}

export async function resetarErros(projeto_id?: string): Promise<void> {
  const db = getDb()
  if (projeto_id) {
    await db.runAsync(
      `UPDATE pontos_locais SET sync_status = 'pending', sync_tentativas = 0 WHERE sync_status = 'error' AND projeto_id = ?`,
      [projeto_id]
    )
  } else {
    await db.runAsync(
      `UPDATE pontos_locais SET sync_status = 'pending', sync_tentativas = 0 WHERE sync_status = 'error'`
    )
  }
}

