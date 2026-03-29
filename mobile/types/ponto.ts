/**
 * mobile/types/ponto.ts
 * Tipos compartilhados para pontos locais de coleta GNSS.
 * Utilizado por db.ts (SQLite nativo) e db.web.ts (localStorage).
 */

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
