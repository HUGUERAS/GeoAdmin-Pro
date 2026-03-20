import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, ScrollView, StyleSheet, Alert, Platform } from 'react-native'
import { Colors } from '../../../constants/Colors'

type Lado = 'D' | 'E'

function decimalParaDms(graus: number): string {
  const g = Math.floor(graus)
  const mf = (graus - g) * 60
  const m = Math.floor(mf)
  const s = ((mf - m) * 60).toFixed(3)
  return `${g}°${String(m).padStart(2, '0')}'${String(s).padStart(6, '0')}"`
}

export default function DeflexaoScreen() {
  const C = Colors.dark
  const [azEntrada, setAzEntrada] = useState('')
  const [deflexao, setDeflexao] = useState('')
  const [lado, setLado] = useState<Lado>('D')
  const [resultado, setResultado] = useState<{ decimal: number; dms: string } | null>(null)

  const calcular = () => {
    const az = parseFloat(azEntrada)
    const def = parseFloat(deflexao)
    if (isNaN(az) || isNaN(def)) {
      Alert.alert('Dados incompletos', 'Preencha o Azimute de Entrada e a Deflexão.')
      return
    }
    const sinal = lado === 'D' ? 1 : -1
    const azSaida = ((az + sinal * def) % 360 + 360) % 360
    setResultado({ decimal: azSaida, dms: decimalParaDms(azSaida) })
  }

  const limpar = () => {
    setAzEntrada('')
    setDeflexao('')
    setLado('D')
    setResultado(null)
  }

  return (
    <ScrollView style={[s.container, { backgroundColor: C.background }]} keyboardShouldPersistTaps="handled">
      <View style={[s.header, { backgroundColor: C.card, borderBottomColor: C.cardBorder }]}>
        <Text style={[s.titulo, { color: C.text }]}>Deflexão</Text>
        <Text style={[s.sub, { color: C.muted }]}>Azimute de saída a partir de entrada e deflexão</Text>
      </View>

      <View style={s.body}>
        <Text style={[s.secao, { color: C.primary }]}>Dados de Entrada</Text>
        <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
          <View style={s.campo}>
            <Text style={[s.label, { color: C.muted }]}>AZIMUTE DE ENTRADA (°)</Text>
            <TextInput
              style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
              value={azEntrada}
              onChangeText={setAzEntrada}
              placeholder="45.000000"
              placeholderTextColor={C.muted}
              keyboardType="numeric"
              returnKeyType="next"
            />
          </View>

          <View style={s.campo}>
            <Text style={[s.label, { color: C.muted }]}>DEFLEXÃO (°)</Text>
            <TextInput
              style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
              value={deflexao}
              onChangeText={setDeflexao}
              placeholder="30.000000"
              placeholderTextColor={C.muted}
              keyboardType="numeric"
              returnKeyType="done"
            />
          </View>

          <View style={s.campo}>
            <Text style={[s.label, { color: C.muted }]}>SENTIDO</Text>
            <View style={[s.toggle, { borderColor: C.cardBorder }]}>
              <TouchableOpacity
                style={[s.toggleBtn, lado === 'D' && { backgroundColor: C.primary }]}
                onPress={() => { setLado('D'); setResultado(null) }}
              >
                <Text style={[s.toggleTxt, { color: lado === 'D' ? C.primaryText : C.muted }]}>Direita (D)</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[s.toggleBtn, lado === 'E' && { backgroundColor: C.primary }]}
                onPress={() => { setLado('E'); setResultado(null) }}
              >
                <Text style={[s.toggleTxt, { color: lado === 'E' ? C.primaryText : C.muted }]}>Esquerda (E)</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>

        <View style={s.btns}>
          <TouchableOpacity style={[s.btnSec, { borderColor: C.cardBorder }]} onPress={limpar}>
            <Text style={[s.btnSecTxt, { color: C.muted }]}>Limpar</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[s.btnPri, { backgroundColor: C.primary }]} onPress={calcular}>
            <Text style={[s.btnPriTxt, { color: C.primaryText }]}>Calcular</Text>
          </TouchableOpacity>
        </View>

        {resultado && (
          <View style={[s.resultado, { backgroundColor: C.card, borderColor: C.primary }]}>
            <Text style={[s.resLabel, { color: C.muted }]}>Azimute de Saída</Text>
            <View style={s.resRow}>
              <View style={s.resItem}>
                <Text style={[s.resValor, { color: C.primary }]}>{resultado.decimal.toFixed(6)}°</Text>
                <Text style={[s.resSub, { color: C.muted }]}>Decimal</Text>
              </View>
              <View style={[s.resDivider, { backgroundColor: C.cardBorder }]} />
              <View style={s.resItem}>
                <Text style={[s.resValor, { color: C.primary }]}>{resultado.dms}</Text>
                <Text style={[s.resSub, { color: C.muted }]}>GMS</Text>
              </View>
            </View>
          </View>
        )}

        <TouchableOpacity
          style={[s.gabarito, { borderColor: C.cardBorder }]}
          onPress={() => {
            setAzEntrada('45.000')
            setDeflexao('30.000')
            setLado('D')
            setResultado(null)
          }}
        >
          <Text style={[s.gabaritoTxt, { color: C.muted }]}>Gabarito: Az=45°, Deflexão D 30° → Saída=75°00'00.000"</Text>
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
  toggle:     { flexDirection: 'row', borderRadius: 8, borderWidth: 0.5, overflow: 'hidden' },
  toggleBtn:  { flex: 1, padding: 12, alignItems: 'center' },
  toggleTxt:  { fontSize: 14, fontWeight: '600' },
  btns:       { flexDirection: 'row', gap: 10, marginTop: 20 },
  btnPri:     { flex: 2, padding: 16, borderRadius: 10, alignItems: 'center', justifyContent: 'center', minHeight: 52 },
  btnPriTxt:  { fontSize: 16, fontWeight: '700' },
  btnSec:     { flex: 1, padding: 16, borderRadius: 10, alignItems: 'center', borderWidth: 0.5, minHeight: 52 },
  btnSecTxt:  { fontSize: 16, fontWeight: '500' },
  resultado:  { marginTop: 20, borderRadius: 12, borderWidth: 1, padding: 20 },
  resLabel:   { fontSize: 10, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 14 },
  resRow:     { flexDirection: 'row', alignItems: 'center' },
  resItem:    { flex: 1, alignItems: 'center' },
  resValor:   { fontSize: 20, fontWeight: '700', fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  resSub:     { fontSize: 14, marginTop: 4 },
  resDivider: { width: 0.5, height: 40, marginHorizontal: 16 },
  gabarito:   { marginTop: 16, borderWidth: 0.5, borderRadius: 8, padding: 12, borderStyle: 'dashed' },
  gabaritoTxt:{ fontSize: 12, textAlign: 'center' },
})
