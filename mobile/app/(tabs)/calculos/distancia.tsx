import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, ScrollView, StyleSheet, Alert, ActivityIndicator, Platform } from 'react-native'
import { Colors } from '../../../constants/Colors'
import { API_URL } from '../../../constants/Api'

type PontoState = { norte: string; este: string }
type Resultado = {
  distancia_m: number
  pe_perpendicular: { norte: number; este: number }
  dentro_do_segmento: boolean
}

const VAZIO: PontoState = { norte: '', este: '' }

export default function DistanciaScreen() {
  const C = Colors.dark
  const [ponto, setPonto] = useState<PontoState>(VAZIO)
  const [linhaA, setLinhaA] = useState<PontoState>(VAZIO)
  const [linhaB, setLinhaB] = useState<PontoState>(VAZIO)
  const [resultado, setResultado] = useState<Resultado | null>(null)
  const [loading, setLoading] = useState(false)

  const limpar = () => {
    setPonto(VAZIO); setLinhaA(VAZIO); setLinhaB(VAZIO); setResultado(null)
  }

  const calcular = async () => {
    const pN = parseFloat(ponto.norte), pE = parseFloat(ponto.este)
    const aN = parseFloat(linhaA.norte), aE = parseFloat(linhaA.este)
    const bN = parseFloat(linhaB.norte), bE = parseFloat(linhaB.este)
    if ([pN, pE, aN, aE, bN, bE].some(isNaN)) {
      Alert.alert('Dados incompletos', 'Preencha Norte e Este de todos os pontos.')
      return
    }
    setLoading(true)
    setResultado(null)
    try {
      const res = await fetch(`${API_URL}/geo/distancia-ponto-linha`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ponto: { norte: pN, este: pE },
          linha_a: { norte: aN, este: aE },
          linha_b: { norte: bN, este: bE },
        }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      setResultado(await res.json())
    } catch (e: any) {
      Alert.alert('Erro', e.message || 'Não foi possível calcular.\nVerifique a conexão com o backend.')
    } finally {
      setLoading(false)
    }
  }

  const CampoRow = ({ titulo, estado, setEstado }: { titulo: string; estado: PontoState; setEstado: (p: PontoState) => void }) => (
    <>
      <Text style={[s.secao, { color: C.primary }]}>{titulo}</Text>
      <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
        <View style={s.campoRow}>
          <View style={s.campoHalf}>
            <Text style={[s.label, { color: C.muted }]}>NORTE (m)</Text>
            <TextInput
              style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
              value={estado.norte}
              onChangeText={v => setEstado({ ...estado, norte: v })}
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
              onChangeText={v => setEstado({ ...estado, este: v })}
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
        <Text style={[s.titulo, { color: C.text }]}>Dist. Ponto-Linha</Text>
        <Text style={[s.sub, { color: C.muted }]}>Distância perpendicular de ponto a segmento</Text>
      </View>

      <View style={s.body}>
        <CampoRow titulo="Ponto P" estado={ponto} setEstado={setPonto} />
        <CampoRow titulo="Linha — Ponto A" estado={linhaA} setEstado={setLinhaA} />
        <CampoRow titulo="Linha — Ponto B" estado={linhaB} setEstado={setLinhaB} />

        <View style={s.btns}>
          <TouchableOpacity style={[s.btnSec, { borderColor: C.cardBorder }]} onPress={limpar}>
            <Text style={[s.btnSecTxt, { color: C.muted }]}>Limpar</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[s.btnPri, { backgroundColor: C.primary }]} onPress={calcular} disabled={loading}>
            {loading ? <ActivityIndicator color={C.primaryText} /> : <Text style={[s.btnPriTxt, { color: C.primaryText }]}>Calcular</Text>}
          </TouchableOpacity>
        </View>

        {resultado && (
          <View style={[s.resultado, { backgroundColor: C.card, borderColor: C.primary }]}>
            <Text style={[s.resLabel, { color: C.muted }]}>Resultado</Text>
            <View style={s.resRow}>
              <View style={s.resItem}>
                <Text style={[s.resValor, { color: C.primary }]}>{resultado.distancia_m.toFixed(4)} m</Text>
                <Text style={[s.resSub, { color: C.muted }]}>Distância perpendicular</Text>
              </View>
            </View>
            <View style={[s.sepH, { backgroundColor: C.cardBorder }]} />
            <Text style={[s.resSub2, { color: C.muted }]}>Pé da perpendicular</Text>
            <View style={s.resRow}>
              <View style={s.resItem}>
                <Text style={[s.resValorSm, { color: C.text }]}>{resultado.pe_perpendicular.norte.toFixed(3)}</Text>
                <Text style={[s.resSub, { color: C.muted }]}>Norte (m)</Text>
              </View>
              <View style={[s.resDivider, { backgroundColor: C.cardBorder }]} />
              <View style={s.resItem}>
                <Text style={[s.resValorSm, { color: C.text }]}>{resultado.pe_perpendicular.este.toFixed(3)}</Text>
                <Text style={[s.resSub, { color: C.muted }]}>Este (m)</Text>
              </View>
            </View>
            <View style={[s.badge, { backgroundColor: resultado.dentro_do_segmento ? C.primary : C.cardBorder }]}>
              <Text style={[s.badgeTxt, { color: resultado.dentro_do_segmento ? C.primaryText : C.muted }]}>
                {resultado.dentro_do_segmento ? 'Dentro do segmento' : 'Fora do segmento (projeção)'}
              </Text>
            </View>
          </View>
        )}

        <TouchableOpacity
          style={[s.gabarito, { borderColor: C.cardBorder }]}
          onPress={() => {
            setPonto({ norte: '7395050', este: '313550' })
            setLinhaA({ norte: '7395000', este: '313500' })
            setLinhaB({ norte: '7395000', este: '313600' })
            setResultado(null)
          }}
        >
          <Text style={[s.gabaritoTxt, { color: C.muted }]}>Gabarito: P(7395050,313550), A-B segmento horizontal → dist≈50 m</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  )
}

const s = StyleSheet.create({
  container:   { flex: 1 },
  header:      { padding: 20, paddingTop: 56, borderBottomWidth: 0.5 },
  titulo:      { fontSize: 24, fontWeight: '700' },
  sub:         { fontSize: 13, marginTop: 2 },
  body:        { padding: 16 },
  secao:       { fontSize: 12, fontWeight: '700', marginBottom: 8, marginTop: 16, textTransform: 'uppercase', letterSpacing: 0.5 },
  card:        { borderRadius: 10, borderWidth: 0.5, padding: 14, marginBottom: 4 },
  campoRow:    { flexDirection: 'row', gap: 10 },
  campoHalf:   { flex: 1 },
  label:       { fontSize: 10, fontWeight: '600', marginBottom: 5, textTransform: 'uppercase', letterSpacing: 0.3 },
  input:       { borderWidth: 0.5, borderRadius: 8, padding: 12, fontSize: 15, fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  btns:        { flexDirection: 'row', gap: 10, marginTop: 20 },
  btnPri:      { flex: 2, padding: 16, borderRadius: 10, alignItems: 'center', justifyContent: 'center', minHeight: 52 },
  btnPriTxt:   { fontSize: 16, fontWeight: '700' },
  btnSec:      { flex: 1, padding: 16, borderRadius: 10, alignItems: 'center', borderWidth: 0.5, minHeight: 52 },
  btnSecTxt:   { fontSize: 16, fontWeight: '500' },
  resultado:   { marginTop: 20, borderRadius: 12, borderWidth: 1, padding: 20 },
  resLabel:    { fontSize: 10, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 14 },
  resRow:      { flexDirection: 'row', alignItems: 'center' },
  resItem:     { flex: 1, alignItems: 'center' },
  resValor:    { fontSize: 22, fontWeight: '700', fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  resValorSm:  { fontSize: 17, fontWeight: '700', fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  resSub:      { fontSize: 12, marginTop: 4 },
  resSub2:     { fontSize: 10, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.3, marginBottom: 10 },
  resDivider:  { width: 0.5, height: 40, marginHorizontal: 16 },
  sepH:        { height: 0.5, marginVertical: 14 },
  badge:       { marginTop: 14, borderRadius: 6, padding: 8, alignItems: 'center' },
  badgeTxt:    { fontSize: 12, fontWeight: '600' },
  gabarito:    { marginTop: 16, borderWidth: 0.5, borderRadius: 8, padding: 12, borderStyle: 'dashed' },
  gabaritoTxt: { fontSize: 12, textAlign: 'center' },
})
