import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, ScrollView, StyleSheet, Alert, ActivityIndicator, Platform, Switch } from 'react-native'
import { Colors } from '../../../constants/Colors'
import { apiPost } from '../../../lib/api'
import { ScreenHeader } from '../../../components/ScreenHeader'

type PontoLinha = { norte: string; este: string }
type PontoResultado = { norte: number; este: number }
type Resultado = { pontos: PontoResultado[]; origem: { norte: number; este: number } }

const PONTO_VAZIO: PontoLinha = { norte: '', este: '' }

export default function RotacaoScreen() {
  const C = Colors.dark
  const [pontos, setPontos] = useState<PontoLinha[]>([PONTO_VAZIO, PONTO_VAZIO])
  const [angulo, setAngulo] = useState('')
  const [usarOrigem, setUsarOrigem] = useState(false)
  const [origem, setOrigem] = useState<PontoLinha>(PONTO_VAZIO)
  const [resultado, setResultado] = useState<Resultado | null>(null)
  const [loading, setLoading] = useState(false)

  const adicionarPonto = () => setPontos(p => [...p, PONTO_VAZIO])
  const removerPonto = () => {
    if (pontos.length <= 1) { Alert.alert('Mínimo', 'É necessário pelo menos 1 ponto.'); return }
    setPontos(p => p.slice(0, -1))
    setResultado(null)
  }

  const atualizarPonto = (idx: number, campo: keyof PontoLinha, valor: string) => {
    setPontos(p => p.map((pt, i) => i === idx ? { ...pt, [campo]: valor } : pt))
  }

  const limpar = () => {
    setPontos([PONTO_VAZIO, PONTO_VAZIO])
    setAngulo('')
    setUsarOrigem(false)
    setOrigem(PONTO_VAZIO)
    setResultado(null)
  }

  const calcular = async () => {
    const ang = parseFloat(angulo)
    if (isNaN(ang)) {
      Alert.alert('Dados incompletos', 'Informe o ângulo de rotação.')
      return
    }
    const pontosValidos = pontos.map(p => ({ norte: parseFloat(p.norte), este: parseFloat(p.este) }))
    if (pontosValidos.some(p => isNaN(p.norte) || isNaN(p.este))) {
      Alert.alert('Dados incompletos', 'Preencha Norte e Este de todos os pontos.')
      return
    }
    const body: Record<string, unknown> = { pontos: pontosValidos, angulo_graus: ang }
    if (usarOrigem) {
      const oN = parseFloat(origem.norte), oE = parseFloat(origem.este)
      if (isNaN(oN) || isNaN(oE)) {
        Alert.alert('Dados incompletos', 'Informe a origem de rotação ou desative a opção.')
        return
      }
      body.origem = { norte: oN, este: oE }
    }
    setLoading(true)
    setResultado(null)
    try {
      setResultado(await apiPost<Resultado>('/geo/rotacao', body))
    } catch (e: any) {
      Alert.alert('Erro', e.message || 'Não foi possível calcular.\nVerifique a conexão com o backend.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <ScrollView style={[s.container, { backgroundColor: C.background }]} keyboardShouldPersistTaps="handled">
      <ScreenHeader titulo="Rotação" subtitulo="Rotação de pontos UTM em torno de uma origem" />

      <View style={s.body}>
        <Text style={[s.secao, { color: C.primary }]}>Ângulo de Rotação</Text>
        <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
          <View style={s.campo}>
            <Text style={[s.label, { color: C.muted }]}>ÂNGULO (°) — positivo = anti-horário</Text>
            <TextInput
              style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
              value={angulo}
              onChangeText={v => { setAngulo(v); setResultado(null) }}
              placeholder="90.000"
              placeholderTextColor={C.muted}
              keyboardType="numeric"
              returnKeyType="done"
            />
          </View>
          <View style={s.origemRow}>
            <Text style={[s.label, { color: C.muted, flex: 1, marginBottom: 0 }]}>USAR ORIGEM PERSONALIZADA</Text>
            <Switch
              value={usarOrigem}
              onValueChange={v => { setUsarOrigem(v); setResultado(null) }}
              trackColor={{ true: C.primary, false: C.cardBorder }}
              thumbColor={C.text}
            />
          </View>
          {usarOrigem && (
            <View style={[s.campoRow, { marginTop: 12 }]}>
              <View style={s.campoHalf}>
                <Text style={[s.label, { color: C.muted }]}>ORIGEM NORTE (m)</Text>
                <TextInput
                  style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
                  value={origem.norte}
                  onChangeText={v => setOrigem(o => ({ ...o, norte: v }))}
                  placeholder="7395000.000"
                  placeholderTextColor={C.muted}
                  keyboardType="numeric"
                  returnKeyType="next"
                />
              </View>
              <View style={s.campoHalf}>
                <Text style={[s.label, { color: C.muted }]}>ORIGEM ESTE (m)</Text>
                <TextInput
                  style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
                  value={origem.este}
                  onChangeText={v => setOrigem(o => ({ ...o, este: v }))}
                  placeholder="313500.000"
                  placeholderTextColor={C.muted}
                  keyboardType="numeric"
                  returnKeyType="next"
                />
              </View>
            </View>
          )}
        </View>

        <Text style={[s.secao, { color: C.primary }]}>Pontos a Rotacionar</Text>

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
            <Text style={[s.resLabel, { color: C.muted }]}>Pontos Rotacionados</Text>
            <Text style={[s.origemInfo, { color: C.muted }]}>
              Origem: N={resultado.origem.norte.toFixed(3)}, E={resultado.origem.este.toFixed(3)}
            </Text>
            {resultado.pontos.map((p, idx) => (
              <View key={idx} style={[s.tabelaLinha, { borderTopColor: C.cardBorder }]}>
                <Text style={[s.tabelaIdx, { color: C.muted }]}>P{idx + 1}</Text>
                <View style={s.tabelaVals}>
                  <Text style={[s.tabelaVal, { color: C.text }]}>N {p.norte.toFixed(3)}</Text>
                  <Text style={[s.tabelaVal, { color: C.text }]}>E {p.este.toFixed(3)}</Text>
                </View>
              </View>
            ))}
          </View>
        )}

        <TouchableOpacity
          style={[s.gabarito, { borderColor: C.cardBorder }]}
          onPress={() => {
            setPontos([
              { norte: '7395100', este: '313500' },
              { norte: '7395000', este: '313500' },
            ])
            setAngulo('90')
            setUsarOrigem(false)
            setOrigem(PONTO_VAZIO)
            setResultado(null)
          }}
        >
          <Text style={[s.gabaritoTxt, { color: C.muted }]}>Gabarito: 2 pontos, ângulo 90°, centróide como origem</Text>
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
  campo: { marginBottom: 12 },
  campoRow: { flexDirection: 'row', gap: 10 },
  campoHalf: { flex: 1 },
  origemRow: { flexDirection: 'row', alignItems: 'center', marginTop: 4 },
  pontoLabel: { fontSize: 11, fontWeight: '700', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 },
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
  resLabel: { fontSize: 10, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 },
  origemInfo: { fontSize: 11, marginBottom: 14 },
  tabelaLinha: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, borderTopWidth: 0.5 },
  tabelaIdx: { fontSize: 12, fontWeight: '700', width: 30 },
  tabelaVals: { flex: 1, flexDirection: 'row', justifyContent: 'space-between' },
  tabelaVal: { fontSize: 14, fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  gabarito: { marginTop: 16, borderWidth: 0.5, borderRadius: 8, padding: 12, borderStyle: 'dashed' },
  gabaritoTxt: { fontSize: 12, textAlign: 'center' },
})
