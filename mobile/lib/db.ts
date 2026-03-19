/**
 * mobile/lib/db.ts
 * SQLite local para coleta offline de pontos GNSS.
 * expo-sqlite v14 já vem no Expo SDK 54 — sem npm install.
 */

import * as SQLite from 'expo-sqlite'

export type SyncStatus = 'pending' | 'synced' | 'error'

export interface PontoLocal {
  id: string            // UUID gerado no dispositivo
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
  coletado_em: string   // ISO string
  sync_status: SyncStatus
  sync_tentativas: number
  sync_em?: string      // ISO string quando synced
}

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
      `SELECT * FROM pontos_locais WHERE sync_status = 'pending' AND projeto_id = ? ORDER BY coletado_em`,
      [projeto_id]
    )
  }
  return await db.getAllAsync<PontoLocal>(
    `SELECT * FROM pontos_locais WHERE sync_status = 'pending' ORDER BY coletado_em`
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
    `UPDATE pontos_locais SET sync_status = 'error', sync_tentativas = sync_tentativas + 1 WHERE id = ?`,
    [id]
  )
}

export async function contarPendentes(projeto_id?: string): Promise<number> {
  const db = getDb()
  const row = projeto_id
    ? await db.getFirstAsync<{ count: number }>(
        `SELECT COUNT(*) as count FROM pontos_locais WHERE sync_status = 'pending' AND projeto_id = ?`,
        [projeto_id]
      )
    : await db.getFirstAsync<{ count: number }>(
        `SELECT COUNT(*) as count FROM pontos_locais WHERE sync_status = 'pending'`
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
