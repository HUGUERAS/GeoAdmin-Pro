import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import {
  View, Text, StyleSheet, TouchableOpacity,
  ActivityIndicator, Alert, Dimensions, PanResponder, GestureResponderEvent, Platform,
} from 'react-native'
import { WebView } from 'react-native-webview'
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

function render(layers) {
  lg.clearLayers();
  if (!pontos.length) return;
  var ll = pontos.map(function(p){return [p.lat,p.lon];});
  if (layers.poligono && pontos.length > 1) {
    L.polygon(ll,{color:'#EF9F27',weight:2.5,fillOpacity:0.07}).addTo(lg);
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
    });
  }
  map.fitBounds(ll,{padding:[40,40]});
}

function updateMap(d) {
  pontos = d.pontos||[];
  render(d.layers||{pontos:true,poligono:true,rotulos:true});
}

document.addEventListener('message',function(e){try{var d=JSON.parse(e.data);updateMap(d);}catch(_){}});
window.addEventListener('message',function(e){try{var d=JSON.parse(e.data);updateMap(d);}catch(_){}});
</script>
</body></html>`

// ── WebView satellite view ────────────────────────────────────────────────────

function MapaWebView({ pontos, layers }: { pontos: Ponto[]; layers: Layers }) {
  const webRef  = useRef<WebView>(null)
  const ready   = useRef(false)

  const inject = useCallback((pts: Ponto[], lyr: Layers) => {
    if (!ready.current || !webRef.current) return
    webRef.current.injectJavaScript(
      `updateMap(${JSON.stringify({ pontos: pts, layers: lyr })});true;`
    )
  }, [])

  useEffect(() => { inject(pontos, layers) }, [pontos, layers, inject])

  return (
    <WebView
      ref={webRef}
      style={StyleSheet.absoluteFillObject}
      source={{ html: MAP_HTML }}
      javaScriptEnabled
      originWhitelist={['*']}
      onLoad={() => { ready.current = true; inject(pontos, layers) }}
    />
  )
}

// ── CAD view ──────────────────────────────────────────────────────────────────

function CadView({ pontos, layers, C, editMode, editTool, editVertices, origVertices,
  onVertexDrag, onVertexDelete, onMidpointAdd, onDragStart }: any) {
  const { width: W, height: H } = Dimensions.get('window')
  const svgH = H - 56 - 50 - 50
  const TOUCH_R = 20

  const allPts = useMemo(
    () => editMode ? [...(editVertices || []), ...(origVertices || [])] : pontos,
    [editMode, editVertices, origVertices, pontos]
  )
  const xform = useMemo(
    () => computeTransform(allPts.length ? allPts : pontos, W, svgH),
    [allPts, W, svgH]
  )
  const { toX, toY, fromX, fromY, minLon, maxLon, minLat, maxLat } = xform

  const stateRef = useRef({ editMode, editTool, editVertices, toX, toY, fromX, fromY, onVertexDrag, onDragStart })
  useEffect(() => {
    stateRef.current = { editMode, editTool, editVertices, toX, toY, fromX, fromY, onVertexDrag, onDragStart }
  })

  const panRef = useRef<{ idx: number } | null>(null)

  const panResponder = useRef(PanResponder.create({
    onStartShouldSetPanResponder: () =>
      stateRef.current.editMode && stateRef.current.editTool === 'mover',
    onMoveShouldSetPanResponder: () =>
      stateRef.current.editMode && stateRef.current.editTool === 'mover',
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

      {!editMode && layers.poligono && pontos.length > 1 && (
        <SvgPolyline points={closedPts(pontos)} stroke={C.primary} strokeWidth={1.5}
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
      {editMode && editTool === 'adicionar' && editVertices?.map((_: any, i: number) => {
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
        const color = editTool === 'deletar' ? '#E24B4A' : C.primary
        return (
          <Circle key={`ev${i}`} cx={x} cy={y} r={8}
            fill={color} stroke="#fff" strokeWidth={1.5}
            onPress={() => editTool === 'deletar' && onVertexDelete(i)} />
        )
      })}
    </Svg>
  )
}

// ── Main screen ───────────────────────────────────────────────────────────────

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

  const [editMode,    setEditMode] = useState(false)
  const [editTool,    setEditTool] = useState<EditTool>('mover')
  const [editVerts,   setEditVerts] = useState<Vertice[]>([])
  const [origVerts,   setOrigVerts] = useState<Vertice[]>([])
  const [editHistory, setEditHist] = useState<Vertice[][]>([])

  useEffect(() => {
    fetch(`${API_URL}/projetos/${id}`)
      .then(r => r.json())
      .then(data => {
        setProjeto(data)
        setPontos((data.pontos || []).filter((p: any) => p.lon != null && p.lat != null))
      })
      .catch(() => Alert.alert('Erro', 'Não foi possível carregar o projeto.'))
      .finally(() => setLoading(false))
  }, [id])

  const region = useMemo(() => {
    if (!pontos.length) return undefined
    const lons = pontos.map(p => p.lon), lats = pontos.map(p => p.lat)
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

  const entrarEdit = useCallback(async () => {
    if (!pontos.length) { Alert.alert('Sem pontos', 'Projeto sem pontos com coordenadas.'); return }
    setMode('cad')
    const verts: Vertice[] = pontos.map(p => ({ lon: p.lon, lat: p.lat, nome: p.nome }))
    setOrigVerts(verts)
    setEditVerts([...verts])
    setEditHist([])
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
    } catch {}
  }, [pontos, projeto, id])

  const pushHist = useCallback((verts: Vertice[]) => {
    setEditHist(prev => [...prev.slice(-49), verts.map(v => ({ ...v }))])
  }, [])

  const handleDragStart = useCallback(() => {
    setEditVerts(prev => {
      setEditHist(h => [...h.slice(-49), prev.map(v => ({ ...v }))])
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
    setEditHist(prev => {
      if (!prev.length) return prev
      const last = prev[prev.length - 1]
      setEditVerts(last)
      return prev.slice(0, -1)
    })
  }, [])

  const salvarEdit = useCallback(async () => {
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
      if (!res.ok) throw new Error()
      Alert.alert('Salvo!', `Perímetro editado salvo — ${editVerts.length} vértices.`)
      setEditMode(false)
    } catch {
      Alert.alert('Erro', 'Falha ao salvar o perímetro.')
    }
  }, [id, projeto, editVerts])

  const cancelarEdit = useCallback(() => {
    Alert.alert('Cancelar edição', 'Descartar alterações?', [
      { text: 'Não', style: 'cancel' },
      { text: 'Sim', onPress: () => setEditMode(false) },
    ])
  }, [])

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
          <TouchableOpacity style={s.etool} onPress={desfazer}>
            <Text style={{ color: C.muted, fontSize: 12 }}>↩</Text>
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
        {pontos.length === 0 ? (
          <View style={[s.fill, s.centro]}>
            <Feather name="map-pin" size={40} color={C.muted} />
            <Text style={[s.emptyMsg, { color: C.muted }]}>Nenhum ponto com coordenadas</Text>
          </View>
        ) : mode === 'mapa' ? (
          <MapaWebView pontos={pontos} layers={layers} />
        ) : (
          <CadView
            pontos={pontos} layers={layers} C={C}
            editMode={editMode} editTool={editTool}
            editVertices={editVerts} origVertices={origVerts}
            onVertexDrag={handleVertexDrag}
            onVertexDelete={handleVertexDelete}
            onMidpointAdd={handleMidpointAdd}
            onDragStart={handleDragStart}
          />
        )}

        {/* Coordinate overlay — Padrão 7 */}
        {pontos.length > 0 && !editMode && region && (
          <View style={s.coordOverlay} pointerEvents="none">
            <Text style={s.coordText}>
              {`Lat  ${region.latitude.toFixed(5)}°   Lon  ${region.longitude.toFixed(5)}°`}
            </Text>
            <Text style={s.coordMuted}>{`N pontos: ${pontos.length}`}</Text>
          </View>
        )}
      </View>

      {/* Layer panel */}
      {!editMode && showLayers && (
        <View style={[s.layerPanel, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <Text style={{ color: C.muted, fontSize: 11, fontWeight: '700', letterSpacing: 0.5 }}>CAMADAS</Text>
            <TouchableOpacity onPress={() => setShowLayers(false)} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
              <Feather name="x" size={16} color={C.muted} />
            </TouchableOpacity>
          </View>
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
  fill:        { flex: 1 },
  centro:      { alignItems: 'center', justifyContent: 'center' },
  header:      { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingTop: 56, paddingBottom: 12, borderBottomWidth: 0.5 },
  backBtn:     { marginRight: 12 },
  titulo:      { fontSize: 18, fontWeight: '700' },
  sub:         { fontSize: 12, marginTop: 1 },
  toolbar:     { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 12, paddingVertical: 8, borderBottomWidth: 0.5, gap: 8 },
  modeGroup:   { flex: 1, flexDirection: 'row', gap: 6 },
  modeBtn:     { paddingHorizontal: 14, paddingVertical: 6, borderRadius: 8 },
  layerBtn:    { padding: 8, borderRadius: 8 },
  editBtn:     { paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8, borderWidth: 1 },
  emptyMsg:    { marginTop: 12, fontSize: 15 },
  layerPanel:  { position: 'absolute', right: 12, top: 56 + 50 + 12, borderWidth: 0.5, borderRadius: 10, padding: 12, gap: 10 },
  layerRow:    { flexDirection: 'row', alignItems: 'center', gap: 10 },
  check:       { width: 18, height: 18, borderRadius: 4, borderWidth: 1.5, borderColor: '#555', alignItems: 'center', justifyContent: 'center' },
  editToolbar: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 10, paddingVertical: 6, borderBottomWidth: 0.5, gap: 4 },
  editTag:     { paddingHorizontal: 7, paddingVertical: 3, borderRadius: 5, borderWidth: 1, marginRight: 4 },
  etool:       { paddingHorizontal: 9, paddingVertical: 6, borderRadius: 7, borderWidth: 1, borderColor: '#333330' },
  coordOverlay: { position: 'absolute', bottom: 8, left: 8, right: 8, backgroundColor: 'rgba(0,0,0,0.65)', borderRadius: 8, padding: 8, alignItems: 'center' },
  coordText:    { fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier', fontSize: 13, color: '#ffffff', letterSpacing: 0.2 },
  coordMuted:   { fontSize: 11, color: '#9c9a92', marginTop: 2 },
})
