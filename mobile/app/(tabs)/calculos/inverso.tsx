import { useState } from 'react'
import { View, Text, TouchableOpacity, ScrollView, StyleSheet, Alert, ActivityIndicator } from 'react-native'
import { Colors } from '../../../constants/Colors'
import { apiPost } from '../../../lib/api'
import { ScreenHeader } from '../../../components/ScreenHeader'
import { CampoInput } from '../../../components/CampoInput'
import { ss } from '@/styles/ss'

type PontoState = { norte: string; este: string }
type Resultado = {
  distancia_m: number
  azimute_graus: number
  azimute_gms: string
  delta_norte: number
  delta_este: number
}

const VAZIO: PontoState = { norte: '', este: '' }

export default function InversoScreen() {
  const C = Colors.dark
  const [p1, setP1] = useState<PontoState>(VAZIO)
  const [p2, setP2] = useState<PontoState>(VAZIO)
  const [resultado, setResultado] = useState<Resultado | null>(null)
  const [loading, setLoading] = useState(false)

  const limpar = () => { setP1(VAZIO); setP2(VAZIO); setResultado(null) }

  const calcular = async () => {
    const n1 = parseFloat(p1.norte), e1 = parseFloat(p1.este)
    const n2 = parseFloat(p2.norte), e2 = parseFloat(p2.este)
    if ([n1, e1, n2, e2].some(isNaN)) {
      Alert.alert('Dados incompletos', 'Preencha Norte e Este dos dois pontos.')
      return
    }
    setLoading(true)
    setResultado(null)
    try {
      setResultado(await apiPost<Resultado>('/geo/inverso', {
        p1: { norte: n1, este: e1 },
        p2: { norte: n2, este: e2 },
      }))
    } catch (e: any) {
      Alert.alert('Erro', e.message || 'Não foi possível calcular.\nVerifique a conexão com o backend.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <ScrollView style={[ss.container, { backgroundColor: C.background }]} keyboardShouldPersistTaps="handled">
      <ScreenHeader titulo="Inverso" subtitulo="Distância e azimute entre dois pontos UTM" />

      <View style={ss.body}>

        <Text style={[ss.secaoLabel, { color: C.primary }]}>Ponto P1</Text>
        <View style={[ss.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
          <View style={ss.campoRow}>
            <View style={ss.campoHalf}>
              <CampoInput
                label="NORTE (m)"
                value={p1.norte}
                onChangeText={v => setP1(prev => ({ ...prev, norte: v }))}
                placeholder="7395000.000"
              />
            </View>
            <View style={ss.campoHalf}>
              <CampoInput
                label="ESTE (m)"
                value={p1.este}
                onChangeText={v => setP1(prev => ({ ...prev, este: v }))}
                placeholder="313500.000"
              />
            </View>
          </View>
        </View>

        <Text style={[ss.secaoLabel, { color: C.primary }]}>Ponto P2</Text>
        <View style={[ss.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
          <View style={ss.campoRow}>
            <View style={ss.campoHalf}>
              <CampoInput
                label="NORTE (m)"
                value={p2.norte}
                onChangeText={v => setP2(prev => ({ ...prev, norte: v }))}
                placeholder="7395100.000"
              />
            </View>
            <View style={ss.campoHalf}>
              <CampoInput
                label="ESTE (m)"
                value={p2.este}
                onChangeText={v => setP2(prev => ({ ...prev, este: v }))}
                placeholder="313600.000"
              />
            </View>
          </View>
        </View>

        <View style={ss.btns}>
          <TouchableOpacity style={[ss.btnSec, { borderColor: C.cardBorder }]} onPress={limpar}>
            <Text style={[ss.btnSecTxt, { color: C.muted }]}>Limpar</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[ss.btnPri, { backgroundColor: C.primary }]} onPress={calcular} disabled={loading}>
            {loading
              ? <ActivityIndicator color={C.primaryText} />
              : <Text style={[ss.btnPriTxt, { color: C.primaryText }]}>Calcular</Text>}
          </TouchableOpacity>
        </View>

        {resultado && (
          <View style={[ss.resultado, { backgroundColor: C.card, borderColor: C.primary }]}>
            <Text style={[ss.resLabel, { color: C.muted }]}>Resultado</Text>

            <Text style={[ss.resValor, { color: C.primary }]}>{resultado.distancia_m.toFixed(4)} m</Text>
            <Text style={[s.resSub, { color: C.muted }]}>Distância</Text>

            <View style={[s.sep, { backgroundColor: C.cardBorder }]} />

            <View style={ss.resLinha}>
              <Text style={[s.resNome, { color: C.muted }]}>Azimute</Text>
              <View style={s.resValores}>
                <Text style={[s.resGms, { color: C.text }]}>{resultado.azimute_gms}</Text>
                <Text style={[s.resDd, { color: C.muted }]}>{resultado.azimute_graus.toFixed(6)}°</Text>
              </View>
            </View>

            <View style={ss.resLinha}>
              <Text style={[s.resNome, { color: C.muted }]}>ΔNorte</Text>
              <Text style={[s.resNum, { color: C.text }]}>{resultado.delta_norte.toFixed(4)} m</Text>
            </View>

            <View style={[ss.resLinha, s.ultimaLinha]}>
              <Text style={[s.resNome, { color: C.muted }]}>ΔEste</Text>
              <Text style={[s.resNum, { color: C.text }]}>{resultado.delta_este.toFixed(4)} m</Text>
            </View>
          </View>
        )}

        <TouchableOpacity
          style={[s.gabarito, { borderColor: C.cardBorder }]}
          onPress={() => {
            setP1({ norte: '7395000', este: '313500' })
            setP2({ norte: '7395100', este: '313600' })
            setResultado(null)
          }}
        >
          <Text style={[s.gabaritoTxt, { color: C.muted }]}>
            Gabarito: P1(7395000, 313500) → P2(7395100, 313600) ≈ 141,42 m · Az 45°
          </Text>
        </TouchableOpacity>

      </View>
    </ScrollView>
  )
}

const s = StyleSheet.create({
  resSub: { fontSize: 12, marginTop: 2 },
  sep: { height: 0.5, marginVertical: 14 },
  resNome: { fontSize: 12, fontWeight: '600' },
  resValores: { alignItems: 'flex-end' },
  resGms: { fontSize: 17, fontWeight: '700' },
  resDd: { fontSize: 12, marginTop: 2 },
  resNum: { fontSize: 16, fontWeight: '700' },
  ultimaLinha: { borderBottomWidth: 0 },
  gabarito: { marginTop: 8, borderWidth: 0.5, borderRadius: 8, padding: 12, borderStyle: 'dashed' },
  gabaritoTxt: { fontSize: 12, textAlign: 'center' },
})

