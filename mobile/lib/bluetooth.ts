/**
 * mobile/lib/bluetooth.ts
 * Gerenciador de conexão Bluetooth SPP com CHC i73+.
 * Usa react-native-bluetooth-classic (SPP clássico, NÃO BLE).
 *
 * ATENÇÃO: Módulo nativo — exige EAS build. Não funciona no Expo Go.
 */

import RNBluetoothClassic, {
  BluetoothDevice,
} from 'react-native-bluetooth-classic'
import { parseLinha, parseGGA, parseRMC, mergeNmea, NmeaFix } from './nmea'

const THROTTLE_MS   = 1000   // atualiza UI no máximo 1x/segundo
const BUFFER_MAX    = 4096   // descarta buffer se muito grande (stale data)

let _dispositivo: BluetoothDevice | null = null
let _leituraAtiva = false
let _ultimoFix: number = 0
let _buffer = ''
let _ultimoGGA: Partial<NmeaFix> = {}
let _ultimoRMC: Partial<NmeaFix> = {}
let _subscription: any = null

/** Lista dispositivos Bluetooth clássicos já pareados no Android */
export async function listarDispositivosPareados(): Promise<BluetoothDevice[]> {
  try {
    const pareados = await RNBluetoothClassic.getBondedDevices()
    return pareados
  } catch {
    return []
  }
}

/** Conecta ao dispositivo pelo endereço MAC */
export async function conectar(address: string): Promise<boolean> {
  try {
    if (_dispositivo) await desconectar()
    const dev = await RNBluetoothClassic.connectToDevice(address)
    _dispositivo = dev
    return true
  } catch {
    _dispositivo = null
    return false
  }
}

/** Desconecta do dispositivo atual */
export async function desconectar(): Promise<void> {
  try {
    pararLeitura()
    if (_dispositivo) {
      await _dispositivo.disconnect()
    }
  } catch {
    // ignora erros de desconexão
  } finally {
    _dispositivo = null
  }
}

/** Verifica se há conexão ativa */
export function isConectado(): boolean {
  return _dispositivo !== null
}

/**
 * Inicia leitura contínua de sentenças NMEA via SPP.
 * Chama onFix no máximo 1x/segundo com o último fix válido.
 * Guard contra race conditions: verifica flag e retorna imediatamente se já ativa.
 */
export function iniciarLeitura(onFix: (fix: NmeaFix) => void): void {
  // Guard robusto: verifica flag e retorna antes de qualquer inicialização
  if (_leituraAtiva) return
  if (!_dispositivo) return

  _leituraAtiva = true
  _buffer = ''
  _ultimoGGA = {}
  _ultimoRMC = {}

  _subscription = _dispositivo.onDataReceived((event: { data: string }) => {
    _buffer += event.data

    // Descarta buffer se muito grande (evita memória)
    if (_buffer.length > BUFFER_MAX) {
      const ultimo = _buffer.lastIndexOf('$')
      _buffer = ultimo > 0 ? _buffer.substring(ultimo) : ''
    }

    // Processa linhas completas
    const linhas = _buffer.split('\n')
    _buffer = linhas.pop() ?? ''  // mantém linha incompleta no buffer

    for (const linha of linhas) {
      const dados = parseLinha(linha)
      if (!dados) continue

      if (linha.includes('GGA')) _ultimoGGA = { ..._ultimoGGA, ...dados }
      if (linha.includes('RMC')) _ultimoRMC = { ..._ultimoRMC, ...dados }
    }

    // Throttle: emite fix no máximo 1x/segundo
    const agora = Date.now()
    if (agora - _ultimoFix >= THROTTLE_MS && _ultimoGGA.lat !== undefined) {
      _ultimoFix = agora
      const fix = mergeNmea(_ultimoGGA, _ultimoRMC)
      onFix(fix)
    }
  })
}

/** Para a leitura e remove o listener */
export function pararLeitura(): void {
  _leituraAtiva = false
  if (_subscription) {
    _subscription.remove?.()
    _subscription = null
  }
}
