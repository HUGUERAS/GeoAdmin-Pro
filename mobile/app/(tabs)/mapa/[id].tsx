import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import {
  View, Text, StyleSheet, TouchableOpacity, Modal, ScrollView, TextInput,
  ActivityIndicator, Alert, Dimensions, PanResponder, GestureResponderEvent, Platform,
} from 'react-native'
import WebViewCompat from '../../../components/WebViewCompat'
import Svg, { G, Line, Text as SvgText, Polyline as SvgPolyline, Circle } from 'react-native-svg'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { Feather } from '@expo/vector-icons'
import { Colors } from '../../../constants/Colors'
import { API_URL } from '../../../constants/Api'

type Ponto    = { id: string; nome: string; altitude_m: number; lon: number; lat: number }
type Vertice  = { lon: number; lat: number; nome: string }
type Layers   = { pontos: boolean; poligono: boolean; rotulos: boolean }
type Mode     = 'mapa' | 'cad'
type EditTool = 'mover' | 'adicionar' | 'deletar'

type NomeFerramenta = 'area' | 'inverso' | 'irradiacao' | 'intersecao' | 'distpl' | 'deflexao' | 'mediaPts' | 'conversao' | 'rotacao' | 'subdivisao'

// ── helpers ───────────────────────────────────────────────────────────────────

function computeTransform(pontos: { lon: number; lat: number }[], svgW: number, svgH: number, pad = 48) {
  const lons = pontos.map(p => p.lon), lats = pontos.map(p => p.lat)
  const minLon = Math.min(...lons), maxLon = Math.max(...lons)
  const minLat = Math.min(...lats), maxLat = Math.max(...lats)
  const rangeX = maxLon - minLon || 0.0001, rangeY = maxLat - minLat || 0.0001
  const scale  = Math.min((svgW - 2 * pad) / rangeX, (svgH - 2 * pad) / rangeY)
  const drawW = rangeX * scale, drawH = rangeY * scale
  const offX = (svgW - drawW) / 2, offY = (svgH - drawH) / 2
  const toX = (lon: number) => offX + (lon - minLon) * scale
  const toY = (lat: number) => svgH - offY - (lat - minLat) * scale
  const fromX = (x: number) => minLon + (x - offX) / scale
  const fromY = (y: number) => minLat + (svgH - offY - y) / scale
  return { toX, toY, fromX, fromY, minLon, maxLon, minLat, maxLat, scale }
}

function niceInterval(range: number, ticks = 5) {
  const raw = range / ticks, mag = Math.pow(10, Math.floor(Math.log10(raw)))
  const f = raw / mag
  return (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * mag
}

function haversine(lat1: number, lon1: number, lat2: number, lon2: number) {
  const R = 6378137, r = Math.PI / 180
  const dLat = (lat2 - lat1) * r, dLon = (lon2 - lon1) * r
  const a = Math.sin(dLat/2)**2 + Math.cos(lat1*r)*Math.cos(lat2*r)*Math.sin(dLon/2)**2
  return R * 2 * Math.asin(Math.sqrt(a))
}

function azimute(lat1: number, lon1: number, lat2: number, lon2: number) {
  const r = Math.PI / 180, dLon = (lon2 - lon1) * r
  const φ1 = lat1*r, φ2 = lat2*r
  const y = Math.sin(dLon)*Math.cos(φ2)
  const x = Math.cos(φ1)*Math.sin(φ2) - Math.sin(φ1)*Math.cos(φ2)*Math.cos(dLon)
  let az = Math.atan2(y, x)*180/Math.PI
  if (az < 0) az += 360
  const g = Math.floor(az), mf = (az-g)*60, m = Math.floor(mf)
  const s = Math.round((mf-m)*60)
  return `${g}°${String(m).padStart(2,'0')}'${String(s).padStart(2,'0')}"`
}

function calcArea(verts: Vertice[]): number {
  if (verts.length < 3) return 0
  const lat0 = verts[0].lat, lon0 = verts[0].lon
  const kLat = 111320, kLon = 111320 * Math.cos(lat0 * Math.PI / 180)
  let area = 0
  for (let i = 0; i < verts.length; i++) {
    const j = (i + 1) % verts.length
    const xi = (verts[i].lon - lon0) * kLon
    const yi = (verts[i].lat - lat0) * kLat
    const xj = (verts[j].lon - lon0) * kLon
    const yj = (verts[j].lat - lat0) * kLat
    area += xi * yj - xj * yi
  }
  return Math.abs(area) / 2
}

function calcPerimetro(verts: Vertice[]): number {
  let p = 0
  for (let i = 0; i < verts.length; i++) {
    const j = (i + 1) % verts.length
    p += haversine(verts[i].lat, verts[i].lon, verts[j].lat, verts[j].lon)
  }
  return p
}

function pontosParaVertices(pontos: Ponto[]): Vertice[] {
  return pontos.map((p) => ({ lon: p.lon, lat: p.lat, nome: p.nome }))
}

function coordKey(lon: number, lat: number) {
  return `${lon.toFixed(8)}:${lat.toFixed(8)}`
}

function pontosVisiveis(pontos: Ponto[], polygonVerts: Vertice[]): Ponto[] {
  const visiveis: Ponto[] = []
  const usados = new Set<string>()

  pontos.forEach((p) => {
    const key = coordKey(p.lon, p.lat)
    if (usados.has(key)) return
    usados.add(key)
    visiveis.push(p)
  })

  polygonVerts.forEach((v, idx) => {
    const key = coordKey(v.lon, v.lat)
    if (usados.has(key)) return
    usados.add(key)
    visiveis.push({
      id: `vertice-${idx}-${key}`,
      nome: v.nome?.trim() || `V${idx + 1}`,
      altitude_m: 0,
      lon: v.lon,
      lat: v.lat,
    })
  })

  return visiveis
}

function dmsParaDecimal(dms: string): number {
  const match = dms.match(/(\d+)°(\d+)'([\d.]+)"/)
  if (!match) return parseFloat(dms)
  return +match[1] + +match[2]/60 + +match[3]/3600
}

function decimalParaDms(dec: number): string {
  const g = Math.floor(dec)
  const mf = (dec - g) * 60
  const m = Math.floor(mf)
  const s = (mf - m) * 60
  return `${g}°${String(m).padStart(2,'0')}'${s.toFixed(1).padStart(4,'0')}"`
}

function intersecaoLocal(p1: Vertice, az1: number, p2: Vertice, az2: number): { lat: number; lon: number } | null {
  const cosLat = Math.cos(((p1.lat + p2.lat) / 2) * Math.PI / 180)
  const r1 = az1 * Math.PI / 180
  const r2 = az2 * Math.PI / 180
  const dx1 = Math.sin(r1), dy1 = Math.cos(r1)
  const dx2 = Math.sin(r2), dy2 = Math.cos(r2)
  const de = (p2.lon - p1.lon) * cosLat
  const dn = p2.lat - p1.lat
  const det = dx1 * (-dy2) + dx2 * dy1
  if (Math.abs(det) < 1e-10) return null
  const t1 = (de * (-dy2) + dx2 * dn) / det
  return {
    lat: p1.lat + t1 * dy1,
    lon: p1.lon + t1 * dx1 / cosLat,
  }
}

function distPontoLinhaLocal(p: Vertice, a: Vertice, b: Vertice): { dist: number; dentroSegmento: boolean } {
  const cosLat = Math.cos(((p.lat + a.lat + b.lat) / 3) * Math.PI / 180) * 111320
  const kLat = 111320
  const px = p.lon * cosLat, py = p.lat * kLat
  const ax = a.lon * cosLat, ay = a.lat * kLat
  const bx = b.lon * cosLat, by = b.lat * kLat
  const dx = bx - ax, dy = by - ay
  const len2 = dx*dx + dy*dy
  if (len2 < 1e-12) return { dist: Math.hypot(px-ax, py-ay), dentroSegmento: true }
  const t = ((px-ax)*dx + (py-ay)*dy) / len2
  const fx = ax + t*dx, fy = ay + t*dy
  return {
    dist: Math.sqrt((px-fx)**2 + (py-fy)**2),
    dentroSegmento: t >= 0 && t <= 1,
  }
}

function latLonParaUTM(lat: number, lon: number): { norte: number; este: number; fuso: number } {
  const fuso = Math.floor((lon + 180) / 6) + 1
  const a = 6378137.0, f = 1/298.257223563
  const b = a * (1 - f)
  const e2 = (a*a - b*b) / (a*a)
  const latR = lat * Math.PI / 180
  const lonR = lon * Math.PI / 180
  const lon0 = ((fuso - 1) * 6 - 180 + 3) * Math.PI / 180
  const N = a / Math.sqrt(1 - e2 * Math.sin(latR)**2)
  const T = Math.tan(latR)**2
  const C = e2 / (1 - e2) * Math.cos(latR)**2
  const A = Math.cos(latR) * (lonR - lon0)
  const M = a * ((1 - e2/4 - 3*e2*e2/64) * latR
    - (3*e2/8 + 3*e2*e2/32) * Math.sin(2*latR)
    + (15*e2*e2/256) * Math.sin(4*latR))
  const este = 0.9996 * N * (A + (1-T+C)*A**3/6) + 500000
  const norte = 0.9996 * (M + N*Math.tan(latR)*(A**2/2 + (5-T+9*C)*A**4/24)) + (lat < 0 ? 10000000 : 0)
  return { norte: Math.round(norte * 1000) / 1000, este: Math.round(este * 1000) / 1000, fuso }
}

function vxNecessarios(ferr: NomeFerramenta): number {
  switch (ferr) {
    case 'inverso':    return 2
    case 'irradiacao': return 1
    case 'intersecao': return 2
    case 'distpl':     return 3
    case 'deflexao':   return 2
    case 'mediaPts':   return -1 // variável
    case 'conversao':  return 1
    case 'area':       return 0
    case 'rotacao':    return 0
    case 'subdivisao': return 0
    default:           return 0
  }
}

const FERRAMENTAS: { id: NomeFerramenta; icone: string; label: string }[] = [
  { id: 'area',       icone: '⬟', label: 'Área' },
  { id: 'inverso',    icone: '↔', label: 'Inverso' },
  { id: 'irradiacao', icone: '📡', label: 'Irradiação' },
  { id: 'intersecao', icone: '✕', label: 'Interseção' },
  { id: 'distpl',     icone: '⊥', label: 'Dist. P-L' },
  { id: 'deflexao',   icone: '↗', label: 'Deflexão' },
  { id: 'mediaPts',   icone: '⊕', label: 'Média Pts' },
  { id: 'conversao',  icone: '🔄', label: 'Conversão' },
  { id: 'rotacao',    icone: '↻', label: 'Rotação' },
  { id: 'subdivisao', icone: '✂', label: 'Subdivisão' },
]

// ── Leaflet HTML ──────────────────────────────────────────────────────────────

const MAP_HTML = `<!DOCTYPE html>
<html><head>
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{background:#111;overflow:hidden}
  #map{width:100vw;height:100vh}
  .leaflet-control-attribution{display:none}
  .leaflet-control-zoom{margin:8px}
</style>
</head><body>
<div id="map"></div>
<script>
var map = L.map('map',{zoomControl:true});
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:19}).addTo(map);
var lg = L.layerGroup().addTo(map);
var pontos = [];
var poligono = [];

function render(layers) {
  lg.clearLayers();
  var bounds = [];
  if (layers.poligono && poligono.length > 1) {
    var poly = poligono.map(function(v){return [v.lat,v.lon];});
    L.polygon(poly,{color:'#EF9F27',weight:2.5,fillOpacity:0.07}).addTo(lg);
    bounds = bounds.concat(poly);
  }
  if (layers.pontos) {
    pontos.forEach(function(p) {
      L.circleMarker([p.lat,p.lon],{radius:5,color:'#fff',fillColor:'#EF9F27',fillOpacity:1,weight:1.5})
        .bindPopup(p.nome).addTo(lg);
      if (layers.rotulos) {
        L.marker([p.lat,p.lon],{
          icon:L.divIcon({
            className:'',
            html:'<span style="color:#fff;font-size:9px;font-weight:700;white-space:nowrap;text-shadow:0 0 3px #000,0 0 3px #000;padding-left:9px">'+p.nome+'</span>',
            iconAnchor:[0,9]
          }),interactive:false
        }).addTo(lg);
      }
      bounds.push([p.lat, p.lon]);
    });
  }
  if (bounds.length) {
    map.fitBounds(bounds,{padding:[40,40]});
  }
}

function updateMap(d) {
  pontos = d.pontos||[];
  poligono = d.poligono||[];
  render(d.layers||{pontos:true,poligono:true,rotulos:true});
}

document.addEventListener('message',function(e){try{var d=JSON.parse(e.data);updateMap(d);}catch(_){}});
window.addEventListener('message',function(e){try{var d=JSON.parse(e.data);updateMap(d);}catch(_){}});
</script>
</body></html>`

// ── WebView satellite view ────────────────────────────────────────────────────

function MapaWebView({ pontos, poligono, layers }: { pontos: Ponto[]; poligono: Vertice[]; layers: Layers }) {
  const webRef  = useRef<any>(null)
  const ready   = useRef(false)

  const inject = useCallback((pts: Ponto[], poly: Vertice[], lyr: Layers) => {
    if (!ready.current || !webRef.current) return
    const msg = JSON.stringify({ pontos: pts, poligono: poly, layers: lyr })
    if (Platform.OS === 'web') {
      webRef.current.postMessage(msg)
    } else {
      webRef.current.injectJavaScript(`updateMap(${msg});true;`)
    }
  }, [])

  useEffect(() => { inject(pontos, poligono, layers) }, [pontos, poligono, layers, inject])

  return (
    <WebViewCompat
      ref={webRef}
      style={StyleSheet.absoluteFillObject}
      source={{ html: MAP_HTML }}
      javaScriptEnabled
      originWhitelist={['*']}
      onLoad={() => { ready.current = true; inject(pontos, poligono, layers) }}
    />
  )
}

// ── CAD view ──────────────────────────────────────────────────────────────────

function CadView({ pontos, polygonVerts, layers, C, editMode, editTool, editVertices, origVertices,
  onVertexDrag, onVertexDelete, onMidpointAdd, onDragStart,
  onVertexTap, selecaoAtiva, vxSelecionados }: any) {
  const { width: W, height: H } = Dimensions.get('window')
  const svgH = H - 56 - 50 - 50
  const TOUCH_R = 20

  const allPts = useMemo(
    () => editMode ? [...(editVertices || []), ...(origVertices || [])] : [...(pontos || []), ...(polygonVerts || [])],
    [editMode, editVertices, origVertices, pontos, polygonVerts]
  )
  const xform = useMemo(
    () => computeTransform(allPts.length ? allPts : pontos, W, svgH),
    [allPts, W, svgH]
  )
  const { toX, toY, fromX, fromY, minLon, maxLon, minLat, maxLat } = xform

  const stateRef = useRef<any>({ editMode, editTool, editVertices, toX, toY, fromX, fromY, onVertexDrag, onDragStart, selecaoAtiva, onVertexTap })
  useEffect(() => {
    stateRef.current = { editMode, editTool, editVertices, toX, toY, fromX, fromY, onVertexDrag, onDragStart, selecaoAtiva, onVertexTap }
  })

  const panRef = useRef<{ idx: number } | null>(null)

  const panResponder = useRef(PanResponder.create({
    onStartShouldSetPanResponder: () =>
      stateRef.current.editMode && stateRef.current.editTool === 'mover' && !stateRef.current.selecaoAtiva,
    onMoveShouldSetPanResponder: () =>
      stateRef.current.editMode && stateRef.current.editTool === 'mover' && !stateRef.current.selecaoAtiva,
    onPanResponderGrant: (e: GestureResponderEvent) => {
      const { editMode: em, editTool: et, editVertices: ev, toX: tx, toY: ty } = stateRef.current
      if (!em || et !== 'mover' || !ev?.length) return
      const { locationX: px, locationY: py } = e.nativeEvent
      let closest = -1, minD = TOUCH_R
      ev.forEach((v: Vertice, i: number) => {
        const d = Math.hypot(tx(v.lon) - px, ty(v.lat) - py)
        if (d < minD) { minD = d; closest = i }
      })
      if (closest >= 0) {
        stateRef.current.onDragStart?.()
        panRef.current = { idx: closest }
      } else {
        panRef.current = null
      }
    },
    onPanResponderMove: (e: GestureResponderEvent) => {
      if (!panRef.current) return
      const { locationX: px, locationY: py } = e.nativeEvent
      const { fromX: fx, fromY: fy, onVertexDrag: drag } = stateRef.current
      drag(panRef.current.idx, fx(px), fy(py))
    },
    onPanResponderRelease: () => { panRef.current = null },
  })).current

  const lonInterval = niceInterval(maxLon - minLon)
  const latInterval = niceInterval(maxLat - minLat)
  const lonGrid: number[] = []
  for (let v = Math.ceil(minLon / lonInterval) * lonInterval; v <= maxLon + lonInterval * 0.01; v += lonInterval)
    lonGrid.push(v)
  const latGrid: number[] = []
  for (let v = Math.ceil(minLat / latInterval) * latInterval; v <= maxLat + latInterval * 0.01; v += latInterval)
    latGrid.push(v)

  const closedPts = (pts: { lon: number; lat: number }[]) =>
    pts.length > 1
      ? [...pts.map(p => `${toX(p.lon)},${toY(p.lat)}`), `${toX(pts[0].lon)},${toY(pts[0].lat)}`].join(' ')
      : ''

  return (
    <Svg width={W} height={svgH} {...panResponder.panHandlers}>
      <G>
        {lonGrid.map(lon => (
          <Line key={`gx${lon}`} x1={toX(lon)} y1={0} x2={toX(lon)} y2={svgH}
            stroke="#333330" strokeWidth={0.5} />
        ))}
        {lonGrid.map(lon => (
          <SvgText key={`lx${lon}`} x={toX(lon)} y={svgH - 4}
            fontSize={8} fill="#666" textAnchor="middle">{lon.toFixed(5)}</SvgText>
        ))}
        {latGrid.map(lat => (
          <Line key={`gy${lat}`} x1={0} y1={toY(lat)} x2={W} y2={toY(lat)}
            stroke="#333330" strokeWidth={0.5} />
        ))}
        {latGrid.map(lat => (
          <SvgText key={`ly${lat}`} x={4} y={toY(lat) - 3}
            fontSize={8} fill="#666">{lat.toFixed(5)}</SvgText>
        ))}
      </G>

      {!editMode && layers.poligono && polygonVerts?.length > 1 && (
        <SvgPolyline points={closedPts(polygonVerts)} stroke={C.primary} strokeWidth={1.5}
          fill="rgba(239,159,39,0.08)" />
      )}
      {!editMode && layers.pontos && pontos.map((p: Ponto) => {
        const x = toX(p.lon), y = toY(p.lat)
        return (
          <G key={p.id}>
            <Line x1={x-5} y1={y} x2={x+5} y2={y} stroke={C.primary} strokeWidth={2} />
            <Line x1={x} y1={y-5} x2={x} y2={y+5} stroke={C.primary} strokeWidth={2} />
            {layers.rotulos && (
              <SvgText x={x+7} y={y-4} fontSize={9} fill={C.text} fontWeight="bold">{p.nome}</SvgText>
            )}
          </G>
        )
      })}

      {editMode && origVertices?.length > 1 && (
        <SvgPolyline points={closedPts(origVertices)} stroke="#666460"
          strokeWidth={1} strokeDasharray="6,4" fill="none" />
      )}
      {editMode && editVertices?.length > 1 && (
        <SvgPolyline points={closedPts(editVertices)} stroke={C.primary}
          strokeWidth={2} fill="rgba(239,159,39,0.08)" />
      )}
      {editMode && editVertices?.map((_: any, i: number) => {
        const j = (i + 1) % editVertices.length
        const v = editVertices[i], vj = editVertices[j]
        const dist = haversine(v.lat, v.lon, vj.lat, vj.lon)
        const az = azimute(v.lat, v.lon, vj.lat, vj.lon)
        const mx = (toX(v.lon) + toX(vj.lon)) / 2
        const my = (toY(v.lat) + toY(vj.lat)) / 2
        return (
          <G key={`med${i}`}>
            <SvgText x={mx} y={my - 4} fontSize={8} fill="#e8e6de" textAnchor="middle">
              {dist.toFixed(1)}m
            </SvgText>
            <SvgText x={mx} y={my + 6} fontSize={7} fill="#7a7870" textAnchor="middle">
              {az}
            </SvgText>
          </G>
        )
      })}
      {editMode && editTool === 'adicionar' && !selecaoAtiva && editVertices?.map((_: any, i: number) => {
        const j = (i + 1) % editVertices.length
        const v = editVertices[i], vj = editVertices[j]
        const mx = (toX(v.lon) + toX(vj.lon)) / 2
        const my = (toY(v.lat) + toY(vj.lat)) / 2
        return (
          <Circle key={`mp${i}`} cx={mx} cy={my} r={6}
            fill="#1a1a18" stroke={C.primary} strokeWidth={2}
            onPress={() => onMidpointAdd(i)} />
        )
      })}
      {editMode && editVertices?.map((v: Vertice, i: number) => {
        const x = toX(v.lon), y = toY(v.lat)
        const selecionado = vxSelecionados?.includes(i)
        const color = selecionado
          ? '#378ADD'
          : editTool === 'deletar' && !selecaoAtiva
            ? '#E24B4A'
            : C.primary
        return (
          <G key={`ev${i}`}>
            <Circle cx={x} cy={y} r={8}
              fill={color} stroke="#fff" strokeWidth={1.5}
              onPress={() => {
                if (selecaoAtiva && onVertexTap) {
                  onVertexTap(i)
                } else if (editTool === 'deletar' && !selecaoAtiva) {
                  onVertexDelete(i)
                }
              }}
            />
            {selecionado && (
              <Circle cx={x} cy={y} r={13}
                fill="none" stroke="#378ADD" strokeWidth={2} />
            )}
          </G>
        )
      })}
    </Svg>
  )
}

// ── Main screen ───────────────────────────────────────────────────────────────

export default function MapaProjetoScreen() {
  const C = Colors.dark
  const insets = useSafeAreaInsets()
  const [topInset, setTopInset] = useState(0)
  useEffect(() => { setTopInset(insets.top) }, [insets.top])
  const headerPaddingTop = Math.max(topInset + 12, 20)
  const { id, tool } = useLocalSearchParams<{ id: string; tool?: NomeFerramenta }>()
  const router  = useRouter()

  const [projeto,     setProjeto]  = useState<any>(null)
  const [pontos,      setPontos]   = useState<Ponto[]>([])
  const [polygonVerts, setPolygonVerts] = useState<Vertice[]>([])
  const [loading,     setLoading]  = useState(true)
  const [mode,        setMode]     = useState<Mode>('mapa')
  const [layers,      setLayers]   = useState<Layers>({ pontos: true, poligono: true, rotulos: true })
  const [showLayers,  setShowLayers] = useState(false)

  const [editMode,    setEditMode] = useState(false)
  const [editTool,    setEditTool] = useState<EditTool>('mover')
  const [editVerts,   setEditVerts] = useState<Vertice[]>([])
  const [origVerts,   setOrigVerts] = useState<Vertice[]>([])
  const [editHistory, setEditHist] = useState<Vertice[][]>([])
  const undoStack = useRef<Vertice[][]>([])

  // ferramentas integradas
  const [ferrAtiva,          setFerrAtiva]          = useState<NomeFerramenta | null>(null)
  const [ferrPickerVisible,  setFerrPickerVisible]  = useState(false)
  const [ferrModalVisible,   setFerrModalVisible]   = useState(false)
  const [vxSelecionados,     setVxSelecionados]     = useState<number[]>([])

  // estados dos inputs de cada ferramenta
  const [irrAzimute,   setIrrAzimute]   = useState('')
  const [irrDist,      setIrrDist]      = useState('')
  const [irrNome,      setIrrNome]      = useState('')
  const [intAz1,       setIntAz1]       = useState('')
  const [intAz2,       setIntAz2]       = useState('')
  const [deflAngulo,   setDeflAngulo]   = useState('')
  const [deflLado,     setDeflLado]     = useState<'D' | 'E'>('D')
  const [rotAngulo,    setRotAngulo]    = useState('')
  const [rotOrigemAuto,setRotOrigemAuto] = useState(true)
  const [rotOrigemLat, setRotOrigemLat] = useState('')
  const [rotOrigemLon, setRotOrigemLon] = useState('')
  const [subArea,      setSubArea]      = useState('')
  const [subUnidade,   setSubUnidade]   = useState<'ha' | 'm2'>('ha')

  // resultados
  const [resultado,    setResultado]    = useState<any>(null)
  const autoToolKeyRef = useRef<string | null>(null)

  const visiblePoints = useMemo(
    () => pontosVisiveis(pontos, polygonVerts),
    [pontos, polygonVerts]
  )

  useEffect(() => {
    fetch(`${API_URL}/projetos/${id}`)
      .then(r => r.json())
      .then(data => {
        const pontosProjeto = (data.pontos || []).filter((p: any) => p.lon != null && p.lat != null)
        const perimetroAtivo = (data.perimetro_ativo?.vertices || []).filter((v: any) => v.lon != null && v.lat != null)

        setProjeto(data)
        setPontos(pontosProjeto)
        setPolygonVerts(perimetroAtivo.length > 0 ? perimetroAtivo : pontosParaVertices(pontosProjeto))
      })
      .catch(() => Alert.alert('Erro', 'Não foi possível carregar o projeto.'))
      .finally(() => setLoading(false))
  }, [id])

  const region = useMemo(() => {
    const boundsSource = polygonVerts.length ? polygonVerts : pontos
    if (!boundsSource.length) return undefined
    const lons = boundsSource.map(p => p.lon), lats = boundsSource.map(p => p.lat)
    const minLon = Math.min(...lons), maxLon = Math.max(...lons)
    const minLat = Math.min(...lats), maxLat = Math.max(...lats)
    return {
      latitude:      (minLat + maxLat) / 2,
      longitude:     (minLon + maxLon) / 2,
      latitudeDelta: Math.max((maxLat - minLat) * 1.4, 0.002),
      longitudeDelta: Math.max((maxLon - minLon) * 1.4, 0.002),
    }
  }, [pontos, polygonVerts])

  const toggleLayer = (key: keyof Layers) =>
    setLayers(prev => ({ ...prev, [key]: !prev[key] }))

  const entrarEdit = useCallback(async () => {
    if (!polygonVerts.length) { Alert.alert('Sem perímetro', 'Projeto sem geometria disponível para edição.'); return }
    setMode('cad')
    const verts = polygonVerts.map(v => ({ ...v }))
    setOrigVerts(verts.map(v => ({ ...v })))
    setEditVerts(verts.map(v => ({ ...v })))
    setEditHist([])
    undoStack.current = []
    setEditTool('mover')
    setEditMode(true)
    try {
      await fetch(`${API_URL}/perimetros/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          projeto_id: id,
          nome: (projeto?.projeto_nome || id) + ' — original',
          tipo: 'original',
          vertices: verts,
        }),
      })
    } catch (err: any) {
      Alert.alert('Aviso', 'Não foi possível registrar o perímetro original: ' + (err?.message || 'erro desconhecido'))
    }
  }, [polygonVerts, projeto, id])

  const pushHist = useCallback((verts: Vertice[]) => {
    setEditHist(prev => [...prev.slice(-49), verts.map(v => ({ ...v }))])
    undoStack.current = [...undoStack.current.slice(-14), verts.map(v => ({ ...v }))]
  }, [])

  const handleDragStart = useCallback(() => {
    setEditVerts(prev => {
      setEditHist(h => [...h.slice(-49), prev.map(v => ({ ...v }))])
      undoStack.current = [...undoStack.current.slice(-14), prev.map(v => ({ ...v }))]
      return prev
    })
  }, [])

  const handleVertexDrag = useCallback((i: number, lon: number, lat: number) => {
    setEditVerts(prev => {
      const next = [...prev]
      next[i] = { ...next[i], lon, lat }
      return next
    })
  }, [])

  const handleVertexDelete = useCallback((i: number) => {
    setEditVerts(prev => {
      if (prev.length <= 3) { Alert.alert('', 'Mínimo de 3 vértices.'); return prev }
      pushHist(prev)
      return prev.filter((_, j) => j !== i)
    })
  }, [pushHist])

  const handleMidpointAdd = useCallback((i: number) => {
    setEditVerts(prev => {
      const j = (i + 1) % prev.length
      const v = prev[i], vj = prev[j]
      pushHist(prev)
      const next = [...prev]
      next.splice(j, 0, { lon: (v.lon + vj.lon) / 2, lat: (v.lat + vj.lat) / 2, nome: '' })
      return next
    })
  }, [pushHist])

  const desfazer = useCallback(() => {
    if (!undoStack.current.length) return
    const last = undoStack.current[undoStack.current.length - 1]
    undoStack.current = undoStack.current.slice(0, -1)
    setEditVerts(last)
    setEditHist(prev => prev.slice(0, -1))
  }, [])

  const salvarEdit = useCallback(() => {
    const doSave = async () => {
      try {
        const res = await fetch(`${API_URL}/perimetros/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            projeto_id: id,
            nome: (projeto?.projeto_nome || id) + ' — editado',
            tipo: 'editado',
            vertices: editVerts,
          }),
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const salvo = await res.json().catch(() => null)
        const proximosVertices = (salvo?.vertices || editVerts).map((v: Vertice) => ({ ...v }))

        setPolygonVerts(proximosVertices)
        setProjeto((atual: any) => atual ? {
          ...atual,
          perimetro_ativo: salvo
            ? { ...salvo, vertices: proximosVertices }
            : atual.perimetro_ativo,
        } : atual)
        setOrigVerts(proximosVertices.map((v: Vertice) => ({ ...v })))
        setEditVerts(proximosVertices.map((v: Vertice) => ({ ...v })))
        setEditHist([])
        undoStack.current = []
        setEditMode(false)
        Alert.alert('Salvo!', `Perímetro salvo com sucesso — ${editVerts.length} vértices.`)
      } catch (err: any) {
        Alert.alert('Erro', 'Falha ao salvar o perímetro: ' + (err?.message || 'erro desconhecido'))
      }
    }
    Alert.alert(
      'Salvar perímetro',
      'Deseja salvar as alterações no perímetro deste projeto?',
      [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Salvar', onPress: () => doSave() },
      ]
    )
  }, [id, projeto, editVerts])

  const cancelarEdit = useCallback(() => {
    Alert.alert('Cancelar edição', 'Descartar alterações?', [
      { text: 'Não', style: 'cancel' },
      {
        text: 'Sim',
        onPress: () => {
          const atuais = polygonVerts.map(v => ({ ...v }))
          setOrigVerts(atuais.map(v => ({ ...v })))
          setEditVerts(atuais)
          setEditHist([])
          undoStack.current = []
          setEditMode(false)
        },
      },
    ])
  }, [polygonVerts])

  // ── ferramentas ──────────────────────────────────────────────────────────────

  const limparFerramenta = useCallback(() => {
    setFerrAtiva(null)
    setFerrPickerVisible(false)
    setFerrModalVisible(false)
    setVxSelecionados([])
    setResultado(null)
    setIrrAzimute(''); setIrrDist(''); setIrrNome('')
    setIntAz1(''); setIntAz2('')
    setDeflAngulo(''); setDeflLado('D')
    setRotAngulo(''); setRotOrigemAuto(true); setRotOrigemLat(''); setRotOrigemLon('')
    setSubArea(''); setSubUnidade('ha')
  }, [])

  const abrirFerramenta = useCallback((ferr: NomeFerramenta) => {
    setFerrPickerVisible(false)
    setFerrAtiva(ferr)
    setVxSelecionados([])
    setResultado(null)
    const nec = vxNecessarios(ferr)
    if (nec === 0) {
      // abre direto
      setFerrModalVisible(true)
    }
    // com seleção: aguarda vertex taps
  }, [])

  useEffect(() => {
    if (!tool || loading || !polygonVerts.length) return
    if (autoToolKeyRef.current === `${id}:${tool}`) return

    const ferramentasSuportadas = new Set<NomeFerramenta>([
      'area',
      'irradiacao',
      'intersecao',
      'distpl',
      'deflexao',
      'mediaPts',
      'conversao',
      'rotacao',
      'subdivisao',
    ])

    if (!ferramentasSuportadas.has(tool)) return
    autoToolKeyRef.current = `${id}:${tool}`

    const abrir = async () => {
      if (!editMode) {
        await entrarEdit()
      }
      setTimeout(() => abrirFerramenta(tool), 80)
    }

    void abrir()
  }, [tool, id, loading, polygonVerts.length, editMode, entrarEdit, abrirFerramenta])

  const handleVertexTap = useCallback((i: number) => {
    if (!ferrAtiva) return
    const nec = vxNecessarios(ferrAtiva)
    setVxSelecionados(prev => {
      // média pts: acumulativo, sem limite
      if (ferrAtiva === 'mediaPts') {
        if (prev.includes(i)) return prev.filter(x => x !== i)
        return [...prev, i]
      }
      // outros: substituição cíclica
      if (prev.includes(i)) return prev.filter(x => x !== i)
      const next = [...prev, i]
      if (nec > 0 && next.length >= nec) {
        // vai abrir o modal (useEffect cuida disso)
        return next.slice(0, nec)
      }
      return next
    })
  }, [ferrAtiva])

  useEffect(() => {
    if (!ferrAtiva) return
    const nec = vxNecessarios(ferrAtiva)
    if (nec > 0 && vxSelecionados.length >= nec) {
      setFerrModalVisible(true)
    }
  }, [vxSelecionados, ferrAtiva])

  const calcular = useCallback(() => {
    if (!ferrAtiva) return
    const selecionados = vxSelecionados.map(i => editVerts[i])

    if (ferrAtiva === 'area') {
      const areaM2 = calcArea(editVerts)
      const perim  = calcPerimetro(editVerts)
      setResultado({ areaM2, areaHa: areaM2 / 10000, perim })
      return
    }

    if (ferrAtiva === 'inverso') {
      const [p1, p2] = selecionados
      const dist = haversine(p1.lat, p1.lon, p2.lat, p2.lon)
      const az   = azimute(p1.lat, p1.lon, p2.lat, p2.lon)
      const azInv = azimute(p2.lat, p2.lon, p1.lat, p1.lon)
      setResultado({ dist, az, azInv })
      return
    }

    if (ferrAtiva === 'irradiacao') {
      const estacao = selecionados[0]
      const az = parseFloat(irrAzimute)
      const dist = parseFloat(irrDist)
      if (isNaN(az) || isNaN(dist)) { Alert.alert('Atenção', 'Preencha azimute e distância.'); return }
      const azRad = (az * Math.PI) / 180
      const dLat = (dist * Math.cos(azRad)) / 111320
      const dLon = (dist * Math.sin(azRad)) / (111320 * Math.cos(estacao.lat * Math.PI / 180))
      setResultado({ lat: estacao.lat + dLat, lon: estacao.lon + dLon })
      return
    }

    if (ferrAtiva === 'intersecao') {
      const [p1, p2] = selecionados
      const az1 = dmsParaDecimal(intAz1)
      const az2 = dmsParaDecimal(intAz2)
      if (isNaN(az1) || isNaN(az2)) { Alert.alert('Atenção', 'Preencha os azimutes.'); return }
      const pt = intersecaoLocal(p1, az1, p2, az2)
      if (!pt) { Alert.alert('', 'Semiretas paralelas, sem interseção.'); return }
      setResultado(pt)
      return
    }

    if (ferrAtiva === 'distpl') {
      const [p, a, b] = selecionados
      const res = distPontoLinhaLocal(p, a, b)
      setResultado(res)
      return
    }

    if (ferrAtiva === 'deflexao') {
      const [v1, v2] = selecionados
      const azEntradaDms = azimute(v1.lat, v1.lon, v2.lat, v2.lon)
      const azEntrada = dmsParaDecimal(azEntradaDms)
      const defl = parseFloat(deflAngulo)
      if (isNaN(defl)) { Alert.alert('Atenção', 'Preencha o ângulo de deflexão.'); return }
      const azSaida = ((azEntrada + (deflLado === 'D' ? defl : -defl)) % 360 + 360) % 360
      setResultado({ azEntradaDms, azSaidaDms: decimalParaDms(azSaida) })
      return
    }

    if (ferrAtiva === 'mediaPts') {
      if (vxSelecionados.length < 2) { Alert.alert('', 'Selecione ao menos 2 vértices.'); return }
      const n = selecionados.length
      const mLat = selecionados.reduce((s, v) => s + v.lat, 0) / n
      const mLon = selecionados.reduce((s, v) => s + v.lon, 0) / n
      const dpLat = n > 1 ? Math.sqrt(selecionados.reduce((s, v) => s + (v.lat - mLat)**2, 0) / (n-1)) * 111320 : 0
      const dpLon = n > 1 ? Math.sqrt(selecionados.reduce((s, v) => s + (v.lon - mLon)**2, 0) / (n-1)) * 111320 * Math.cos(mLat * Math.PI/180) : 0
      const dp = Math.sqrt(dpLat**2 + dpLon**2)
      setResultado({ lat: mLat, lon: mLon, dp, n })
      return
    }

    if (ferrAtiva === 'conversao') {
      const v = selecionados[0]
      const utm = latLonParaUTM(v.lat, v.lon)
      setResultado(utm)
      return
    }

    if (ferrAtiva === 'rotacao') {
      const ang = parseFloat(rotAngulo)
      if (isNaN(ang)) { Alert.alert('Atenção', 'Preencha o ângulo de rotação.'); return }
      const angRad = ang * Math.PI / 180
      let oLat: number, oLon: number
      if (rotOrigemAuto) {
        oLat = editVerts.reduce((s, v) => s + v.lat, 0) / editVerts.length
        oLon = editVerts.reduce((s, v) => s + v.lon, 0) / editVerts.length
      } else {
        oLat = parseFloat(rotOrigemLat)
        oLon = parseFloat(rotOrigemLon)
        if (isNaN(oLat) || isNaN(oLon)) { Alert.alert('Atenção', 'Preencha a origem.'); return }
      }
      const cosLat = Math.cos(oLat * Math.PI / 180)
      const rotacionados = editVerts.map(v => {
        const dLon = (v.lon - oLon) * cosLat
        const dLat = v.lat - oLat
        const rLon = dLon * Math.cos(angRad) - dLat * Math.sin(angRad)
        const rLat = dLon * Math.sin(angRad) + dLat * Math.cos(angRad)
        return { ...v, lon: oLon + rLon / cosLat, lat: oLat + rLat }
      })
      setResultado({ rotacionados, angulo: ang })
      return
    }

    if (ferrAtiva === 'subdivisao') {
      const areaAlvoStr = parseFloat(subArea)
      if (isNaN(areaAlvoStr) || areaAlvoStr <= 0) { Alert.alert('Atenção', 'Preencha a área alvo.'); return }
      const areaAlvoM2 = subUnidade === 'ha' ? areaAlvoStr * 10000 : areaAlvoStr
      const totalM2 = calcArea(editVerts)
      if (areaAlvoM2 >= totalM2) { Alert.alert('', 'Área alvo maior ou igual à área total.'); return }

      // bisseção: tenta cortar a aresta entre i e i+1 e calcular a área da sub-parte
      // estratégia: fixar aresta 0->1 como corte, e variar o ponto na aresta correta
      // simplificação: corta na primeira aresta em que a área acumulada excede o alvo
      const n = editVerts.length
      // acumular shoelace parcial
      let melhorAresta = 0, melhorT = 0.5
      let found = false
      for (let aresta = 1; aresta < n - 1 && !found; aresta++) {
        // sub-polígono: verts[0..aresta] + ponto interpolado na aresta aresta->aresta+1
        let lo = 0, hi = 1, bestT = 0
        for (let iter = 0; iter < 50; iter++) {
          const mid = (lo + hi) / 2
          const va = editVerts[aresta], vb = editVerts[(aresta + 1) % n]
          const pCorte: Vertice = {
            lat: va.lat + mid * (vb.lat - va.lat),
            lon: va.lon + mid * (vb.lon - va.lon),
            nome: 'P-corte',
          }
          const subVerts = [...editVerts.slice(0, aresta + 1), pCorte, editVerts[0]]
          const areaSubM2 = calcArea(subVerts)
          if (Math.abs(areaSubM2 - areaAlvoM2) < 0.1) { bestT = mid; found = true; break }
          if (areaSubM2 < areaAlvoM2) lo = mid
          else { hi = mid; bestT = mid }
        }
        if (found || lo > 0) {
          melhorAresta = aresta
          melhorT = (lo + hi) / 2
          const va = editVerts[aresta], vb = editVerts[(aresta + 1) % n]
          const pCorte: Vertice = {
            lat: va.lat + melhorT * (vb.lat - va.lat),
            lon: va.lon + melhorT * (vb.lon - va.lon),
            nome: 'P-corte',
          }
          const subVerts = [...editVerts.slice(0, aresta + 1), pCorte, editVerts[0]]
          const areaSub = calcArea(subVerts)
          if (Math.abs(areaSub - areaAlvoM2) < totalM2 * 0.01) {
            setResultado({ pCorte, areaSub, areaResto: totalM2 - areaSub, aresta: aresta, t: melhorT })
            return
          }
        }
      }
      // fallback: resultado com melhor aproximação
      const va = editVerts[melhorAresta], vb = editVerts[(melhorAresta + 1) % n]
      const pCorte: Vertice = {
        lat: va.lat + melhorT * (vb.lat - va.lat),
        lon: va.lon + melhorT * (vb.lon - va.lon),
        nome: 'P-corte',
      }
      const subVerts = [...editVerts.slice(0, melhorAresta + 1), pCorte, editVerts[0]]
      setResultado({ pCorte, areaSub: calcArea(subVerts), areaResto: totalM2 - calcArea(subVerts), aresta: melhorAresta, t: melhorT })
    }
  }, [ferrAtiva, vxSelecionados, editVerts, irrAzimute, irrDist, intAz1, intAz2, deflAngulo, deflLado, rotAngulo, rotOrigemAuto, rotOrigemLat, rotOrigemLon, subArea, subUnidade])

  const inserirNoPeriemtro = useCallback(() => {
    if (!resultado || !ferrAtiva) return

    if (ferrAtiva === 'irradiacao') {
      pushHist(editVerts)
      setEditVerts(prev => [...prev, { lat: resultado.lat, lon: resultado.lon, nome: irrNome || 'P-irrad' }])
      limparFerramenta()
      return
    }

    if (ferrAtiva === 'intersecao') {
      pushHist(editVerts)
      setEditVerts(prev => [...prev, { lat: resultado.lat, lon: resultado.lon, nome: 'P-intrs' }])
      limparFerramenta()
      return
    }

    if (ferrAtiva === 'mediaPts') {
      pushHist(editVerts)
      setEditVerts(prev => [...prev, { lat: resultado.lat, lon: resultado.lon, nome: 'P-media' }])
      limparFerramenta()
      return
    }

    if (ferrAtiva === 'subdivisao' && resultado.pCorte) {
      pushHist(editVerts)
      setEditVerts(prev => {
        const next = [...prev]
        next.splice(resultado.aresta + 1, 0, resultado.pCorte)
        return next
      })
      limparFerramenta()
      return
    }
  }, [ferrAtiva, resultado, editVerts, irrNome, pushHist, limparFerramenta])

  const aplicarRotacao = useCallback(() => {
    if (!resultado?.rotacionados) return
    pushHist(editVerts)
    setEditVerts(resultado.rotacionados)
    limparFerramenta()
  }, [resultado, editVerts, pushHist, limparFerramenta])

  const selecaoAtiva = ferrAtiva !== null && vxNecessarios(ferrAtiva) !== 0
  const hasGeometry = visiblePoints.length > 0 || polygonVerts.length > 0

  if (loading) return (
    <View style={[s.fill, s.centro, { backgroundColor: C.background }]}>
      <ActivityIndicator color={C.primary} size="large" />
    </View>
  )

  return (
    <View style={[s.fill, { backgroundColor: C.background }]}>
      {/* Header */}
      <View style={[s.header, { backgroundColor: C.card, borderBottomColor: C.cardBorder, paddingTop: headerPaddingTop }]}>
        <TouchableOpacity onPress={() => router.back()} style={s.backBtn}>
          <Feather name="arrow-left" size={22} color={C.text} />
        </TouchableOpacity>
        <View style={{ flex: 1 }}>
          <Text style={[s.titulo, { color: C.text }]} numberOfLines={1}>
            {projeto?.projeto_nome || '...'}
          </Text>
          <Text style={[s.sub, { color: C.muted }]}>
            {`${pontos.length} medidos • ${visiblePoints.length} visíveis • ${polygonVerts.length} vértices`}
          </Text>
        </View>
      </View>

      {/* Toolbar */}
      {!editMode ? (
        <View style={[s.toolbar, { backgroundColor: C.card, borderBottomColor: C.cardBorder }]}>
          <View style={s.modeGroup}>
            {(['mapa', 'cad'] as Mode[]).map(m => (
              <TouchableOpacity key={m} style={[s.modeBtn, mode === m && { backgroundColor: C.primary }]}
                onPress={() => setMode(m)}>
                <Text style={{ color: mode === m ? C.primaryText : C.muted, fontWeight: '600', fontSize: 13 }}>
                  {m === 'mapa' ? '🗺 Satélite' : '📐 CAD'}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
          <TouchableOpacity style={[s.editBtn, { borderColor: C.primary }]} onPress={entrarEdit}>
            <Text style={{ color: C.primary, fontSize: 12, fontWeight: '700' }}>✏️ Editar</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[s.layerBtn, showLayers && { backgroundColor: C.card }]}
            onPress={() => setShowLayers(v => !v)}>
            <Feather name="layers" size={18} color={showLayers ? C.primary : C.muted} />
          </TouchableOpacity>
        </View>
      ) : (
        <View style={[s.editToolbar, { backgroundColor: C.card, borderBottomColor: C.cardBorder }]}>
          <View style={[s.editTag, { borderColor: C.primary + '60', backgroundColor: C.primary + '20' }]}>
            <Text style={{ color: C.primary, fontSize: 9, fontWeight: '700', letterSpacing: 1 }}>EDITANDO</Text>
          </View>
          {([
            ['mover',     '↔'],
            ['adicionar', '+'],
            ['deletar',   '✕'],
          ] as [EditTool, string][]).map(([t, icon]) => (
            <TouchableOpacity key={t}
              style={[s.etool, editTool === t && { backgroundColor: C.primary }]}
              onPress={() => setEditTool(t)}>
              <Text style={{ color: editTool === t ? C.primaryText : C.muted, fontSize: 12, fontWeight: '700' }}>
                {icon}
              </Text>
            </TouchableOpacity>
          ))}
          <TouchableOpacity
            style={[s.etool, { opacity: undoStack.current.length === 0 ? 0.3 : 1 }]}
            onPress={desfazer}
            disabled={undoStack.current.length === 0}>
            <Feather name="corner-up-left" size={18} color={C.muted} />
          </TouchableOpacity>
          {/* Botão ferramentas ⚙ */}
          <TouchableOpacity style={[s.etool, { borderColor: C.primary }]}
            onPress={() => setFerrPickerVisible(true)}
            accessibilityRole="button" accessibilityLabel="Ferramentas de cálculo">
            <Text style={{ color: C.primary, fontSize: 13 }}>⚙</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[s.etool, { marginLeft: 'auto' }]} onPress={cancelarEdit}>
            <Text style={{ color: C.muted, fontSize: 11 }}>Cancelar</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[s.etool, { backgroundColor: '#1D9E75', borderColor: '#1D9E75' }]}
            onPress={salvarEdit}>
            <Text style={{ color: '#fff', fontSize: 11, fontWeight: '700' }}>💾</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Map area */}
      <View style={s.fill}>
        {!hasGeometry ? (
          <View style={[s.fill, s.centro]}>
            <Feather name="map-pin" size={40} color={C.muted} />
            <Text style={[s.emptyMsg, { color: C.muted }]}>Nenhuma geometria disponível</Text>
          </View>
        ) : mode === 'mapa' ? (
          <MapaWebView pontos={visiblePoints} poligono={polygonVerts} layers={layers} />
        ) : (
          <CadView
            pontos={visiblePoints} polygonVerts={polygonVerts} layers={layers} C={C}
            editMode={editMode} editTool={editTool}
            editVertices={editVerts} origVertices={origVerts}
            onVertexDrag={handleVertexDrag}
            onVertexDelete={handleVertexDelete}
            onMidpointAdd={handleMidpointAdd}
            onDragStart={handleDragStart}
            onVertexTap={handleVertexTap}
            selecaoAtiva={selecaoAtiva}
            vxSelecionados={vxSelecionados}
          />
        )}

        {/* Overlay de seleção de vértices */}
        {editMode && ferrAtiva && vxNecessarios(ferrAtiva) !== 0 && (
          <View style={s.selecaoOverlay}>
            <Text style={s.selecaoTxt}>
              {ferrAtiva === 'mediaPts'
                ? `Toque nos vértices • ${vxSelecionados.length} selecionados`
                : `Toque nos vértices • ${vxSelecionados.length}/${vxNecessarios(ferrAtiva)} selecionados`}
            </Text>
            {ferrAtiva === 'mediaPts' && vxSelecionados.length >= 2 && (
              <TouchableOpacity onPress={() => { setFerrModalVisible(true) }}
                style={{ marginTop: 6, backgroundColor: '#378ADD', borderRadius: 6, paddingHorizontal: 12, paddingVertical: 4 }}>
                <Text style={{ color: '#fff', fontSize: 12, fontWeight: '700' }}>✓ Calcular</Text>
              </TouchableOpacity>
            )}
            <TouchableOpacity onPress={limparFerramenta}
              style={{ marginTop: 4, padding: 4 }}>
              <Text style={{ color: '#378ADD', fontSize: 11 }}>Cancelar</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Coordinate overlay */}
        {hasGeometry && !editMode && region && (
          <View style={s.coordOverlay} pointerEvents="none">
            <Text style={s.coordText}>
              {`Lat  ${region.latitude.toFixed(5)}°   Lon  ${region.longitude.toFixed(5)}°`}
            </Text>
            <Text style={s.coordMuted}>
              {`Medidos: ${pontos.length} • Visíveis: ${visiblePoints.length} • Vértices: ${polygonVerts.length}`}
            </Text>
          </View>
        )}
      </View>

      {/* Layer panel */}
      {!editMode && showLayers && (
        <View style={[s.layerPanel, { backgroundColor: C.card, borderColor: C.cardBorder, top: headerPaddingTop + 50 + 12 }]}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <Text style={{ color: C.muted, fontSize: 11, fontWeight: '700', letterSpacing: 0.5 }}>CAMADAS</Text>
            <TouchableOpacity onPress={() => setShowLayers(false)} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
              <Feather name="x" size={16} color={C.muted} />
            </TouchableOpacity>
          </View>
          {([
            ['pontos',   '🔵 Pontos visíveis'],
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

      {/* ── Modal picker de ferramentas ── */}
      <Modal visible={ferrPickerVisible} transparent animationType="slide"
        onRequestClose={() => setFerrPickerVisible(false)}>
        <View style={s.ferrModal}>
          <View style={[s.ferrSheet, { backgroundColor: C.card }]}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <Text style={[s.ferrSheetTitle, { color: C.text }]}>Ferramentas de Cálculo</Text>
              <TouchableOpacity onPress={() => setFerrPickerVisible(false)}>
                <Feather name="x" size={20} color={C.muted} />
              </TouchableOpacity>
            </View>
            <View style={s.ferrGrid}>
              {FERRAMENTAS.map(ferr => (
                <TouchableOpacity key={ferr.id}
                  style={[s.ferrItem, { borderColor: C.cardBorder, backgroundColor: C.background }]}
                  onPress={() => abrirFerramenta(ferr.id)}>
                  <Text style={{ fontSize: 22 }}>{ferr.icone}</Text>
                  <Text style={[s.ferrItemTxt, { color: C.text }]}>{ferr.label}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        </View>
      </Modal>

      {/* ── Modal da ferramenta ativa ── */}
      <Modal visible={ferrModalVisible} transparent animationType="slide"
        onRequestClose={limparFerramenta}>
        <View style={s.ferrModal}>
          <View style={[s.ferrSheet, { backgroundColor: C.card }]}>
            <ScrollView showsVerticalScrollIndicator={false}>
              <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <Text style={[s.ferrSheetTitle, { color: C.text }]}>
                  {FERRAMENTAS.find(f => f.id === ferrAtiva)?.icone}{' '}
                  {FERRAMENTAS.find(f => f.id === ferrAtiva)?.label}
                </Text>
                <TouchableOpacity onPress={limparFerramenta}>
                  <Feather name="x" size={20} color={C.muted} />
                </TouchableOpacity>
              </View>

              {/* Vértices selecionados */}
              {vxSelecionados.length > 0 && (
                <View style={{ marginBottom: 12 }}>
                  {vxSelecionados.map((idx, pos) => {
                    const v = editVerts[idx]
                    const labels = ['P1', 'P2', 'P3', 'P', 'A', 'B']
                    const label = ferrAtiva === 'distpl'
                      ? ['P', 'A', 'B'][pos] || `V${pos+1}`
                      : `V${pos+1} (${v.nome || `#${idx+1}`})`
                    return (
                      <View key={idx} style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 4 }}>
                        <View style={{ width: 28, height: 28, borderRadius: 14, backgroundColor: '#378ADD', alignItems: 'center', justifyContent: 'center', marginRight: 8 }}>
                          <Text style={{ color: '#fff', fontSize: 11, fontWeight: '700' }}>
                            {ferrAtiva === 'distpl' ? ['P','A','B'][pos] || pos+1 : pos+1}
                          </Text>
                        </View>
                        <Text style={{ color: C.text, fontSize: 13 }}>
                          {v.nome || `Vértice ${idx+1}`} — {v.lat.toFixed(6)}, {v.lon.toFixed(6)}
                        </Text>
                      </View>
                    )
                  })}
                </View>
              )}

              {/* Inputs por ferramenta */}
              {ferrAtiva === 'irradiacao' && (
                <View style={{ gap: 10, marginBottom: 12 }}>
                  <View>
                    <Text style={{ color: C.muted, fontSize: 12, marginBottom: 4 }}>Azimute (graus decimais ou DMS)</Text>
                    <TextInput style={[s.input, { color: C.text, borderColor: C.cardBorder }]}
                      placeholderTextColor={C.muted} placeholder="Ex: 45 ou 45°30'00&quot;"
                      value={irrAzimute} onChangeText={setIrrAzimute} keyboardType="decimal-pad" />
                  </View>
                  <View>
                    <Text style={{ color: C.muted, fontSize: 12, marginBottom: 4 }}>Distância (metros)</Text>
                    <TextInput style={[s.input, { color: C.text, borderColor: C.cardBorder }]}
                      placeholderTextColor={C.muted} placeholder="Ex: 150.00"
                      value={irrDist} onChangeText={setIrrDist} keyboardType="decimal-pad" />
                  </View>
                  <View>
                    <Text style={{ color: C.muted, fontSize: 12, marginBottom: 4 }}>Nome do ponto (opcional)</Text>
                    <TextInput style={[s.input, { color: C.text, borderColor: C.cardBorder }]}
                      placeholderTextColor={C.muted} placeholder="Ex: P-5"
                      value={irrNome} onChangeText={setIrrNome} />
                  </View>
                </View>
              )}

              {ferrAtiva === 'intersecao' && (
                <View style={{ gap: 10, marginBottom: 12 }}>
                  <View>
                    <Text style={{ color: C.muted, fontSize: 12, marginBottom: 4 }}>Azimute de V1 (graus)</Text>
                    <TextInput style={[s.input, { color: C.text, borderColor: C.cardBorder }]}
                      placeholderTextColor={C.muted} placeholder="Ex: 120.5"
                      value={intAz1} onChangeText={setIntAz1} keyboardType="decimal-pad" />
                  </View>
                  <View>
                    <Text style={{ color: C.muted, fontSize: 12, marginBottom: 4 }}>Azimute de V2 (graus)</Text>
                    <TextInput style={[s.input, { color: C.text, borderColor: C.cardBorder }]}
                      placeholderTextColor={C.muted} placeholder="Ex: 300.0"
                      value={intAz2} onChangeText={setIntAz2} keyboardType="decimal-pad" />
                  </View>
                </View>
              )}

              {ferrAtiva === 'deflexao' && (
                <View style={{ gap: 10, marginBottom: 12 }}>
                  <View>
                    <Text style={{ color: C.muted, fontSize: 12, marginBottom: 4 }}>Ângulo de deflexão (graus)</Text>
                    <TextInput style={[s.input, { color: C.text, borderColor: C.cardBorder }]}
                      placeholderTextColor={C.muted} placeholder="Ex: 90"
                      value={deflAngulo} onChangeText={setDeflAngulo} keyboardType="decimal-pad" />
                  </View>
                  <View style={{ flexDirection: 'row', gap: 8 }}>
                    {(['D', 'E'] as const).map(lado => (
                      <TouchableOpacity key={lado}
                        style={[s.etool, deflLado === lado && { backgroundColor: C.primary, borderColor: C.primary }]}
                        onPress={() => setDeflLado(lado)}>
                        <Text style={{ color: deflLado === lado ? C.primaryText : C.muted, fontWeight: '700' }}>
                          {lado === 'D' ? 'Direita' : 'Esquerda'}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </View>
              )}

              {ferrAtiva === 'rotacao' && (
                <View style={{ gap: 10, marginBottom: 12 }}>
                  <View>
                    <Text style={{ color: C.muted, fontSize: 12, marginBottom: 4 }}>Ângulo de rotação (graus)</Text>
                    <TextInput style={[s.input, { color: C.text, borderColor: C.cardBorder }]}
                      placeholderTextColor={C.muted} placeholder="Ex: 15 (positivo = horário)"
                      value={rotAngulo} onChangeText={setRotAngulo} keyboardType="decimal-pad" />
                  </View>
                  <View style={{ flexDirection: 'row', gap: 8 }}>
                    <TouchableOpacity
                      style={[s.etool, rotOrigemAuto && { backgroundColor: C.primary, borderColor: C.primary }]}
                      onPress={() => setRotOrigemAuto(true)}>
                      <Text style={{ color: rotOrigemAuto ? C.primaryText : C.muted, fontSize: 12 }}>Centróide</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={[s.etool, !rotOrigemAuto && { backgroundColor: C.primary, borderColor: C.primary }]}
                      onPress={() => setRotOrigemAuto(false)}>
                      <Text style={{ color: !rotOrigemAuto ? C.primaryText : C.muted, fontSize: 12 }}>Manual</Text>
                    </TouchableOpacity>
                  </View>
                  {!rotOrigemAuto && (
                    <View style={{ flexDirection: 'row', gap: 8 }}>
                      <TextInput style={[s.input, { flex: 1, color: C.text, borderColor: C.cardBorder }]}
                        placeholderTextColor={C.muted} placeholder="Lat origem"
                        value={rotOrigemLat} onChangeText={setRotOrigemLat} keyboardType="decimal-pad" />
                      <TextInput style={[s.input, { flex: 1, color: C.text, borderColor: C.cardBorder }]}
                        placeholderTextColor={C.muted} placeholder="Lon origem"
                        value={rotOrigemLon} onChangeText={setRotOrigemLon} keyboardType="decimal-pad" />
                    </View>
                  )}
                </View>
              )}

              {ferrAtiva === 'subdivisao' && (
                <View style={{ gap: 10, marginBottom: 12 }}>
                  <Text style={{ color: C.muted, fontSize: 12 }}>
                    Área total: {(calcArea(editVerts) / 10000).toFixed(4)} ha ({calcArea(editVerts).toFixed(1)} m²)
                  </Text>
                  <View>
                    <Text style={{ color: C.muted, fontSize: 12, marginBottom: 4 }}>Área alvo</Text>
                    <TextInput style={[s.input, { color: C.text, borderColor: C.cardBorder }]}
                      placeholderTextColor={C.muted} placeholder="Ex: 1.5"
                      value={subArea} onChangeText={setSubArea} keyboardType="decimal-pad" />
                  </View>
                  <View style={{ flexDirection: 'row', gap: 8 }}>
                    {(['ha', 'm2'] as const).map(un => (
                      <TouchableOpacity key={un}
                        style={[s.etool, subUnidade === un && { backgroundColor: C.primary, borderColor: C.primary }]}
                        onPress={() => setSubUnidade(un)}>
                        <Text style={{ color: subUnidade === un ? C.primaryText : C.muted, fontSize: 12 }}>
                          {un === 'ha' ? 'Hectares' : 'm²'}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </View>
              )}

              {/* Botão calcular */}
              <TouchableOpacity
                style={{ backgroundColor: C.primary, borderRadius: 10, paddingVertical: 12, alignItems: 'center', marginBottom: 12 }}
                onPress={calcular}>
                <Text style={{ color: C.primaryText, fontWeight: '700', fontSize: 15 }}>Calcular</Text>
              </TouchableOpacity>

              {/* Resultados */}
              {resultado && (
                <View style={{ backgroundColor: C.background, borderRadius: 10, padding: 14, gap: 6, marginBottom: 12 }}>
                  <Text style={{ color: C.primary, fontWeight: '700', fontSize: 13, marginBottom: 4 }}>Resultado</Text>

                  {ferrAtiva === 'area' && (
                    <>
                      <Text style={{ color: C.text, fontSize: 14 }}>Área: {resultado.areaM2.toFixed(2)} m²</Text>
                      <Text style={{ color: C.text, fontSize: 14 }}>     = {resultado.areaHa.toFixed(4)} ha</Text>
                      <Text style={{ color: C.text, fontSize: 14 }}>Perímetro: {resultado.perim.toFixed(2)} m</Text>
                    </>
                  )}

                  {ferrAtiva === 'inverso' && (
                    <>
                      <Text style={{ color: C.text, fontSize: 14 }}>Distância: {resultado.dist.toFixed(3)} m</Text>
                      <Text style={{ color: C.text, fontSize: 14 }}>Az V1→V2: {resultado.az}</Text>
                      <Text style={{ color: C.text, fontSize: 14 }}>Az V2→V1: {resultado.azInv}</Text>
                    </>
                  )}

                  {ferrAtiva === 'irradiacao' && (
                    <>
                      <Text style={{ color: C.text, fontSize: 14 }}>Lat: {resultado.lat.toFixed(8)}</Text>
                      <Text style={{ color: C.text, fontSize: 14 }}>Lon: {resultado.lon.toFixed(8)}</Text>
                    </>
                  )}

                  {ferrAtiva === 'intersecao' && (
                    <>
                      <Text style={{ color: C.text, fontSize: 14 }}>Lat: {resultado.lat.toFixed(8)}</Text>
                      <Text style={{ color: C.text, fontSize: 14 }}>Lon: {resultado.lon.toFixed(8)}</Text>
                    </>
                  )}

                  {ferrAtiva === 'distpl' && (
                    <>
                      <Text style={{ color: C.text, fontSize: 14 }}>Distância: {resultado.dist.toFixed(3)} m</Text>
                      <Text style={{ color: C.text, fontSize: 14 }}>
                        Dentro do segmento: {resultado.dentroSegmento ? 'Sim' : 'Não'}
                      </Text>
                    </>
                  )}

                  {ferrAtiva === 'deflexao' && (
                    <>
                      <Text style={{ color: C.text, fontSize: 14 }}>Az entrada: {resultado.azEntradaDms}</Text>
                      <Text style={{ color: C.text, fontSize: 14 }}>Az saída: {resultado.azSaidaDms}</Text>
                    </>
                  )}

                  {ferrAtiva === 'mediaPts' && (
                    <>
                      <Text style={{ color: C.text, fontSize: 14 }}>Lat média: {resultado.lat.toFixed(8)}</Text>
                      <Text style={{ color: C.text, fontSize: 14 }}>Lon média: {resultado.lon.toFixed(8)}</Text>
                      <Text style={{ color: C.text, fontSize: 14 }}>N pontos: {resultado.n}</Text>
                      <Text style={{ color: C.text, fontSize: 14 }}>Desvio padrão: {resultado.dp.toFixed(3)} m</Text>
                    </>
                  )}

                  {ferrAtiva === 'conversao' && (
                    <>
                      <Text style={{ color: C.text, fontSize: 14 }}>Norte: {resultado.norte.toFixed(3)} m</Text>
                      <Text style={{ color: C.text, fontSize: 14 }}>Este:  {resultado.este.toFixed(3)} m</Text>
                      <Text style={{ color: C.text, fontSize: 14 }}>Fuso:  {resultado.fuso}</Text>
                    </>
                  )}

                  {ferrAtiva === 'rotacao' && resultado.rotacionados && (
                    <>
                      <Text style={{ color: C.text, fontSize: 14 }}>Rotação de {resultado.angulo}° calculada.</Text>
                      <Text style={{ color: C.muted, fontSize: 12 }}>{resultado.rotacionados.length} vértices serão rotacionados.</Text>
                    </>
                  )}

                  {ferrAtiva === 'subdivisao' && resultado.pCorte && (
                    <>
                      <Text style={{ color: C.text, fontSize: 14 }}>Ponto de corte:</Text>
                      <Text style={{ color: C.text, fontSize: 13 }}>  Lat: {resultado.pCorte.lat.toFixed(8)}</Text>
                      <Text style={{ color: C.text, fontSize: 13 }}>  Lon: {resultado.pCorte.lon.toFixed(8)}</Text>
                      <Text style={{ color: C.text, fontSize: 14 }}>Área sub-parte: {(resultado.areaSub / 10000).toFixed(4)} ha</Text>
                      <Text style={{ color: C.text, fontSize: 14 }}>Área restante: {(resultado.areaResto / 10000).toFixed(4)} ha</Text>
                    </>
                  )}
                </View>
              )}

              {/* Botões de ação */}
              {resultado && (ferrAtiva === 'irradiacao' || ferrAtiva === 'intersecao' || ferrAtiva === 'mediaPts') && (
                <TouchableOpacity
                  style={{ backgroundColor: '#378ADD', borderRadius: 10, paddingVertical: 12, alignItems: 'center', marginBottom: 8 }}
                  onPress={inserirNoPeriemtro}>
                  <Text style={{ color: '#fff', fontWeight: '700', fontSize: 14 }}>📍 Inserir no Perímetro</Text>
                </TouchableOpacity>
              )}

              {resultado && ferrAtiva === 'subdivisao' && resultado.pCorte && (
                <TouchableOpacity
                  style={{ backgroundColor: '#378ADD', borderRadius: 10, paddingVertical: 12, alignItems: 'center', marginBottom: 8 }}
                  onPress={inserirNoPeriemtro}>
                  <Text style={{ color: '#fff', fontWeight: '700', fontSize: 14 }}>📍 Inserir ponto de corte</Text>
                </TouchableOpacity>
              )}

              {resultado && ferrAtiva === 'rotacao' && resultado.rotacionados && (
                <TouchableOpacity
                  style={{ backgroundColor: '#9B59B6', borderRadius: 10, paddingVertical: 12, alignItems: 'center', marginBottom: 8 }}
                  onPress={aplicarRotacao}>
                  <Text style={{ color: '#fff', fontWeight: '700', fontSize: 14 }}>↩ Aplicar ao Perímetro</Text>
                </TouchableOpacity>
              )}
            </ScrollView>
          </View>
        </View>
      </Modal>
    </View>
  )
}

const s = StyleSheet.create({
  fill:        { flex: 1 },
  centro:      { alignItems: 'center', justifyContent: 'center' },
  header:      { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingBottom: 12, borderBottomWidth: 0.5 },
  backBtn:     { marginRight: 12 },
  titulo:      { fontSize: 18, fontWeight: '700' },
  sub:         { fontSize: 12, marginTop: 1 },
  toolbar:     { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 12, paddingVertical: 8, borderBottomWidth: 0.5, gap: 8 },
  modeGroup:   { flex: 1, flexDirection: 'row', gap: 6 },
  modeBtn:     { paddingHorizontal: 14, paddingVertical: 6, borderRadius: 8 },
  layerBtn:    { padding: 8, borderRadius: 8 },
  editBtn:     { paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8, borderWidth: 1 },
  emptyMsg:    { marginTop: 12, fontSize: 15 },
  layerPanel:  { position: 'absolute', right: 12, borderWidth: 0.5, borderRadius: 10, padding: 12, gap: 10 },
  layerRow:    { flexDirection: 'row', alignItems: 'center', gap: 10 },
  check:       { width: 18, height: 18, borderRadius: 4, borderWidth: 1.5, borderColor: '#555', alignItems: 'center', justifyContent: 'center' },
  editToolbar: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 10, paddingVertical: 6, borderBottomWidth: 0.5, gap: 4 },
  editTag:     { paddingHorizontal: 7, paddingVertical: 3, borderRadius: 5, borderWidth: 1, marginRight: 4 },
  etool:       { paddingHorizontal: 9, paddingVertical: 6, borderRadius: 7, borderWidth: 1, borderColor: '#333330' },
  coordOverlay: { position: 'absolute', bottom: 8, left: 8, right: 8, backgroundColor: 'rgba(0,0,0,0.65)', borderRadius: 8, padding: 8, alignItems: 'center' },
  coordText:    { fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier', fontSize: 13, color: '#ffffff', letterSpacing: 0.2 },
  coordMuted:   { fontSize: 11, color: '#9c9a92', marginTop: 2 },
  // ferramentas
  selecaoOverlay: { position: 'absolute', top: 8, left: 8, right: 8, backgroundColor: '#378ADD22', borderRadius: 8, padding: 10, borderWidth: 1, borderColor: '#378ADD', alignItems: 'center' },
  selecaoTxt:     { color: '#378ADD', fontSize: 13, fontWeight: '700' },
  ferrGrid:       { flexDirection: 'row', flexWrap: 'wrap', gap: 8, padding: 4 },
  ferrItem:       { width: '30%', aspectRatio: 1, borderRadius: 12, borderWidth: 1, alignItems: 'center', justifyContent: 'center', gap: 4 },
  ferrItemTxt:    { fontSize: 11, fontWeight: '600', textAlign: 'center' },
  ferrModal:      { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'flex-end' },
  ferrSheet:      { borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20, maxHeight: '85%' },
  ferrSheetTitle: { fontSize: 18, fontWeight: '700' },
  input:          { borderWidth: 1, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 8, fontSize: 14, backgroundColor: 'transparent' },
})
