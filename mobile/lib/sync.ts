/**
 * mobile/lib/sync.ts
 * Motor de sincronização de pontos offline → Supabase via backend.
 * Idempotente: usa local_id como chave de dedup no servidor.
 */

import { listarPendentes, marcarResultadosBatch } from './db'
import { apiPost } from './api'

export interface SyncResult {
  sincronizados: number
  duplicados: number
  erros: number
  total: number
  semConexao?: boolean
}

interface SyncApiResult {
  sincronizados: number
  duplicados: number
  erros: Array<{ local_id?: string; nome?: string; erro?: string }>
  itens?: Array<{ local_id?: string; status: string }>
  sincronizados_local_ids?: string[]
  duplicados_local_ids?: string[]
  erro_local_ids?: string[]
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

    const result = await apiPost<SyncApiResult>(
      '/pontos/sync',
      payload
    )

    const sincronizadosIds = new Set<string>([
      ...(result.sincronizados_local_ids ?? []),
      ...(result.duplicados_local_ids ?? []),
    ])
    const erroIds = new Set<string>([
      ...(result.erro_local_ids ?? []),
      ...((result.erros ?? []).map((item) => item.local_id).filter(Boolean) as string[]),
    ])
    const possuiResultadoPorItem = (
      Array.isArray(result.itens)
      || Array.isArray(result.sincronizados_local_ids)
      || Array.isArray(result.duplicados_local_ids)
      || Array.isArray(result.erro_local_ids)
    )

    let idsParaSincronizar: string[] = []
    let idsParaErro: string[] = []

    if (possuiResultadoPorItem) {
      for (const p of pendentes) {
        if (sincronizadosIds.has(p.id)) {
          idsParaSincronizar.push(p.id)
        } else {
          idsParaErro.push(p.id)
        }
      }
    } else if ((result.erros?.length ?? 0) === 0 && (result.sincronizados + result.duplicados) === pendentes.length) {
      idsParaSincronizar = pendentes.map(p => p.id)
    } else {
      idsParaErro = pendentes.map(p => p.id)
    }

    try {
      await marcarResultadosBatch(idsParaSincronizar, idsParaErro)
    } catch (erro) {
      console.warn('Erro ao persistir resultados da sincronização:', erro)
    }

    return {
      sincronizados: result.sincronizados,
      duplicados:    result.duplicados,
      erros:         (result.erro_local_ids?.length ?? result.erros?.length ?? 0),
      total:         pendentes.length,
    }
  } catch (err) {
    // Sem conexão — mantém como pending para retentar depois
    return {
      sincronizados: 0,
      duplicados:    0,
      erros:         0,
      total:         pendentes.length,
      semConexao:    true,
    }
  }
}
