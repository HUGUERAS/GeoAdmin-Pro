import { useState, useEffect, useMemo, useRef } from 'react'
import {
  View, Text, StyleSheet, TouchableOpacity,
  ActivityIndicator, Alert, Dimensions,
} from 'react-native'
import MapView, { Marker, Polyline, UrlTile, PROVIDER_DEFAULT } from 'react-native-maps'
import Svg, { G, Line, Text as SvgText, Polyline as SvgPolyline } from 'react-native-svg'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { Feather } from '@expo/vector-icons'
import { Colors } from '../../../constants/Colors'
import { API_URL } from '../../../constants/Api'

const ESRI_IMAGERY =
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'

type Ponto = {
  id: string
  nome: string
  altitude_m: number
  lon: number
  lat: number
  codigo?: string
}
type Layers = { pontos: boolean; poligono: boolean; rotulos: boolean }
type Mode   = 'mapa' | 'cad'

// ── CAD transform helpers ────────────────────────────────────────────────────

function computeTransform(pontos: Ponto[], svgW: number, svgH: number, pad = 48) {
  const lons = pontos.map(p => p.lon)
  const lats = pontos.map(p => p.lat)
  const minLon = Math.min(...lons), maxLon = Math.max(...lons)
  const minLat = Math.min(...lats), maxLat = Math.max(...lats)
  const rangeX = maxLon - minLon || 0.0001
  const rangeY = maxLat - minLat || 0.0001
  const scale  = Math.min((svgW - 2 * pad) / rangeX, (svgH - 2 * pad) / rangeY)
  const drawW  = rangeX * scale
  const drawH  = rangeY * scale
  const offX   = (svgW - drawW) / 2
  const offY   = (svgH - drawH) / 2
  const toX    = (lon: number) => offX + (lon - minLon) * scale
  const toY    = (lat: number) => svgH - offY - (lat - minLat) * scale
  return { toX, toY, minLon, maxLon, minLat, maxLat, scale }
}

function niceInterval(range: number, ticks = 5) {
  const raw   = range / ticks
  const mag   = Math.pow(10, Math.floor(Math.log10(raw)))
  const frac  = raw / mag
  const nice  = frac < 1.5 ? 1 : frac < 3 ? 2 : frac < 7 ? 5 : 10
  return nice * mag
}

// ── Satellite view ───────────────────────────────────────────────────────────

function SatelliteView({ pontos, layers, region, C }: any) {
  const mapRef = useRef<MapView>(null)
  const polyCoords = [
    ...pontos.map((p: Ponto) => ({ latitude: p.lat, longitude: p.lon })),
    pontos.length > 1 ? { latitude: pontos[0].lat, longitude: pontos[0].lon } : null,
  ].filter(Boolean) as { latitude: number; longitude: number }[]

  useEffect(() => {
    if (region) mapRef.current?.animateToRegion(region, 800)
  }, [region])

  return (
    <MapView
      ref={mapRef}
      style={StyleSheet.absoluteFillObject}
      provider={PROVIDER_DEFAULT}
      mapType="none"
      initialRegion={region}
    >
      <UrlTile urlTemplate={ESRI_IMAGERY} maximumZ={19} flipY={false} tileSize={256} />

      {layers.poligono && polyCoords.length > 1 && (
        <Polyline coordinates={polyCoords} strokeColor={C.primary} strokeWidth={2.5} />
      )}

      {layers.pontos && pontos.map((p: Ponto) => (
        <Marker
          key={p.id}
          coordinate={{ latitude: p.lat, longitude: p.lon }}
          title={p.nome}
          description={p.altitude_m != null ? `Alt: ${p.altitude_m} m` : undefined}
          pinColor={C.primary}
        />
      ))}
    </MapView>
  )
}

// ── CAD view (SVG) ───────────────────────────────────────────────────────────

function CadView({ pontos, layers, C }: any) {
  const { width: W, height: H } = Dimensions.get('window')
  const svgH = H - 56 - 50 - 50  // header + toolbar + tabbar

  const { toX, toY, minLon, maxLon, minLat, maxLat } =
    useMemo(() => computeTransform(pontos, W, svgH), [pontos, W, svgH])

  // Grid lines
  const lonInterval = niceInterval(maxLon - minLon)
  const latInterval = niceInterval(maxLat - minLat)

  const lonGrid: number[] = []
  for (let v = Math.ceil(minLon / lonInterval) * lonInterval; v <= maxLon + lonInterval * 0.01; v += lonInterval)
    lonGrid.push(v)
  const latGrid: number[] = []
  for (let v = Math.ceil(minLat / latInterval) * latInterval; v <= maxLat + latInterval * 0.01; v += latInterval)
    latGrid.push(v)

  const polyPoints = pontos
    .map((p: Ponto) => `${toX(p.lon)},${toY(p.lat)}`)
    .join(' ')
  const closedPolyPoints = pontos.length > 1
    ? polyPoints + ` ${toX(pontos[0].lon)},${toY(pontos[0].lat)}`
    : polyPoints

  return (
    <Svg width={W} height={svgH}>
      {/* Background */}
      <G>
        {/* Grid lines (lon) */}
        {lonGrid.map(lon => (
          <Line key={`gx${lon}`}
            x1={toX(lon)} y1={0} x2={toX(lon)} y2={svgH}
            stroke="#333330" strokeWidth={0.5} />
        ))}
        {/* Grid labels (lon) */}
        {lonGrid.map(lon => (
          <SvgText key={`lx${lon}`}
            x={toX(lon)} y={svgH - 4}
            fontSize={8} fill="#666" textAnchor="middle">
            {lon.toFixed(5)}
          </SvgText>
        ))}
        {/* Grid lines (lat) */}
        {latGrid.map(lat => (
          <Line key={`gy${lat}`}
            x1={0} y1={toY(lat)} x2={W} y2={toY(lat)}
            stroke="#333330" strokeWidth={0.5} />
        ))}
        {/* Grid labels (lat) */}
        {latGrid.map(lat => (
          <SvgText key={`ly${lat}`}
            x={4} y={toY(lat) - 3}
            fontSize={8} fill="#666">
            {lat.toFixed(5)}
          </SvgText>
        ))}
      </G>

      {/* Polygon */}
      {layers.poligono && pontos.length > 1 && (
        <SvgPolyline
          points={closedPolyPoints}
          stroke={C.primary}
          strokeWidth={1.5}
          fill="rgba(239,159,39,0.08)"
        />
      )}

      {/* Points */}
      {layers.pontos && pontos.map((p: Ponto) => {
        const x = toX(p.lon)
        const y = toY(p.lat)
        return (
          <G key={p.id}>
            {/* Cross marker */}
            <Line x1={x - 5} y1={y} x2={x + 5} y2={y} stroke={C.primary} strokeWidth={2} />
            <Line x1={x} y1={y - 5} x2={x} y2={y + 5} stroke={C.primary} strokeWidth={2} />
            {/* Label */}
            {layers.rotulos && (
              <SvgText x={x + 7} y={y - 4} fontSize={9} fill={C.text} fontWeight="bold">
                {p.nome}
              </SvgText>
            )}
          </G>
        )
      })}
    </Svg>
  )
}

// ── Main screen ──────────────────────────────────────────────────────────────

export default function MapaProjetoScreen() {
  const C = Colors.dark
  const { id } = useLocalSearchParams<{ id: string }>()
  const router  = useRouter()

  const [projeto,     setProjeto]  = useState<any>(null)
  const [pontos,      setPontos]   = useState<Ponto[]>([])
  const [loading,     setLoading]  = useState(true)
  const [mode,        setMode]     = useState<Mode>('mapa')
  const [layers,      setLayers]   = useState<Layers>({ pontos: true, poligono: true, rotulos: true })
  const [showLayers,  setShowLayers] = useState(false)

  useEffect(() => {
    fetch(`${API_URL}/projetos/${id}`)
      .then(r => r.json())
      .then(data => {
        setProjeto(data)
        const pts = (data.pontos || []).filter((p: any) => p.lon != null && p.lat != null)
        setPontos(pts)
      })
      .catch(() => Alert.alert('Erro', 'Não foi possível carregar o projeto.'))
      .finally(() => setLoading(false))
  }, [id])

  const region = useMemo(() => {
    if (!pontos.length) return undefined
    const lons = pontos.map(p => p.lon)
    const lats = pontos.map(p => p.lat)
    const minLon = Math.min(...lons), maxLon = Math.max(...lons)
    const minLat = Math.min(...lats), maxLat = Math.max(...lats)
    return {
      latitude:      (minLat + maxLat) / 2,
      longitude:     (minLon + maxLon) / 2,
      latitudeDelta: Math.max((maxLat - minLat) * 1.4, 0.002),
      longitudeDelta: Math.max((maxLon - minLon) * 1.4, 0.002),
    }
  }, [pontos])

  const toggleLayer = (key: keyof Layers) =>
    setLayers(prev => ({ ...prev, [key]: !prev[key] }))

  if (loading) return (
    <View style={[s.fill, s.centro, { backgroundColor: C.background }]}>
      <ActivityIndicator color={C.primary} size="large" />
    </View>
  )

  return (
    <View style={[s.fill, { backgroundColor: C.background }]}>
      {/* Header */}
      <View style={[s.header, { backgroundColor: C.card, borderBottomColor: C.cardBorder }]}>
        <TouchableOpacity onPress={() => router.back()} style={s.backBtn}>
          <Feather name="arrow-left" size={22} color={C.text} />
        </TouchableOpacity>
        <View style={{ flex: 1 }}>
          <Text style={[s.titulo, { color: C.text }]} numberOfLines={1}>
            {projeto?.projeto_nome || '...'}
          </Text>
          <Text style={[s.sub, { color: C.muted }]}>{pontos.length} pontos</Text>
        </View>
      </View>

      {/* Toolbar */}
      <View style={[s.toolbar, { backgroundColor: C.card, borderBottomColor: C.cardBorder }]}>
        <View style={s.modeGroup}>
          {(['mapa', 'cad'] as Mode[]).map(m => (
            <TouchableOpacity
              key={m}
              style={[s.modeBtn, mode === m && { backgroundColor: C.primary }]}
              onPress={() => setMode(m)}
            >
              <Text style={{ color: mode === m ? C.primaryText : C.muted, fontWeight: '600', fontSize: 13 }}>
                {m === 'mapa' ? '🗺 Satélite' : '📐 CAD'}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
        <TouchableOpacity
          style={[s.layerBtn, showLayers && { backgroundColor: C.card }]}
          onPress={() => setShowLayers(v => !v)}
        >
          <Feather name="layers" size={18} color={showLayers ? C.primary : C.muted} />
        </TouchableOpacity>
      </View>

      {/* Map area */}
      <View style={s.fill}>
        {pontos.length === 0 ? (
          <View style={[s.fill, s.centro]}>
            <Feather name="map-pin" size={40} color={C.muted} />
            <Text style={[s.emptyMsg, { color: C.muted }]}>Nenhum ponto com coordenadas</Text>
          </View>
        ) : mode === 'mapa' ? (
          <SatelliteView pontos={pontos} layers={layers} region={region} C={C} />
        ) : (
          <CadView pontos={pontos} layers={layers} C={C} />
        )}
      </View>

      {/* Layer panel */}
      {showLayers && (
        <View style={[s.layerPanel, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
          {([
            ['pontos',   '🔵 Pontos'],
            ['poligono', '🟧 Polígono'],
            ['rotulos',  '🏷 Rótulos'],
          ] as [keyof Layers, string][]).map(([key, label]) => (
            <TouchableOpacity key={key} style={s.layerRow} onPress={() => toggleLayer(key)}>
              <View style={[s.check, layers[key] && { backgroundColor: C.primary, borderColor: C.primary }]}>
                {layers[key] && <Feather name="check" size={10} color={C.primaryText} />}
              </View>
              <Text style={{ color: C.text, fontSize: 14 }}>{label}</Text>
            </TouchableOpacity>
          ))}
        </View>
      )}
    </View>
  )
}

const s = StyleSheet.create({
  fill:       { flex: 1 },
  centro:     { alignItems: 'center', justifyContent: 'center' },
  header:     { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingTop: 56, paddingBottom: 12, borderBottomWidth: 0.5 },
  backBtn:    { marginRight: 12 },
  titulo:     { fontSize: 18, fontWeight: '700' },
  sub:        { fontSize: 12, marginTop: 1 },
  toolbar:    { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 12, paddingVertical: 8, borderBottomWidth: 0.5, gap: 8 },
  modeGroup:  { flex: 1, flexDirection: 'row', gap: 6 },
  modeBtn:    { paddingHorizontal: 14, paddingVertical: 6, borderRadius: 8 },
  layerBtn:   { padding: 8, borderRadius: 8 },
  emptyMsg:   { marginTop: 12, fontSize: 15 },
  layerPanel: { position: 'absolute', right: 12, top: 56 + 50 + 12, borderWidth: 0.5, borderRadius: 10, padding: 12, gap: 10 },
  layerRow:   { flexDirection: 'row', alignItems: 'center', gap: 10 },
  check:      { width: 18, height: 18, borderRadius: 4, borderWidth: 1.5, borderColor: '#555', alignItems: 'center', justifyContent: 'center' },
})
