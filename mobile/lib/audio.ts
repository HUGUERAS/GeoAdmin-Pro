/**
 * mobile/lib/audio.ts
 * Feedback sonoro em campo usando os OGGs do LandStar
 * (D:\coletoraprolanddd\outras biblioteecas\voice\)
 *
 * Sons usados:
 *   point_stored.ogg        — ponto salvo com sucesso
 *   type_fixed.ogg          — fix mudou para RTK Fixo
 *   type_float.ogg          — fix mudou para RTK Float / qualidade caiu
 *   high_pdop.ogg           — PDOP alto (precisão ruim)
 *   low_precision.ogg       — precisão insuficiente para INCRA
 *   connection_success.ogg  — Bluetooth conectado
 *   connection_lost.ogg     — Bluetooth desconectado
 *   insufficient_satellites.ogg — satélites insuficientes
 *
 * Requer: expo-av  (instalado via package.json)
 * Fallback silencioso se expo-av não estiver disponível (web / Expo Go).
 */

let Audio: any = null
try {
  // Import dinâmico para não quebrar web/Expo Go
  Audio = require('expo-av').Audio
} catch {
  // expo-av não disponível neste ambiente — sons desabilitados
}

const _cache: Record<string, any> = {}

async function _carregar(nome: string): Promise<any | null> {
  if (!Audio) return null
  if (_cache[nome]) return _cache[nome]
  try {
    const { sound } = await Audio.Sound.createAsync(
      _mapArquivo(nome),
      { shouldPlay: false, volume: 1.0 }
    )
    _cache[nome] = sound
    return sound
  } catch {
    return null
  }
}

function _mapArquivo(nome: string): any {
  const mapa: Record<string, any> = {
    point_stored:           require('../assets/sounds/point_stored.ogg'),
    type_fixed:             require('../assets/sounds/type_fixed.ogg'),
    type_float:             require('../assets/sounds/type_float.ogg'),
    high_pdop:              require('../assets/sounds/high_pdop.ogg'),
    low_precision:          require('../assets/sounds/low_precision.ogg'),
    connection_success:     require('../assets/sounds/connection_success.ogg'),
    connection_lost:        require('../assets/sounds/connection_lost.ogg'),
    insufficient_satellites: require('../assets/sounds/insufficient_satellites.ogg'),
  }
  return mapa[nome]
}

async function tocar(nome: string): Promise<void> {
  try {
    const sound = await _carregar(nome)
    if (!sound) return
    await sound.replayAsync()
  } catch {
    // silencioso — som não é crítico para a operação
  }
}

// ── API pública ────────────────────────────────────────────────────────────────

/** Toca quando um ponto é salvo com sucesso */
export const somPontoSalvo        = () => tocar('point_stored')

/** Toca quando o fix muda para RTK Fixo */
export const somRtkFixo           = () => tocar('type_fixed')

/** Toca quando o fix cai para Float ou GPS */
export const somRtkFloat          = () => tocar('type_float')

/** Toca quando PDOP > 4 (precisão ruim) */
export const somPdopAlto          = () => tocar('high_pdop')

/** Toca quando precisão é insuficiente para INCRA (HDOP > 2 ou não-fixo) */
export const somPrecisaoBaixa     = () => tocar('low_precision')

/** Toca quando Bluetooth conecta ao receptor GNSS */
export const somConectado         = () => tocar('connection_success')

/** Toca quando Bluetooth perde conexão */
export const somDesconectado      = () => tocar('connection_lost')

/** Toca quando satélites são insuficientes (< 4) */
export const somSatelitesInsuf    = () => tocar('insufficient_satellites')

/** Descarrega todos os sons da memória (chamar no unmount da tela) */
export async function descarregarSons(): Promise<void> {
  for (const [key, sound] of Object.entries(_cache)) {
    try { await sound.unloadAsync() } catch { /* ignore */ }
    delete _cache[key]
  }
}
