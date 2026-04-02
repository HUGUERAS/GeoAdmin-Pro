import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, ScrollView, StyleSheet, Alert, ActivityIndicator, Platform } from 'react-native'
import { Colors } from '../../../constants/Colors'
import { apiPost } from '../../../lib/api'
import { ScreenHeader } from '../../../components/ScreenHeader'

type PontoLinha = { norte: string; este: string }
type Resultado = { area_m2: number; area_ha: number; perimetro_m: number }

const PONTO_VAZIO: PontoLinha = { norte: '', este: '' }

export default function AreaScreen() {
  const C = Colors.dark
  const [pontos, setPontos] = useState<PontoLinha[]>([PONTO_VAZIO, PONTO_VAZIO, PONTO_VAZIO])
  const [resultado, setResultado] = useState<Resultado | null>(null)
  const [loading, setLoading] = useState(false)

  const adicionarPonto = () => setPontos(p => [...p, PONTO_VAZIO])
  const removerPonto = () => {
    if (pontos.length <= 3) { Alert.alert('Mínimo', 'São necessários pelo menos 3 pontos.'); return }
    setPontos(p => p.slice(0, -1))
    setResultado(null)
  }

  const atualizarPonto = (idx: number, campo: keyof PontoLinha, valor: string) => {
    setPontos(p => p.map((pt, i) => i === idx ? { ...pt, [campo]: valor } : pt))
  }

  const limpar = () => {
    setPontos([PONTO_VAZIO, PONTO_VAZIO, PONTO_VAZIO])
    setResultado(null)
  }

  const calcular = async () => {
    const parsed = pontos.map(p => ({ norte: parseFloat(p.norte), este: parseFloat(p.este) }))
    if (parsed.some(p => isNaN(p.norte) || isNaN(p.este))) {
      Alert.alert('Dados incompletos', 'Preencha Norte e Este de todos os pontos.')
      return
    }
    setLoading(true)
    setResultado(null)
    try {
      setResultado(await apiPost<Resultado>('/geo/area', { pontos: parsed }))
    } catch (e: any) {
      Alert.alert('Erro', e.message || 'Não foi possível calcular.\nVerifique a conexão com o backend.')
    } finally {
      setLoading(false)
    }
  }

  const formatarNumero = (n: number, casas: number) =>
    n.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas })

  return (
    <ScrollView style={[s.container, { backgroundColor: C.background }]} keyboardShouldPersistTaps="handled">
      <ScreenHeader titulo="Área" subtitulo="Área e perímetro de polígono UTM" />

      <View style={s.body}>
        <Text style={[s.secao, { color: C.primary }]}>Vértices do Polígono</Text>

        {pontos.map((pt, idx) => (
          <View key={idx} style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
            <Text style={[s.pontoLabel, { color: C.primary }]}>P{idx + 1}</Text>
            <View style={s.campoRow}>
              <View style={s.campoHalf}>
                <Text style={[s.label, { color: C.muted }]}>NORTE (m)</Text>
                <TextInput
                  style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
                  value={pt.norte}
                  onChangeText={v => atualizarPonto(idx, 'norte', v)}
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
                  value={pt.este}
                  onChangeText={v => atualizarPonto(idx, 'este', v)}
                  placeholder="313500.000"
                  placeholderTextColor={C.muted}
                  keyboardType="numeric"
                  returnKeyType="next"
                />
              </View>
            </View>
          </View>
        ))}

        <View style={s.btnsPonto}>
          <TouchableOpacity style={[s.btnPonto, { borderColor: C.primary }]} onPress={adicionarPonto}>
            <Text style={[s.btnPontoTxt, { color: C.primary }]}>+ Ponto</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[s.btnPonto, { borderColor: C.cardBorder }]} onPress={removerPonto}>
            <Text style={[s.btnPontoTxt, { color: C.muted }]}>– Ponto</Text>
          </TouchableOpacity>
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
            <Text style={[s.resLabel, { color: C.muted }]}>Resultado</Text>
            <View style={s.resRow}>
              <View style={s.resItem}>
                <Text style={[s.resValor, { color: C.primary }]}>{formatarNumero(resultado.area_m2, 4)} m²</Text>
                <Text style={[s.resSub, { color: C.muted }]}>Área</Text>
              </View>
            </View>
            <View style={[s.resDivider, { backgroundColor: C.cardBorder }]} />
            <View style={s.resRow}>
              <View style={s.resItem}>
                <Text style={[s.resValorSm, { color: C.text }]}>{formatarNumero(resultado.area_ha, 6)} ha</Text>
                <Text style={[s.resSub, { color: C.muted }]}>Área em hectares</Text>
              </View>
              <View style={[s.resDividerV, { backgroundColor: C.cardBorder }]} />
              <View style={s.resItem}>
                <Text style={[s.resValorSm, { color: C.text }]}>{formatarNumero(resultado.perimetro_m, 4)} m</Text>
                <Text style={[s.resSub, { color: C.muted }]}>Perímetro</Text>
              </View>
            </View>
          </View>
        )}

        <TouchableOpacity
          style={[s.gabarito, { borderColor: C.cardBorder }]}
          onPress={() => {
            setPontos([
              { norte: '7395000', este: '313500' },
              { norte: '7395000', este: '313600' },
              { norte: '7395100', este: '313600' },
              { norte: '7395100', este: '313500' },
            ])
            setResultado(null)
          }}
        >
          <Text style={[s.gabaritoTxt, { color: C.muted }]}>Carregar gabarito (quadrado 100m × 100m = 10.000 m²)</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  )
}

const s = StyleSheet.create({
  container: { flex: 1 },
  header: { padding: 20, borderBottomWidth: 0.5 },
  titulo: { fontSize: 24, fontWeight: '700' },
  sub: { fontSize: 13, marginTop: 2 },
  body: { padding: 16 },
  secao: { fontSize: 12, fontWeight: '700', marginBottom: 8, marginTop: 16, textTransform: 'uppercase', letterSpacing: 0.5 },
  card: { borderRadius: 10, borderWidth: 0.5, padding: 14, marginBottom: 8 },
  pontoLabel: { fontSize: 11, fontWeight: '700', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 },
  campoRow: { flexDirection: 'row', gap: 10 },
  campoHalf: { flex: 1 },
  label: { fontSize: 10, fontWeight: '600', marginBottom: 5, textTransform: 'uppercase', letterSpacing: 0.3 },
  input: { borderWidth: 0.5, borderRadius: 8, padding: 12, fontSize: 15, fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  btnsPonto: { flexDirection: 'row', gap: 10, marginTop: 4, marginBottom: 4 },
  btnPonto: { flex: 1, padding: 10, borderRadius: 8, alignItems: 'center', borderWidth: 0.5 },
  btnPontoTxt: { fontSize: 14, fontWeight: '600' },
  btns: { flexDirection: 'row', gap: 10, marginTop: 16 },
  btnPri: { flex: 2, padding: 16, borderRadius: 10, alignItems: 'center', justifyContent: 'center', minHeight: 52 },
  btnPriTxt: { fontSize: 16, fontWeight: '700' },
  btnSec: { flex: 1, padding: 16, borderRadius: 10, alignItems: 'center', borderWidth: 0.5, minHeight: 52 },
  btnSecTxt: { fontSize: 16, fontWeight: '500' },
  resultado: { marginTop: 20, borderRadius: 12, borderWidth: 1, padding: 20 },
  resLabel: { fontSize: 10, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 14 },
  resRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center' },
  resItem: { flex: 1, alignItems: 'center' },
  resValor: { fontSize: 20, fontWeight: '700', fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  resValorSm: { fontSize: 16, fontWeight: '700', fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  resSub: { fontSize: 12, marginTop: 4 },
  resDivider: { height: 0.5, marginVertical: 14 },
  resDividerV: { width: 0.5, height: 40, marginHorizontal: 10 },
  gabarito: { marginTop: 16, borderWidth: 0.5, borderRadius: 8, padding: 12, borderStyle: 'dashed' },
  gabaritoTxt: { fontSize: 12, textAlign: 'center' },
})
