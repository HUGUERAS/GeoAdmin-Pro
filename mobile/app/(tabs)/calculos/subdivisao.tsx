import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, ScrollView, StyleSheet, Alert, ActivityIndicator, Platform } from 'react-native'
import { Colors } from '../../../constants/Colors'
import { apiPost } from '../../../lib/api'
import { ScreenHeader } from '../../../components/ScreenHeader'

type VertexLinha = { norte: string; este: string }
type Resultado = {
  ponto_corte: { norte: number; este: number }
  aresta_inicio: number
  aresta_fim: number
  area_parte1_m2: number
  area_parte2_m2: number
  area_total_m2: number
}

const VAZIO: VertexLinha = { norte: '', este: '' }

export default function SubdivisaoScreen() {
  const C = Colors.dark
  const [vertices, setVertices] = useState<VertexLinha[]>([VAZIO, VAZIO, VAZIO, VAZIO])
  const [areaAlvo, setAreaAlvo] = useState('')
  const [resultado, setResultado] = useState<Resultado | null>(null)
  const [loading, setLoading] = useState(false)

  const adicionarVertice = () => setVertices(v => [...v, VAZIO])
  const removerVertice = () => {
    if (vertices.length <= 3) { Alert.alert('Mínimo', 'São necessários pelo menos 3 vértices.'); return }
    setVertices(v => v.slice(0, -1))
    setResultado(null)
  }

  const atualizarVertice = (idx: number, campo: keyof VertexLinha, valor: string) => {
    setVertices(v => v.map((vt, i) => i === idx ? { ...vt, [campo]: valor } : vt))
  }

  const limpar = () => {
    setVertices([VAZIO, VAZIO, VAZIO, VAZIO])
    setAreaAlvo('')
    setResultado(null)
  }

  const calcular = async () => {
    const alvo = parseFloat(areaAlvo)
    if (isNaN(alvo) || alvo <= 0) {
      Alert.alert('Dados incompletos', 'Informe uma área alvo válida (maior que zero).')
      return
    }
    const verts = vertices.map(v => ({ norte: parseFloat(v.norte), este: parseFloat(v.este) }))
    if (verts.some(v => isNaN(v.norte) || isNaN(v.este))) {
      Alert.alert('Dados incompletos', 'Preencha Norte e Este de todos os vértices.')
      return
    }
    setLoading(true)
    setResultado(null)
    try {
      setResultado(await apiPost<Resultado>('/geo/subdivisao', { vertices: verts, area_alvo_m2: alvo }))
    } catch (e: any) {
      Alert.alert('Erro', e.message || 'Não foi possível calcular.\nVerifique a conexão com o backend.')
    } finally {
      setLoading(false)
    }
  }

  const formatarArea = (m2: number) =>
    m2.toLocaleString('pt-BR', { minimumFractionDigits: 4, maximumFractionDigits: 4 })

  return (
    <ScrollView style={[s.container, { backgroundColor: C.background }]} keyboardShouldPersistTaps="handled">
      <ScreenHeader titulo="Subdivisão" subtitulo="Divisão de polígono por área alvo (bisseção)" />

      <View style={s.body}>
        <Text style={[s.secao, { color: C.primary }]}>Área Alvo</Text>
        <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
          <View style={s.campo}>
            <Text style={[s.label, { color: C.muted }]}>ÁREA ALVO (m²)</Text>
            <TextInput
              style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
              value={areaAlvo}
              onChangeText={v => { setAreaAlvo(v); setResultado(null) }}
              placeholder="10000.0000"
              placeholderTextColor={C.muted}
              keyboardType="numeric"
              returnKeyType="done"
            />
          </View>
        </View>

        <Text style={[s.secao, { color: C.primary }]}>Vértices (sentido anti-horário)</Text>

        {vertices.map((vt, idx) => (
          <View key={idx} style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
            <Text style={[s.pontoLabel, { color: C.primary }]}>V{idx + 1}</Text>
            <View style={s.campoRow}>
              <View style={s.campoHalf}>
                <Text style={[s.label, { color: C.muted }]}>NORTE (m)</Text>
                <TextInput
                  style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
                  value={vt.norte}
                  onChangeText={v => atualizarVertice(idx, 'norte', v)}
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
                  value={vt.este}
                  onChangeText={v => atualizarVertice(idx, 'este', v)}
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
          <TouchableOpacity style={[s.btnPonto, { borderColor: C.primary }]} onPress={adicionarVertice}>
            <Text style={[s.btnPontoTxt, { color: C.primary }]}>+ Vértice</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[s.btnPonto, { borderColor: C.cardBorder }]} onPress={removerVertice}>
            <Text style={[s.btnPontoTxt, { color: C.muted }]}>– Vértice</Text>
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
            <Text style={[s.resLabel, { color: C.muted }]}>Resultado da Subdivisão</Text>

            <Text style={[s.arestaTxt, { color: C.muted }]}>
              Linha de corte: Aresta V{resultado.aresta_inicio + 1} → V{resultado.aresta_fim + 1}
            </Text>

            <View style={[s.corteBox, { borderColor: C.primary }]}>
              <Text style={[s.corteLbl, { color: C.muted }]}>Ponto de corte</Text>
              <Text style={[s.corteVal, { color: C.primary }]}>N {resultado.ponto_corte.norte.toFixed(3)}</Text>
              <Text style={[s.corteVal, { color: C.primary }]}>E {resultado.ponto_corte.este.toFixed(3)}</Text>
            </View>

            <View style={[s.sepH, { backgroundColor: C.cardBorder }]} />

            <View style={s.resRow}>
              <View style={s.resItem}>
                <Text style={[s.resValorSm, { color: C.primary }]}>{formatarArea(resultado.area_parte1_m2)} m²</Text>
                <Text style={[s.resSub, { color: C.muted }]}>Parte 1</Text>
              </View>
              <View style={[s.resDivider, { backgroundColor: C.cardBorder }]} />
              <View style={s.resItem}>
                <Text style={[s.resValorSm, { color: C.text }]}>{formatarArea(resultado.area_parte2_m2)} m²</Text>
                <Text style={[s.resSub, { color: C.muted }]}>Parte 2</Text>
              </View>
            </View>

            <Text style={[s.totalTxt, { color: C.muted }]}>
              Área total: {formatarArea(resultado.area_total_m2)} m²
            </Text>
          </View>
        )}

        <TouchableOpacity
          style={[s.gabarito, { borderColor: C.cardBorder }]}
          onPress={() => {
            setVertices([
              { norte: '7395000', este: '313500' },
              { norte: '7395200', este: '313500' },
              { norte: '7395200', este: '313600' },
              { norte: '7395000', este: '313600' },
            ])
            setAreaAlvo('10000')
            setResultado(null)
          }}
        >
          <Text style={[s.gabaritoTxt, { color: C.muted }]}>Gabarito: retângulo 200×100m (20.000 m²), dividir em 10.000 m²</Text>
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
  campo: { marginBottom: 4 },
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
  resLabel: { fontSize: 10, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8 },
  arestaTxt: { fontSize: 12, marginBottom: 12 },
  corteBox: { borderRadius: 8, borderWidth: 0.5, padding: 12, marginBottom: 6, alignItems: 'center' },
  corteLbl: { fontSize: 10, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.3, marginBottom: 6 },
  corteVal: { fontSize: 18, fontWeight: '700', fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  sepH: { height: 0.5, marginVertical: 14 },
  resRow: { flexDirection: 'row', alignItems: 'center' },
  resItem: { flex: 1, alignItems: 'center' },
  resValorSm: { fontSize: 15, fontWeight: '700', fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier', textAlign: 'center' },
  resSub: { fontSize: 12, marginTop: 4 },
  resDivider: { width: 0.5, height: 40, marginHorizontal: 16 },
  totalTxt: { fontSize: 11, textAlign: 'center', marginTop: 14 },
  gabarito: { marginTop: 16, borderWidth: 0.5, borderRadius: 8, padding: 12, borderStyle: 'dashed' },
  gabaritoTxt: { fontSize: 12, textAlign: 'center' },
})
