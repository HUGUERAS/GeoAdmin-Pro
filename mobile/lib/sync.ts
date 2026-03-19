/**
 * mobile/lib/sync.ts
 * Motor de sincronização de pontos offline → Supabase via backend.
 * Idempotente: usa local_id como chave de dedup no servidor.
 */

import { listarPendentes, marcarSincronizado, marcarErro } from './db'
import { apiPost } from './api'

export interface SyncResult {
  sincronizados: number
  duplicados: number
  erros: number
  total: number
}

export async function sincronizar(projeto_id?: string): Promise<SyncResult> {
  const pendentes = await listarPendentes(projeto_id)

  if (pendentes.length === 0) {
    return { sincronizados: 0, duplicados: 0, erros: 0, total: 0 }
  }

  try {
    const payload = {
      pontos: pendentes.map(p => ({
        projeto_id:  p.projeto_id,
        nome:        p.nome,
        lat:         p.lat,
        lon:         p.lon,
        norte:       p.norte,
        este:        p.este,
        cota:        p.cota,
        codigo:      p.codigo,
        status_gnss: p.status_gnss,
        satelites:   p.satelites,
        pdop:        p.pdop,
        sigma_e:     p.sigma_e,
        sigma_n:     p.sigma_n,
        sigma_u:     p.sigma_u,
        origem:      p.origem,
        local_id:    p.id,
        coletado_em: p.coletado_em,
      })),
    }

    const result = await apiPost<{ sincronizados: number; duplicados: number; erros: any[] }>(
      '/pontos/sync',
      payload
    )

    // Marca todos como synced (servidor fez dedup via local_id)
    for (const p of pendentes) {
      await marcarSincronizado(p.id)
    }

    return {
      sincronizados: result.sincronizados,
      duplicados:    result.duplicados,
      erros:         result.erros?.length ?? 0,
      total:         pendentes.length,
    }
  } catch {
    // Sem conexão — incrementa tentativas mas mantém pending
    for (const p of pendentes) {
      await marcarErro(p.id)
    }
    return {
      sincronizados: 0,
      duplicados:    0,
      erros:         pendentes.length,
      total:         pendentes.length,
    }
  }
}
