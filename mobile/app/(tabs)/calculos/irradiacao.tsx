import { useState } from 'react'
import { View, Text, TouchableOpacity, ScrollView, StyleSheet, Alert } from 'react-native'
import { Colors } from '../../../constants/Colors'
import { ScreenHeader } from '../../../components/ScreenHeader'
import { ss } from '@/styles/ss'
import { CampoInput } from '../../../components/CampoInput'

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
    const este = e + dist * Math.sin(azRad)
    setResultado({ norte, este })
  }

  return (
    <ScrollView style={[ss.container, { backgroundColor: C.background }]} keyboardShouldPersistTaps="handled">
      <ScreenHeader titulo="Irradiação" subtitulo="Coordenadas de ponto irradiado por azimute e distância" />

      <View style={ss.body}>
        <Text style={[s.secao, { color: C.primary }]}>Estação</Text>
        <View style={[ss.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
          <CampoInput label="NORTE (m)" value={estN} onChangeText={setEstN} placeholder="7395000.000" />
          <CampoInput label="ESTE (m)" value={estE} onChangeText={setEstE} placeholder="313500.000" />
        </View>

        <Text style={[s.secao, { color: C.primary }]}>Direção e Distância</Text>
        <View style={[ss.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
          <CampoInput label="AZIMUTE (°)" value={azimute} onChangeText={setAzimute} placeholder="45.000000" />
          <CampoInput label="DISTÂNCIA (m)" value={distancia} onChangeText={setDistancia} placeholder="141.421356" />
        </View>

        <View style={ss.btns}>
          <TouchableOpacity style={[ss.btnSec, { borderColor: C.cardBorder }]} onPress={limpar}>
            <Text style={[ss.btnSecTxt, { color: C.muted }]}>Limpar</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[ss.btnPri, { backgroundColor: C.primary }]} onPress={calcular}>
            <Text style={[ss.btnPriTxt, { color: C.primaryText }]}>Calcular</Text>
          </TouchableOpacity>
        </View>

        {resultado && (
          <View style={[ss.resultado, { backgroundColor: C.card, borderColor: C.primary }]}>
            <Text style={[ss.resLabel, { color: C.muted }]}>Ponto Irradiado</Text>
            <View style={s.resRow}>
              <View style={s.resItem}>
                <Text style={[ss.resValor, { color: C.primary }]}>{resultado.norte.toFixed(3)}</Text>
                <Text style={[s.resSub, { color: C.muted }]}>Norte (m)</Text>
              </View>
              <View style={[s.resDivider, { backgroundColor: C.cardBorder }]} />
              <View style={s.resItem}>
                <Text style={[ss.resValor, { color: C.primary }]}>{resultado.este.toFixed(3)}</Text>
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
  secao: { fontSize: 12, fontWeight: '700', marginBottom: 8, marginTop: 16, textTransform: 'uppercase', letterSpacing: 0.5 },
  resRow: { flexDirection: 'row', alignItems: 'center' },
  resItem: { flex: 1, alignItems: 'center' },
  resSub: { fontSize: 14, marginTop: 4 },
  resDivider: { width: 0.5, height: 40, marginHorizontal: 16 },
  gabarito: { marginTop: 16, borderWidth: 0.5, borderRadius: 8, padding: 12, borderStyle: 'dashed' },
  gabaritoTxt: { fontSize: 12, textAlign: 'center' },
})
