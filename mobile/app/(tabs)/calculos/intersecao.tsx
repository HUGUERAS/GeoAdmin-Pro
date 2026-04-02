import { useState } from 'react'
import { View, Text, TouchableOpacity, ScrollView, StyleSheet, Alert, ActivityIndicator } from 'react-native'
import { Colors } from '../../../constants/Colors'
import { apiPost } from '../../../lib/api'
import { ScreenHeader } from '../../../components/ScreenHeader'
import { ss } from '@/styles/ss'
import { CampoInput } from '../../../components/CampoInput'

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
      setResultado(await apiPost<Resultado>('/geo/intersecao', {
        p1: { norte: n1, este: e1, azimute: az1 },
        p2: { norte: n2, este: e2, azimute: az2 },
      }))
    } catch (e: any) {
      Alert.alert('Erro', e.message || 'Não foi possível calcular.\nVerifique a conexão com o backend.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <ScrollView style={[ss.container, { backgroundColor: C.background }]} keyboardShouldPersistTaps="handled">
      <ScreenHeader titulo="Interseção" subtitulo="Interseção de duas semiretas por azimute" />

      <View style={ss.body}>
        <Text style={[s.secao, { color: C.primary }]}>Ponto 1</Text>
        <View style={[ss.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
          <CampoInput label="NORTE (m)" value={p1.norte} onChangeText={(v: string) => setP1(p => ({ ...p, norte: v }))} placeholder="7395000.000" />
          <CampoInput label="ESTE (m)" value={p1.este} onChangeText={(v: string) => setP1(p => ({ ...p, este: v }))} placeholder="313500.000" />
          <CampoInput label="AZIMUTE (°)" value={p1.azimute} onChangeText={(v: string) => setP1(p => ({ ...p, azimute: v }))} placeholder="45.000" />
        </View>

        <Text style={[s.secao, { color: C.primary }]}>Ponto 2</Text>
        <View style={[ss.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
          <CampoInput label="NORTE (m)" value={p2.norte} onChangeText={(v: string) => setP2(p => ({ ...p, norte: v }))} placeholder="7395000.000" />
          <CampoInput label="ESTE (m)" value={p2.este} onChangeText={(v: string) => setP2(p => ({ ...p, este: v }))} placeholder="313600.000" />
          <CampoInput label="AZIMUTE (°)" value={p2.azimute} onChangeText={(v: string) => setP2(p => ({ ...p, azimute: v }))} placeholder="315.000" />
        </View>

        <View style={ss.btns}>
          <TouchableOpacity style={[ss.btnSec, { borderColor: C.cardBorder }]} onPress={limpar}>
            <Text style={[ss.btnSecTxt, { color: C.muted }]}>Limpar</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[ss.btnPri, { backgroundColor: C.primary }]} onPress={calcular} disabled={loading}>
            {loading ? <ActivityIndicator color={C.primaryText} /> : <Text style={[ss.btnPriTxt, { color: C.primaryText }]}>Calcular</Text>}
          </TouchableOpacity>
        </View>

        {resultado && (
          <View style={[ss.resultado, { backgroundColor: C.card, borderColor: C.primary }]}>
            <Text style={[ss.resLabel, { color: C.muted }]}>Ponto de Interseção</Text>
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
  secao: { fontSize: 12, fontWeight: '700', marginBottom: 8, marginTop: 16, textTransform: 'uppercase', letterSpacing: 0.5 },
  resRow: { flexDirection: 'row', alignItems: 'center' },
  resItem: { flex: 1, alignItems: 'center' },
  resSub: { fontSize: 14, marginTop: 4 },
  resDivider: { width: 0.5, height: 40, marginHorizontal: 16 },
  gabarito: { marginTop: 16, borderWidth: 0.5, borderRadius: 8, padding: 12, borderStyle: 'dashed' },
  gabaritoTxt: { fontSize: 12, textAlign: 'center' },
})
