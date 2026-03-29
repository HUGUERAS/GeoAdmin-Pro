import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, ScrollView, StyleSheet, Alert, Platform } from 'react-native'
import { Colors } from '../../../constants/Colors'

type Ponto = { norte: string; este: string }

const VAZIO: Ponto = { norte: '', este: '' }

function decimalParaDms(graus: number): string {
  const g = Math.floor(graus)
  const mf = (graus - g) * 60
  const m = Math.floor(mf)
  const s = ((mf - m) * 60).toFixed(2)
  return `${String(g).padStart(2, '0')}°${String(m).padStart(2, '0')}'${String(s).padStart(5, '0')}"`
}

type Resultado = {
  distancia: number
  azimute: number
  azimuteDms: string
  azConj: number
  azConjDms: string
}

function calcular(p1: Ponto, p2: Ponto): Resultado | null {
  const y1 = parseFloat(p1.norte), x1 = parseFloat(p1.este)
  const y2 = parseFloat(p2.norte), x2 = parseFloat(p2.este)
  if ([x1, y1, x2, y2].some(isNaN)) return null
  const dx = x2 - x1
  const dy = y2 - y1
  const dist = Math.sqrt(dx * dx + dy * dy)
  if (dist < 1e-6) return null
  let az = Math.atan2(dx, dy) * 180 / Math.PI
  if (az < 0) az += 360
  const azConj = (az + 180) % 360
  return {
    distancia: dist,
    azimute: az,
    azimuteDms: decimalParaDms(az),
    azConj,
    azConjDms: decimalParaDms(azConj),
  }
}

export default function LinhaScreen() {
  const C = Colors.dark
  const [p1, setP1] = useState<Ponto>(VAZIO)
  const [p2, setP2] = useState<Ponto>(VAZIO)
  const [res, setRes] = useState<Resultado | null>(null)

  const calcularRes = () => {
    const r = calcular(p1, p2)
    if (!r) {
      Alert.alert('Dados inválidos', 'Preencha Norte e Este dos dois pontos.\nOs pontos não podem ser coincidentes.')
      return
    }
    setRes(r)
  }

  const limpar = () => { setP1(VAZIO); setP2(VAZIO); setRes(null) }

  const CampoRow = ({ titulo, estado, setEstado }: { titulo: string; estado: Ponto; setEstado: (p: Ponto) => void }) => (
    <>
      <Text style={[s.secao, { color: C.primary }]}>{titulo}</Text>
      <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
        <View style={s.campoRow}>
          <View style={s.campoHalf}>
            <Text style={[s.label, { color: C.muted }]}>NORTE (m)</Text>
            <TextInput
              style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
              value={estado.norte}
              onChangeText={v => { setEstado({ ...estado, norte: v }); setRes(null) }}
              placeholder="7395000.000"
              placeholderTextColor={C.muted}
              keyboardType="numeric"
              returnKeyType="next"
            />
          </View>
          <View style={s.campoHalf}>
            <Text style={[s.label, { color: C.muted }]}>ESTE (m)</Text>
            <TextInput
              style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
              value={estado.este}
              onChangeText={v => { setEstado({ ...estado, este: v }); setRes(null) }}
              placeholder="313500.000"
              placeholderTextColor={C.muted}
              keyboardType="numeric"
              returnKeyType="next"
            />
          </View>
        </View>
      </View>
    </>
  )

  return (
    <ScrollView style={[s.container, { backgroundColor: C.background }]} keyboardShouldPersistTaps="handled">
      <View style={[s.header, { backgroundColor: C.card, borderBottomColor: C.cardBorder }]}>
        <Text style={[s.titulo, { color: C.text }]}>Linha</Text>
        <Text style={[s.sub, { color: C.muted }]}>Distância e azimute entre dois pontos UTM</Text>
      </View>

      <View style={s.body}>
        <CampoRow titulo="Ponto Inicial" estado={p1} setEstado={setP1} />
        <CampoRow titulo="Ponto Final" estado={p2} setEstado={setP2} />

        <View style={s.btns}>
          <TouchableOpacity style={[s.btnSec, { borderColor: C.cardBorder }]} onPress={limpar}>
            <Text style={[s.btnSecTxt, { color: C.muted }]}>Limpar</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[s.btnPri, { backgroundColor: C.primary }]} onPress={calcularRes}>
            <Text style={[s.btnPriTxt, { color: C.primaryText }]}>Calcular</Text>
          </TouchableOpacity>
        </View>

        {res && (
          <View style={[s.resultado, { backgroundColor: C.card, borderColor: C.primary }]}>
            <Text style={[s.resLabel, { color: C.muted }]}>Resultado</Text>
            <View style={[s.resBloco, { borderBottomColor: C.cardBorder }]}>
              <Text style={[s.resValorGrande, { color: C.primary }]}>{res.distancia.toFixed(3)} m</Text>
              <Text style={[s.resSub, { color: C.muted }]}>Distância</Text>
            </View>
            <View style={s.resRow}>
              <View style={s.resItem}>
                <Text style={[s.resValor, { color: C.text }]}>{res.azimuteDms}</Text>
                <Text style={[s.resSub, { color: C.muted }]}>Azimute</Text>
                <Text style={[s.resDecimal, { color: C.muted }]}>{res.azimute.toFixed(6)}°</Text>
              </View>
              <View style={[s.resDivider, { backgroundColor: C.cardBorder }]} />
              <View style={s.resItem}>
                <Text style={[s.resValor, { color: C.text }]}>{res.azConjDms}</Text>
                <Text style={[s.resSub, { color: C.muted }]}>Conjugado</Text>
                <Text style={[s.resDecimal, { color: C.muted }]}>{res.azConj.toFixed(6)}°</Text>
              </View>
            </View>
          </View>
        )}

        <TouchableOpacity
          style={[s.gabarito, { borderColor: C.cardBorder }]}
          onPress={() => {
            setP1({ norte: '7395000.000', este: '313500.000' })
            setP2({ norte: '7395400.000', este: '313800.000' })
            setRes(null)
          }}
        >
          <Text style={[s.gabaritoTxt, { color: C.muted }]}>Gabarito: P1(7395000,313500)→P2(7395400,313800) = 500 m, Az≈36°52'11.63"</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  )
}

const s = StyleSheet.create({
  container:       { flex: 1 },
  header:          { padding: 20, paddingTop: 56, borderBottomWidth: 0.5 },
  titulo:          { fontSize: 24, fontWeight: '700' },
  sub:             { fontSize: 13, marginTop: 2 },
  body:            { padding: 16 },
  secao:           { fontSize: 12, fontWeight: '700', marginBottom: 8, marginTop: 16, textTransform: 'uppercase', letterSpacing: 0.5 },
  card:            { borderRadius: 10, borderWidth: 0.5, padding: 14, marginBottom: 4 },
  campoRow:        { flexDirection: 'row', gap: 10 },
  campoHalf:       { flex: 1 },
  label:           { fontSize: 10, fontWeight: '600', marginBottom: 5, textTransform: 'uppercase', letterSpacing: 0.3 },
  input:           { borderWidth: 0.5, borderRadius: 8, padding: 12, fontSize: 15, fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  btns:            { flexDirection: 'row', gap: 10, marginTop: 20 },
  btnPri:          { flex: 2, padding: 16, borderRadius: 10, alignItems: 'center', justifyContent: 'center', minHeight: 52 },
  btnPriTxt:       { fontSize: 16, fontWeight: '700' },
  btnSec:          { flex: 1, padding: 16, borderRadius: 10, alignItems: 'center', borderWidth: 0.5, minHeight: 52 },
  btnSecTxt:       { fontSize: 16, fontWeight: '500' },
  resultado:       { marginTop: 20, borderRadius: 12, borderWidth: 1, padding: 20 },
  resLabel:        { fontSize: 10, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 14 },
  resBloco:        { alignItems: 'center', paddingBottom: 14, marginBottom: 14, borderBottomWidth: 0.5 },
  resRow:          { flexDirection: 'row', alignItems: 'flex-start' },
  resItem:         { flex: 1, alignItems: 'center' },
  resValorGrande:  { fontSize: 30, fontWeight: '700', fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  resValor:        { fontSize: 18, fontWeight: '700', fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  resSub:          { fontSize: 12, marginTop: 4 },
  resDecimal:      { fontSize: 11, marginTop: 2 },
  resDivider:      { width: 0.5, height: 60, marginHorizontal: 8, marginTop: 4 },
  gabarito:        { marginTop: 16, borderWidth: 0.5, borderRadius: 8, padding: 12, borderStyle: 'dashed' },
  gabaritoTxt:     { fontSize: 12, textAlign: 'center' },
})
