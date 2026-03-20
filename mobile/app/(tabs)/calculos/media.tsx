import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, ScrollView, StyleSheet, Alert, Platform } from 'react-native'
import { Colors } from '../../../constants/Colors'

type PontoLinha = { norte: string; este: string; cota: string }

const PONTO_VAZIO: PontoLinha = { norte: '', este: '', cota: '' }

type Resultado = {
  mediaNorte: number
  mediaEste: number
  dpNorte: number
  dpEste: number
  mediaCota?: number
  n: number
}

export default function MediaScreen() {
  const C = Colors.dark
  const [pontos, setPontos] = useState<PontoLinha[]>([PONTO_VAZIO, PONTO_VAZIO, PONTO_VAZIO])
  const [resultado, setResultado] = useState<Resultado | null>(null)

  const adicionarPonto = () => setPontos(p => [...p, PONTO_VAZIO])
  const removerPonto = () => {
    if (pontos.length <= 2) { Alert.alert('Mínimo', 'São necessárias pelo menos 2 medições.'); return }
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

  const calcular = () => {
    const vals = pontos.filter(p => p.norte && p.este && !isNaN(parseFloat(p.norte)) && !isNaN(parseFloat(p.este)))
    if (vals.length < 2) {
      Alert.alert('Dados insuficientes', 'Preencha Norte e Este de pelo menos 2 pontos.')
      return
    }
    const n = vals.length
    const mNorte = vals.reduce((s, p) => s + parseFloat(p.norte), 0) / n
    const mEste  = vals.reduce((s, p) => s + parseFloat(p.este), 0) / n
    const dpN = Math.sqrt(vals.reduce((s, p) => s + (parseFloat(p.norte) - mNorte) ** 2, 0) / Math.max(n - 1, 1))
    const dpE = Math.sqrt(vals.reduce((s, p) => s + (parseFloat(p.este) - mEste) ** 2, 0) / Math.max(n - 1, 1))

    const valsComCota = vals.filter(p => p.cota && !isNaN(parseFloat(p.cota)))
    const mediaCota = valsComCota.length > 0
      ? valsComCota.reduce((s, p) => s + parseFloat(p.cota), 0) / valsComCota.length
      : undefined

    setResultado({ mediaNorte: mNorte, mediaEste: mEste, dpNorte: dpN, dpEste: dpE, mediaCota, n })
  }

  return (
    <ScrollView style={[s.container, { backgroundColor: C.background }]} keyboardShouldPersistTaps="handled">
      <View style={[s.header, { backgroundColor: C.card, borderBottomColor: C.cardBorder }]}>
        <Text style={[s.titulo, { color: C.text }]}>Média de Pontos</Text>
        <Text style={[s.sub, { color: C.muted }]}>Média e desvio-padrão de medições repetidas</Text>
      </View>

      <View style={s.body}>
        <Text style={[s.secao, { color: C.primary }]}>Medições</Text>

        {pontos.map((pt, idx) => (
          <View key={idx} style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
            <Text style={[s.pontoLabel, { color: C.primary }]}>Medição {idx + 1}</Text>
            <View style={s.tresCol}>
              <View style={s.col}>
                <Text style={[s.label, { color: C.muted }]}>NORTE (m)</Text>
                <TextInput
                  style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
                  value={pt.norte}
                  onChangeText={v => atualizarPonto(idx, 'norte', v)}
                  placeholder="7395001.003"
                  placeholderTextColor={C.muted}
                  keyboardType="numeric"
                  returnKeyType="next"
                />
              </View>
              <View style={s.col}>
                <Text style={[s.label, { color: C.muted }]}>ESTE (m)</Text>
                <TextInput
                  style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
                  value={pt.este}
                  onChangeText={v => atualizarPonto(idx, 'este', v)}
                  placeholder="313500.512"
                  placeholderTextColor={C.muted}
                  keyboardType="numeric"
                  returnKeyType="next"
                />
              </View>
              <View style={s.col}>
                <Text style={[s.label, { color: C.muted }]}>COTA (m)</Text>
                <TextInput
                  style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
                  value={pt.cota}
                  onChangeText={v => atualizarPonto(idx, 'cota', v)}
                  placeholder="opcional"
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
            <Text style={[s.btnPontoTxt, { color: C.primary }]}>+ Medição</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[s.btnPonto, { borderColor: C.cardBorder }]} onPress={removerPonto}>
            <Text style={[s.btnPontoTxt, { color: C.muted }]}>– Medição</Text>
          </TouchableOpacity>
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
            <Text style={[s.resLabel, { color: C.muted }]}>Resultado ({resultado.n} medições)</Text>

            <View style={s.resRow}>
              <View style={s.resItem}>
                <Text style={[s.resValor, { color: C.primary }]}>{resultado.mediaNorte.toFixed(3)}</Text>
                <Text style={[s.resSub, { color: C.muted }]}>Média Norte (m)</Text>
              </View>
              <View style={[s.resDivider, { backgroundColor: C.cardBorder }]} />
              <View style={s.resItem}>
                <Text style={[s.resValor, { color: C.primary }]}>{resultado.mediaEste.toFixed(3)}</Text>
                <Text style={[s.resSub, { color: C.muted }]}>Média Este (m)</Text>
              </View>
            </View>

            <View style={[s.sepH, { backgroundColor: C.cardBorder }]} />

            <View style={s.resRow}>
              <View style={s.resItem}>
                <Text style={[s.resValorSm, { color: C.text }]}>±{resultado.dpNorte.toFixed(4)}</Text>
                <Text style={[s.resSub, { color: C.muted }]}>DP Norte (m)</Text>
              </View>
              <View style={[s.resDivider, { backgroundColor: C.cardBorder }]} />
              <View style={s.resItem}>
                <Text style={[s.resValorSm, { color: C.text }]}>±{resultado.dpEste.toFixed(4)}</Text>
                <Text style={[s.resSub, { color: C.muted }]}>DP Este (m)</Text>
              </View>
            </View>

            {resultado.mediaCota !== undefined && (
              <>
                <View style={[s.sepH, { backgroundColor: C.cardBorder }]} />
                <View style={s.resRow}>
                  <View style={s.resItem}>
                    <Text style={[s.resValorSm, { color: C.text }]}>{resultado.mediaCota.toFixed(3)}</Text>
                    <Text style={[s.resSub, { color: C.muted }]}>Média Cota (m)</Text>
                  </View>
                </View>
              </>
            )}
          </View>
        )}

        <TouchableOpacity
          style={[s.gabarito, { borderColor: C.cardBorder }]}
          onPress={() => {
            setPontos([
              { norte: '7395001.003', este: '313500.512', cota: '' },
              { norte: '7395001.015', este: '313500.497', cota: '' },
              { norte: '7395000.998', este: '313500.523', cota: '' },
            ])
            setResultado(null)
          }}
        >
          <Text style={[s.gabaritoTxt, { color: C.muted }]}>Gabarito: 3 medições repetidas de um mesmo ponto em campo</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  )
}

const s = StyleSheet.create({
  container:   { flex: 1 },
  header:      { padding: 20, paddingTop: 56, borderBottomWidth: 0.5 },
  titulo:      { fontSize: 24, fontWeight: '700' },
  sub:         { fontSize: 13, marginTop: 2 },
  body:        { padding: 16 },
  secao:       { fontSize: 12, fontWeight: '700', marginBottom: 8, marginTop: 16, textTransform: 'uppercase', letterSpacing: 0.5 },
  card:        { borderRadius: 10, borderWidth: 0.5, padding: 14, marginBottom: 8 },
  pontoLabel:  { fontSize: 11, fontWeight: '700', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 },
  tresCol:     { flexDirection: 'row', gap: 8 },
  col:         { flex: 1 },
  label:       { fontSize: 9, fontWeight: '600', marginBottom: 5, textTransform: 'uppercase', letterSpacing: 0.3 },
  input:       { borderWidth: 0.5, borderRadius: 8, padding: 10, fontSize: 13, fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  btnsPonto:   { flexDirection: 'row', gap: 10, marginTop: 4, marginBottom: 4 },
  btnPonto:    { flex: 1, padding: 10, borderRadius: 8, alignItems: 'center', borderWidth: 0.5 },
  btnPontoTxt: { fontSize: 14, fontWeight: '600' },
  btns:        { flexDirection: 'row', gap: 10, marginTop: 16 },
  btnPri:      { flex: 2, padding: 16, borderRadius: 10, alignItems: 'center', justifyContent: 'center', minHeight: 52 },
  btnPriTxt:   { fontSize: 16, fontWeight: '700' },
  btnSec:      { flex: 1, padding: 16, borderRadius: 10, alignItems: 'center', borderWidth: 0.5, minHeight: 52 },
  btnSecTxt:   { fontSize: 16, fontWeight: '500' },
  resultado:   { marginTop: 20, borderRadius: 12, borderWidth: 1, padding: 20 },
  resLabel:    { fontSize: 10, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 14 },
  resRow:      { flexDirection: 'row', alignItems: 'center' },
  resItem:     { flex: 1, alignItems: 'center' },
  resValor:    { fontSize: 20, fontWeight: '700', fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  resValorSm:  { fontSize: 17, fontWeight: '700', fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  resSub:      { fontSize: 12, marginTop: 4 },
  resDivider:  { width: 0.5, height: 40, marginHorizontal: 16 },
  sepH:        { height: 0.5, marginVertical: 14 },
  gabarito:    { marginTop: 16, borderWidth: 0.5, borderRadius: 8, padding: 12, borderStyle: 'dashed' },
  gabaritoTxt: { fontSize: 12, textAlign: 'center' },
})
