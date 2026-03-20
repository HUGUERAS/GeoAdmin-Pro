import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, ScrollView, StyleSheet, Alert, Platform } from 'react-native'
import { Colors } from '../../../constants/Colors'

type Resultado = { norte: number; este: number }

export default function IrradiacaoScreen() {
  const C = Colors.dark
  const [estN, setEstN] = useState('')
  const [estE, setEstE] = useState('')
  const [azimute, setAzimute] = useState('')
  const [distancia, setDistancia] = useState('')
  const [resultado, setResultado] = useState<Resultado | null>(null)

  const limpar = () => {
    setEstN(''); setEstE(''); setAzimute(''); setDistancia(''); setResultado(null)
  }

  const calcular = () => {
    const n = parseFloat(estN)
    const e = parseFloat(estE)
    const az = parseFloat(azimute)
    const dist = parseFloat(distancia)
    if ([n, e, az, dist].some(isNaN)) {
      Alert.alert('Dados incompletos', 'Preencha todos os campos: Norte, Este, Azimute e Distância.')
      return
    }
    if (dist <= 0) {
      Alert.alert('Dados inválidos', 'A distância deve ser maior que zero.')
      return
    }
    const azRad = (az * Math.PI) / 180
    const norte = n + dist * Math.cos(azRad)
    const este  = e + dist * Math.sin(azRad)
    setResultado({ norte, este })
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
        <Text style={[s.titulo, { color: C.text }]}>Irradiação</Text>
        <Text style={[s.sub, { color: C.muted }]}>Coordenadas de ponto irradiado por azimute e distância</Text>
      </View>

      <View style={s.body}>
        <Text style={[s.secao, { color: C.primary }]}>Estação</Text>
        <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
          <Campo label="NORTE (m)" value={estN} onChange={setEstN} placeholder="7395000.000" />
          <Campo label="ESTE (m)"  value={estE} onChange={setEstE} placeholder="313500.000" />
        </View>

        <Text style={[s.secao, { color: C.primary }]}>Direção e Distância</Text>
        <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
          <Campo label="AZIMUTE (°)"    value={azimute}   onChange={setAzimute}   placeholder="45.000000" />
          <Campo label="DISTÂNCIA (m)"  value={distancia} onChange={setDistancia} placeholder="141.421356" />
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
            <Text style={[s.resLabel, { color: C.muted }]}>Ponto Irradiado</Text>
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
            setEstN('7395000')
            setEstE('313500')
            setAzimute('45.000')
            setDistancia('141.421')
            setResultado(null)
          }}
        >
          <Text style={[s.gabaritoTxt, { color: C.muted }]}>Gabarito: Est(7395000, 313500), Az=45°, Dist=141.421m → P≈(7395100, 313600)</Text>
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
