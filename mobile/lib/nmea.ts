/**
 * mobile/lib/nmea.ts
 * Parser NMEA 0183 para receptor CHC i73+ via Bluetooth SPP.
 *
 * Suporta: $GPGGA, $GNGGA, $GPRMC, $GNRMC
 *
 * IMPORTANTE: O formato NMEA usa DDMM.MMMM (graus + minutos decimais),
 * diferente do parser_landstar.py Python que lê exportação CSV do LandStar.
 *
 * Qualidade fix (campo 6 do GGA):
 *   0 = Sem fix
 *   1 = GPS autônomo
 *   2 = DGPS
 *   4 = RTK Fixo ← ideal para INCRA (σ ≤ 0.05m)
 *   5 = RTK Float
 */

export interface NmeaFix {
  lat: number           // decimal degrees, negativo = Sul
  lon: number           // decimal degrees, negativo = Oeste
  alt: number           // altitude MSL em metros (aprox. ortométrica — GGA campo 9)
  altElipsoidal: number // altitude elipsoidal WGS84 = alt + sepGeoide (GGA campos 9+11)
  sepGeoide: number     // ondulação geoidal N do receptor (EGM96) — GGA campo 11
  qualidade: number     // 0..5
  satelites: number
  hdop: number
  valida: boolean       // do RMC: 'A'=válido, 'V'=void
  timestamp: number     // Date.now()
}

/** Converte DDMM.MMMM + hemisferio para graus decimais */
function dmsParaDecimal(dms: string, hemisferio: string): number {
  if (!dms || dms.length < 4) return 0
  // Extrai graus: os 2 primeiros dígitos para lat, 3 para lon
  const lenGraus = dms.indexOf('.') - 2  // minutos sempre têm 2 dígitos antes do ponto
  const graus   = parseFloat(dms.substring(0, lenGraus))
  const minutos = parseFloat(dms.substring(lenGraus))
  const decimal = graus + minutos / 60
  return (hemisferio === 'S' || hemisferio === 'W') ? -decimal : decimal
}

/** Verifica checksum NMEA: XOR de todos os bytes entre $ e * */
function checksumValido(sentenca: string): boolean {
  const inicio = sentenca.indexOf('$')
  const fim    = sentenca.lastIndexOf('*')
  if (inicio < 0 || fim < 0 || fim <= inicio) return true // sem checksum, aceita
  const dados = sentenca.substring(inicio + 1, fim)
  const cs    = sentenca.substring(fim + 1, fim + 3)
  let xor = 0
  for (let i = 0; i < dados.length; i++) xor ^= dados.charCodeAt(i)
  return xor.toString(16).toUpperCase().padStart(2, '0') === cs.toUpperCase()
}

/** Parseia $GPGGA ou $GNGGA */
export function parseGGA(linha: string): Partial<NmeaFix> | null {
  if (!linha.includes('GGA')) return null
  const partes = linha.split(',')
  if (partes.length < 10) return null

  const lat       = dmsParaDecimal(partes[2], partes[3])
  const lon       = dmsParaDecimal(partes[4], partes[5])
  const qualidade = parseInt(partes[6] ?? '0', 10)
  const satelites = parseInt(partes[7] ?? '0', 10)
  const hdop      = parseFloat(partes[8] ?? '99')
  const alt       = parseFloat(partes[9] ?? '0')   // altitude MSL (aprox. ortométrica)

  // Campo 11: ondulação do geoide N (altura do geoide EGM96 acima do elipsoide)
  // h_elipsoidal = h_msl + N  (CHC i73+ e maioria dos receptores RTK fornecem este campo)
  const sepGeoide    = parseFloat(partes[11] ?? '0') || 0
  const altElipsoidal = alt + sepGeoide

  if (isNaN(lat) || isNaN(lon)) return null

  return { lat, lon, alt, altElipsoidal, sepGeoide, qualidade, satelites, hdop }
}

/** Parseia $GPRMC ou $GNRMC */
export function parseRMC(linha: string): Partial<NmeaFix> | null {
  if (!linha.includes('RMC')) return null
  const partes = linha.split(',')
  if (partes.length < 7) return null

  const valida = partes[2] === 'A'
  const lat    = dmsParaDecimal(partes[3], partes[4])
  const lon    = dmsParaDecimal(partes[5], partes[6])

  if (isNaN(lat) || isNaN(lon)) return null

  return { lat, lon, valida }
}

/** Parseia qualquer linha NMEA e retorna dados parciais */
export function parseLinha(linha: string): Partial<NmeaFix> | null {
  const l = linha.trim()
  if (!l.startsWith('$')) return null
  if (!checksumValido(l)) return null

  if (l.includes('GGA')) return parseGGA(l)
  if (l.includes('RMC')) return parseRMC(l)
  return null
}

/** Combina GGA + RMC num NmeaFix completo */
export function mergeNmea(
  gga: Partial<NmeaFix>,
  rmc: Partial<NmeaFix>
): NmeaFix {
  const alt = gga.alt ?? 0
  const sep = gga.sepGeoide ?? 0
  return {
    lat:          gga.lat          ?? rmc.lat ?? 0,
    lon:          gga.lon          ?? rmc.lon ?? 0,
    alt,
    altElipsoidal: gga.altElipsoidal ?? (alt + sep),
    sepGeoide:    sep,
    qualidade:    gga.qualidade ?? 0,
    satelites:    gga.satelites ?? 0,
    hdop:         gga.hdop      ?? 99,
    valida:       rmc.valida    ?? (gga.qualidade !== undefined && gga.qualidade > 0),
    timestamp:    Date.now(),
  }
}

/** Label legível da qualidade do fix */
export function labelQualidade(q: number): string {
  const labels: Record<number, string> = {
    0: 'Sem Fix',
    1: 'GPS',
    2: 'DGPS',
    3: 'PPS',
    4: 'RTK Fixo',
    5: 'RTK Float',
  }
  return labels[q] ?? `Fix ${q}`
}

/** Cor da qualidade do fix */
export function corQualidade(q: number): string {
  if (q === 4) return '#27ae60'   // verde — RTK Fixo
  if (q === 5) return '#f39c12'   // laranja — RTK Float
  if (q === 2) return '#8e44ad'   // roxo — DGPS
  if (q === 1) return '#7f8c8d'   // cinza — GPS
  return '#e74c3c'                // vermelho — sem fix
}
