import { useState } from 'react'
import { View, Text, TouchableOpacity, ScrollView, StyleSheet, Alert, Platform } from 'react-native'
import { Colors } from '../../../constants/Colors'
import { ScreenHeader } from '../../../components/ScreenHeader'
import { ss } from '@/styles/ss'
import { CampoInput } from '../../../components/CampoInput'

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
    const mEste = vals.reduce((s, p) => s + parseFloat(p.este), 0) / n
    const dpN = Math.sqrt(vals.reduce((s, p) => s + (parseFloat(p.norte) - mNorte) ** 2, 0) / Math.max(n - 1, 1))
    const dpE = Math.sqrt(vals.reduce((s, p) => s + (parseFloat(p.este) - mEste) ** 2, 0) / Math.max(n - 1, 1))

    const valsComCota = vals.filter(p => p.cota && !isNaN(parseFloat(p.cota)))
    const mediaCota = valsComCota.length > 0
      ? valsComCota.reduce((s, p) => s + parseFloat(p.cota), 0) / valsComCota.length
      : undefined

    setResultado({ mediaNorte: mNorte, mediaEste: mEste, dpNorte: dpN, dpEste: dpE, mediaCota, n })
  }

  return (
    <ScrollView style={[ss.container, { backgroundColor: C.background }]} keyboardShouldPersistTaps="handled">
      <ScreenHeader titulo="Média de Pontos" subtitulo="Média e desvio-padrão de medições repetidas" />

      <View style={ss.body}>
        <Text style={[s.secao, { color: C.primary }]}>Medições</Text>

        {pontos.map((pt, idx) => (
          <View key={idx} style={[ss.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
            <Text style={[s.pontoLabel, { color: C.primary }]}>Medição {idx + 1}</Text>
            <View style={s.tresCol}>
              <View style={s.col}>
                <CampoInput
                  label="NORTE (m)"
                  value={pt.norte}
                  onChangeText={v => atualizarPonto(idx, 'norte', v)}
                  placeholder="7395001.003"
                />
              </View>
              <View style={s.col}>
                <CampoInput
                  label="ESTE (m)"
                  value={pt.este}
                  onChangeText={v => atualizarPonto(idx, 'este', v)}
                  placeholder="313500.512"
                />
              </View>
              <View style={s.col}>
                <CampoInput
                  label="COTA (m)"
                  value={pt.cota}
                  onChangeText={v => atualizarPonto(idx, 'cota', v)}
                  placeholder="opcional"
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
            <Text style={[ss.resLabel, { color: C.muted }]}>Resultado ({resultado.n} medições)</Text>

            <View style={s.resRow}>
              <View style={s.resItem}>
                <Text style={[ss.resValor, { color: C.primary }]}>{resultado.mediaNorte.toFixed(3)}</Text>
                <Text style={[s.resSub, { color: C.muted }]}>Média Norte (m)</Text>
              </View>
              <View style={[s.resDivider, { backgroundColor: C.cardBorder }]} />
              <View style={s.resItem}>
                <Text style={[ss.resValor, { color: C.primary }]}>{resultado.mediaEste.toFixed(3)}</Text>
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
  secao: { fontSize: 12, fontWeight: '700', marginBottom: 8, marginTop: 16, textTransform: 'uppercase', letterSpacing: 0.5 },
  pontoLabel: { fontSize: 11, fontWeight: '700', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 },
  tresCol: { flexDirection: 'row', gap: 8 },
  col: { flex: 1 },
  btnsPonto: { flexDirection: 'row', gap: 10, marginTop: 4, marginBottom: 4 },
  btnPonto: { flex: 1, padding: 10, borderRadius: 8, alignItems: 'center', borderWidth: 0.5 },
  btnPontoTxt: { fontSize: 14, fontWeight: '600' },
  resRow: { flexDirection: 'row', alignItems: 'center' },
  resItem: { flex: 1, alignItems: 'center' },
  resValorSm: { fontSize: 17, fontWeight: '700', fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  resSub: { fontSize: 12, marginTop: 4 },
  resDivider: { width: 0.5, height: 40, marginHorizontal: 16 },
  sepH: { height: 0.5, marginVertical: 14 },
  gabarito: { marginTop: 16, borderWidth: 0.5, borderRadius: 8, padding: 12, borderStyle: 'dashed' },
  gabaritoTxt: { fontSize: 12, textAlign: 'center' },
})
