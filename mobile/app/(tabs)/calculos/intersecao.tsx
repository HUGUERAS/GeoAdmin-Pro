import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, ScrollView, StyleSheet, Alert, ActivityIndicator, Platform } from 'react-native'
import { Colors } from '../../../constants/Colors'
import { API_URL } from '../../../constants/Api'

type SemiretaState = { norte: string; este: string; azimute: string }
type Resultado = { norte: number; este: number }

const VAZIO: SemiretaState = { norte: '', este: '', azimute: '' }

export default function IntersecaoScreen() {
  const C = Colors.dark
  const [p1, setP1] = useState<SemiretaState>(VAZIO)
  const [p2, setP2] = useState<SemiretaState>(VAZIO)
  const [resultado, setResultado] = useState<Resultado | null>(null)
  const [loading, setLoading] = useState(false)

  const limpar = () => { setP1(VAZIO); setP2(VAZIO); setResultado(null) }

  const calcular = async () => {
    const n1 = parseFloat(p1.norte), e1 = parseFloat(p1.este), az1 = parseFloat(p1.azimute)
    const n2 = parseFloat(p2.norte), e2 = parseFloat(p2.este), az2 = parseFloat(p2.azimute)
    if ([n1, e1, az1, n2, e2, az2].some(isNaN)) {
      Alert.alert('Dados incompletos', 'Preencha Norte, Este e Azimute dos dois pontos.')
      return
    }
    setLoading(true)
    setResultado(null)
    try {
      const res = await fetch(`${API_URL}/geo/intersecao`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          p1: { norte: n1, este: e1, azimute: az1 },
          p2: { norte: n2, este: e2, azimute: az2 },
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

  const Campo = ({ label, value, onChange, placeholder }: any) => (
    <View style={s.campo}>
      <Text style={[s.label, { color: C.muted }]}>{label}</Text>
      <TextInput
        style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
        value={value} onChangeText={onChange} placeholder={placeholder}
        placeholderTextColor={C.muted} keyboardType="numeric" returnKeyType="next"
      />
    </View>
  )

  return (
    <ScrollView style={[s.container, { backgroundColor: C.background }]} keyboardShouldPersistTaps="handled">
      <View style={[s.header, { backgroundColor: C.card, borderBottomColor: C.cardBorder }]}>
        <Text style={[s.titulo, { color: C.text }]}>Interseção</Text>
        <Text style={[s.sub, { color: C.muted }]}>Interseção de duas semiretas por azimute</Text>
      </View>

      <View style={s.body}>
        <Text style={[s.secao, { color: C.primary }]}>Ponto 1</Text>
        <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
          <Campo label="NORTE (m)"   value={p1.norte}   onChange={(v: string) => setP1(p => ({ ...p, norte: v }))}   placeholder="7395000.000" />
          <Campo label="ESTE (m)"    value={p1.este}    onChange={(v: string) => setP1(p => ({ ...p, este: v }))}    placeholder="313500.000" />
          <Campo label="AZIMUTE (°)" value={p1.azimute} onChange={(v: string) => setP1(p => ({ ...p, azimute: v }))} placeholder="45.000" />
        </View>

        <Text style={[s.secao, { color: C.primary }]}>Ponto 2</Text>
        <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
          <Campo label="NORTE (m)"   value={p2.norte}   onChange={(v: string) => setP2(p => ({ ...p, norte: v }))}   placeholder="7395000.000" />
          <Campo label="ESTE (m)"    value={p2.este}    onChange={(v: string) => setP2(p => ({ ...p, este: v }))}    placeholder="313600.000" />
          <Campo label="AZIMUTE (°)" value={p2.azimute} onChange={(v: string) => setP2(p => ({ ...p, azimute: v }))} placeholder="315.000" />
        </View>

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
            <Text style={[s.resLabel, { color: C.muted }]}>Ponto de Interseção</Text>
            <View style={s.resRow}>
              <View style={s.resItem}>
                <Text style={[s.resValor, { color: C.primary }]}>{resultado.norte.toFixed(3)}</Text>
                <Text style={[s.resSub, { color: C.muted }]}>Norte (m)</Text>
              </View>
              <View style={[s.resDivider, { backgroundColor: C.cardBorder }]} />
              <View style={s.resItem}>
                <Text style={[s.resValor, { color: C.primary }]}>{resultado.este.toFixed(3)}</Text>
                <Text style={[s.resSub, { color: C.muted }]}>Este (m)</Text>
              </View>
            </View>
          </View>
        )}

        <TouchableOpacity
          style={[s.gabarito, { borderColor: C.cardBorder }]}
          onPress={() => {
            setP1({ norte: '7395000', este: '313500', azimute: '45.000' })
            setP2({ norte: '7395000', este: '313600', azimute: '315.000' })
            setResultado(null)
          }}
        >
          <Text style={[s.gabaritoTxt, { color: C.muted }]}>Gabarito: P1(Az=45°) × P2(Az=315°) → P≈N7395050 E313550</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  )
}

const s = StyleSheet.create({
  container:  { flex: 1 },
  header:     { padding: 20, paddingTop: 56, borderBottomWidth: 0.5 },
  titulo:     { fontSize: 24, fontWeight: '700' },
  sub:        { fontSize: 13, marginTop: 2 },
  body:       { padding: 16 },
  secao:      { fontSize: 12, fontWeight: '700', marginBottom: 8, marginTop: 16, textTransform: 'uppercase', letterSpacing: 0.5 },
  card:       { borderRadius: 10, borderWidth: 0.5, padding: 14, marginBottom: 4 },
  campo:      { marginBottom: 12 },
  label:      { fontSize: 10, fontWeight: '600', marginBottom: 5, textTransform: 'uppercase', letterSpacing: 0.3 },
  input:      { borderWidth: 0.5, borderRadius: 8, padding: 12, fontSize: 16, fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  btns:       { flexDirection: 'row', gap: 10, marginTop: 20 },
  btnPri:     { flex: 2, padding: 16, borderRadius: 10, alignItems: 'center', justifyContent: 'center', minHeight: 52 },
  btnPriTxt:  { fontSize: 16, fontWeight: '700' },
  btnSec:     { flex: 1, padding: 16, borderRadius: 10, alignItems: 'center', borderWidth: 0.5, minHeight: 52 },
  btnSecTxt:  { fontSize: 16, fontWeight: '500' },
  resultado:  { marginTop: 20, borderRadius: 12, borderWidth: 1, padding: 20 },
  resLabel:   { fontSize: 10, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 14 },
  resRow:     { flexDirection: 'row', alignItems: 'center' },
  resItem:    { flex: 1, alignItems: 'center' },
  resValor:   { fontSize: 22, fontWeight: '700', fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  resSub:     { fontSize: 14, marginTop: 4 },
  resDivider: { width: 0.5, height: 40, marginHorizontal: 16 },
  gabarito:   { marginTop: 16, borderWidth: 0.5, borderRadius: 8, padding: 12, borderStyle: 'dashed' },
  gabaritoTxt:{ fontSize: 12, textAlign: 'center' },
})
