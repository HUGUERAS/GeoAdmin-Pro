import { View, Text, StyleSheet } from 'react-native'
import Svg, { Polygon as SvgPolygon, Polyline, Text as SvgText } from 'react-native-svg'
import { Colors } from '../constants/Colors'

type Vertice = { lon: number; lat: number }

function normalizar(vertices?: Vertice[]) {
  return (vertices || []).filter((item) => Number.isFinite(item.lon) && Number.isFinite(item.lat))
}

function transform(verticesA: Vertice[], verticesB: Vertice[], width: number, height: number, pad = 14) {
  const todos = [...verticesA, ...verticesB]
  if (todos.length === 0) {
    return {
      toX: (_lon: number) => width / 2,
      toY: (_lat: number) => height / 2,
    }
  }

  const lons = todos.map((item) => item.lon)
  const lats = todos.map((item) => item.lat)
  const minLon = Math.min(...lons)
  const maxLon = Math.max(...lons)
  const minLat = Math.min(...lats)
  const maxLat = Math.max(...lats)
  const rangeX = maxLon - minLon || 0.0001
  const rangeY = maxLat - minLat || 0.0001
  const escala = Math.min((width - pad * 2) / rangeX, (height - pad * 2) / rangeY)
  const drawW = rangeX * escala
  const drawH = rangeY * escala
  const offX = (width - drawW) / 2
  const offY = (height - drawH) / 2

  return {
    toX: (lon: number) => offX + (lon - minLon) * escala,
    toY: (lat: number) => height - offY - (lat - minLat) * escala,
  }
}

function pontosFechados(vertices: Vertice[], toX: (lon: number) => number, toY: (lat: number) => number) {
  if (vertices.length < 2) return ''
  const coords = vertices.map((item) => `${toX(item.lon)},${toY(item.lat)}`)
  return [...coords, coords[0]].join(' ')
}

export function ClienteGeometryPreview({
  referencia,
  tecnico,
}: {
  referencia?: Vertice[]
  tecnico?: Vertice[]
}) {
  const C = Colors.dark
  const ref = normalizar(referencia)
  const tec = normalizar(tecnico)

  if (ref.length < 3 && tec.length < 3) {
    return (
      <View style={[s.vazio, { backgroundColor: C.background, borderColor: C.cardBorder }]}>
        <Text style={[s.vazioTxt, { color: C.muted }]}>Sem geometria suficiente para comparar.</Text>
        <Text style={[s.vazioSub, { color: C.muted }]}>Importe um croqui ou desenhe ao menos 3 vertices para ver o comparativo.</Text>
      </View>
    )
  }

  const width = 300
  const height = 220
  const xform = transform(ref, tec, width, height)
  const refPts = pontosFechados(ref, xform.toX, xform.toY)
  const tecPts = pontosFechados(tec, xform.toX, xform.toY)

  return (
    <View style={[s.box, { backgroundColor: C.background, borderColor: C.cardBorder }]}>
      <Svg width={width} height={height}>
        {tec.length >= 3 ? (
          <SvgPolygon
            points={tecPts}
            fill="rgba(55,138,221,0.12)"
            stroke={C.info}
            strokeWidth={2}
          />
        ) : null}

        {ref.length >= 3 ? (
          <SvgPolygon
            points={refPts}
            fill="rgba(239,159,39,0.12)"
            stroke={C.primary}
            strokeWidth={2}
          />
        ) : null}

        <SvgText x={12} y={18} fontSize={11} fill={C.primary}>Referencia cliente</SvgText>
        <SvgText x={12} y={34} fontSize={11} fill={C.info}>Perimetro tecnico</SvgText>
      </Svg>

      <View style={s.legenda}>
        <View style={s.legendaItem}>
          <View style={[s.swatch, { backgroundColor: C.primary }]} />
          <Text style={[s.legendaTxt, { color: C.muted }]}>Croqui/importacao do cliente</Text>
        </View>
        <View style={s.legendaItem}>
          <View style={[s.swatch, { backgroundColor: C.info }]} />
          <Text style={[s.legendaTxt, { color: C.muted }]}>Perimetro tecnico ativo</Text>
        </View>
      </View>
    </View>
  )
}

const s = StyleSheet.create({
  box: {
    borderWidth: 0.5,
    borderRadius: 12,
    padding: 10,
    alignItems: 'center',
    gap: 8,
  },
  legenda: { width: '100%', gap: 6 },
  legendaItem: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  legendaTxt: { fontSize: 12 },
  swatch: { width: 12, height: 12, borderRadius: 999 },
  vazio: {
    minHeight: 120,
    borderWidth: 0.5,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
    gap: 6,
  },
  vazioTxt: { fontSize: 12, textAlign: 'center' },
  vazioSub: { fontSize: 11, textAlign: 'center', lineHeight: 16 },
})
