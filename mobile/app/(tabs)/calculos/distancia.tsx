import { useState } from 'react'
import { View, Text, TouchableOpacity, ScrollView, StyleSheet, Alert, ActivityIndicator, Platform } from 'react-native'
import { Colors } from '../../../constants/Colors'
import { apiPost } from '../../../lib/api'
import { ScreenHeader } from '../../../components/ScreenHeader'
import { ss } from '@/styles/ss'
import { CampoInput } from '../../../components/CampoInput'

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
      setResultado(await apiPost<Resultado>('/geo/distancia-ponto-linha', {
        ponto: { norte: pN, este: pE },
        linha_a: { norte: aN, este: aE },
        linha_b: { norte: bN, este: bE },
      }))
    } catch (e: any) {
      Alert.alert('Erro', e.message || 'Não foi possível calcular.\nVerifique a conexão com o backend.')
    } finally {
      setLoading(false)
    }
  }

  const CampoRow = ({ titulo, estado, setEstado }: { titulo: string; estado: PontoState; setEstado: (p: PontoState) => void }) => (
    <>
      <Text style={[s.secao, { color: C.primary }]}>{titulo}</Text>
      <View style={[ss.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
        <View style={ss.campoRow}>
          <View style={ss.campoHalf}>
            <CampoInput
              label="NORTE (m)"
              value={estado.norte}
              onChangeText={v => setEstado({ ...estado, norte: v })}
              placeholder="7395000.000"
            />
          </View>
          <View style={ss.campoHalf}>
            <CampoInput
              label="ESTE (m)"
              value={estado.este}
              onChangeText={v => setEstado({ ...estado, este: v })}
              placeholder="313500.000"
            />
          </View>
        </View>
      </View>
    </>
  )

  return (
    <ScrollView style={[ss.container, { backgroundColor: C.background }]} keyboardShouldPersistTaps="handled">
      <ScreenHeader titulo="Dist. Ponto-Linha" subtitulo="Distância perpendicular de ponto a segmento" />

      <View style={ss.body}>
        <CampoRow titulo="Ponto P" estado={ponto} setEstado={setPonto} />
        <CampoRow titulo="Linha — Ponto A" estado={linhaA} setEstado={setLinhaA} />
        <CampoRow titulo="Linha — Ponto B" estado={linhaB} setEstado={setLinhaB} />

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
            <Text style={[ss.resLabel, { color: C.muted }]}>Resultado</Text>
            <View style={s.resRow}>
              <View style={s.resItem}>
                <Text style={[ss.resValor, { color: C.primary }]}>{resultado.distancia_m.toFixed(4)} m</Text>
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
  secao: { fontSize: 12, fontWeight: '700', marginBottom: 8, marginTop: 16, textTransform: 'uppercase', letterSpacing: 0.5 },
  resRow: { flexDirection: 'row', alignItems: 'center' },
  resItem: { flex: 1, alignItems: 'center' },
  resValorSm: { fontSize: 17, fontWeight: '700', fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  resSub: { fontSize: 12, marginTop: 4 },
  resSub2: { fontSize: 10, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.3, marginBottom: 10 },
  resDivider: { width: 0.5, height: 40, marginHorizontal: 16 },
  sepH: { height: 0.5, marginVertical: 14 },
  badge: { marginTop: 14, borderRadius: 6, padding: 8, alignItems: 'center' },
  badgeTxt: { fontSize: 12, fontWeight: '600' },
  gabarito: { marginTop: 16, borderWidth: 0.5, borderRadius: 8, padding: 12, borderStyle: 'dashed' },
  gabaritoTxt: { fontSize: 12, textAlign: 'center' },
})
