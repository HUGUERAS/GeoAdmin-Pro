import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, ScrollView, StyleSheet, Platform } from 'react-native'
import { Feather } from '@expo/vector-icons'
import { Colors } from '../../../constants/Colors'
import { ScreenHeader } from '../../../components/ScreenHeader'
import { ss } from '@/styles/ss'
import { CampoInput } from '../../../components/CampoInput'

type Ponto = { id: string; nome: string; norte: string; este: string }

type Segmento = {
  de: string
  para: string
  distancia: number
  azimute: number
  azimuteDms: string
}

function decimalParaDms(graus: number): string {
  const g = Math.floor(graus)
  const mf = (graus - g) * 60
  const m = Math.floor(mf)
  const s = ((mf - m) * 60).toFixed(2)
  return `${String(g).padStart(2, '0')}°${String(m).padStart(2, '0')}'${String(s).padStart(5, '0')}"`
}

let _idSeq = 0
function novoId() { return String(++_idSeq) }

export default function PolilinhaScreen() {
  const C = Colors.dark
  const [pontos, setPontos] = useState<Ponto[]>([
    { id: novoId(), nome: 'P-01', norte: '', este: '' },
    { id: novoId(), nome: 'P-02', norte: '', este: '' },
  ])
  const [segmentos, setSegmentos] = useState<Segmento[]>([])

  const adicionarPonto = () => {
    const n = pontos.length + 1
    setPontos(prev => [...prev, { id: novoId(), nome: `P-${String(n).padStart(2, '0')}`, norte: '', este: '' }])
    setSegmentos([])
  }

  const removerPonto = (id: string) => {
    if (pontos.length <= 2) return
    setPontos(prev => prev.filter(p => p.id !== id))
    setSegmentos([])
  }

  const atualizarPonto = (id: string, campo: keyof Ponto, valor: string) => {
    setPontos(prev => prev.map(p => p.id === id ? { ...p, [campo]: valor } : p))
    setSegmentos([])
  }

  const calcular = () => {
    const segs: Segmento[] = []
    for (let i = 0; i < pontos.length - 1; i++) {
      const a = pontos[i], b = pontos[i + 1]
      const y1 = parseFloat(a.norte), x1 = parseFloat(a.este)
      const y2 = parseFloat(b.norte), x2 = parseFloat(b.este)
      if ([x1, y1, x2, y2].some(isNaN)) {
        setSegmentos([])
        return
      }
      const dx = x2 - x1, dy = y2 - y1
      const dist = Math.sqrt(dx * dx + dy * dy)
      let az = Math.atan2(dx, dy) * 180 / Math.PI
      if (az < 0) az += 360
      segs.push({ de: a.nome || `P${i + 1}`, para: b.nome || `P${i + 2}`, distancia: dist, azimute: az, azimuteDms: decimalParaDms(az) })
    }
    setSegmentos(segs)
  }

  const limpar = () => {
    setPontos([
      { id: novoId(), nome: 'P-01', norte: '', este: '' },
      { id: novoId(), nome: 'P-02', norte: '', este: '' },
    ])
    setSegmentos([])
  }

  const totalMetros = segmentos.reduce((acc, s) => acc + s.distancia, 0)

  return (
    <ScrollView style={[ss.container, { backgroundColor: C.background }]} keyboardShouldPersistTaps="handled">
      <ScreenHeader titulo="Polilinha" subtitulo="Distância e azimute de cada segmento de uma sequência de pontos" />

      <View style={ss.body}>
        <Text style={[s.secao, { color: C.primary }]}>Pontos</Text>

        {pontos.map((p, i) => (
          <View key={p.id} style={[s.pontoCard, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
            <View style={s.pontoHeader}>
              <TextInput
                style={[s.nomeInput, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
                value={p.nome}
                onChangeText={v => atualizarPonto(p.id, 'nome', v)}
                placeholder={`P-${String(i + 1).padStart(2, '0')}`}
                placeholderTextColor={C.muted}
              />
              <TouchableOpacity
                style={[s.btnRemover, { opacity: pontos.length <= 2 ? 0.3 : 1 }]}
                onPress={() => removerPonto(p.id)}
                disabled={pontos.length <= 2}
              >
                <Feather name="x" size={16} color={C.muted} />
              </TouchableOpacity>
            </View>
            <View style={s.coordRow}>
              <View style={s.coordHalf}>
                <CampoInput
                  label="NORTE (m)"
                  value={p.norte}
                  onChangeText={v => atualizarPonto(p.id, 'norte', v)}
                  placeholder="7395000.000"
                />
              </View>
              <View style={s.coordHalf}>
                <CampoInput
                  label="ESTE (m)"
                  value={p.este}
                  onChangeText={v => atualizarPonto(p.id, 'este', v)}
                  placeholder="313500.000"
                />
              </View>
            </View>
          </View>
        ))}

        <TouchableOpacity style={[s.btnAdd, { borderColor: C.primary }]} onPress={adicionarPonto}>
          <Feather name="plus" size={16} color={C.primary} />
          <Text style={[s.btnAddTxt, { color: C.primary }]}>Adicionar ponto</Text>
        </TouchableOpacity>

        <View style={ss.btns}>
          <TouchableOpacity style={[ss.btnSec, { borderColor: C.cardBorder }]} onPress={limpar}>
            <Text style={[ss.btnSecTxt, { color: C.muted }]}>Limpar</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[ss.btnPri, { backgroundColor: C.primary }]} onPress={calcular}>
            <Text style={[ss.btnPriTxt, { color: C.primaryText }]}>Calcular</Text>
          </TouchableOpacity>
        </View>

        {segmentos.length > 0 && (
          <View style={[ss.resultado, { backgroundColor: C.card, borderColor: C.primary }]}>
            <Text style={[ss.resLabel, { color: C.muted }]}>Segmentos</Text>

            {segmentos.map((seg, i) => (
              <View key={i} style={[s.segRow, i < segmentos.length - 1 && { borderBottomWidth: 0.5, borderBottomColor: C.cardBorder }]}>
                <View style={s.segNomes}>
                  <Text style={[s.segNome, { color: C.text }]}>{seg.de} → {seg.para}</Text>
                </View>
                <View style={s.segVals}>
                  <Text style={[s.segDist, { color: C.primary }]}>{seg.distancia.toFixed(3)} m</Text>
                  <Text style={[s.segAz, { color: C.text }]}>{seg.azimuteDms}</Text>
                </View>
              </View>
            ))}

            <View style={[s.totalRow, { borderTopColor: C.primary }]}>
              <Text style={[s.totalLabel, { color: C.muted }]}>Comprimento total</Text>
              <Text style={[s.totalValor, { color: C.primary }]}>{totalMetros.toFixed(3)} m</Text>
            </View>
          </View>
        )}
      </View>
    </ScrollView>
  )
}

const s = StyleSheet.create({
  secao: { fontSize: 12, fontWeight: '700', marginBottom: 8, marginTop: 16, textTransform: 'uppercase', letterSpacing: 0.5 },
  pontoCard: { borderRadius: 10, borderWidth: 0.5, padding: 14, marginBottom: 8 },
  pontoHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 10 },
  nomeInput: { flex: 1, borderWidth: 0.5, borderRadius: 6, padding: 8, fontSize: 14, fontWeight: '600', fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  btnRemover: { padding: 8, marginLeft: 8 },
  coordRow: { flexDirection: 'row', gap: 10 },
  coordHalf: { flex: 1 },
  btnAdd: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, borderWidth: 0.5, borderRadius: 8, padding: 12, borderStyle: 'dashed', marginTop: 4 },
  btnAddTxt: { fontSize: 14, fontWeight: '600' },
  segRow: { paddingVertical: 12, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  segNomes: { flex: 1 },
  segNome: { fontSize: 14, fontWeight: '600' },
  segVals: { alignItems: 'flex-end' },
  segDist: { fontSize: 15, fontWeight: '700', fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  segAz: { fontSize: 12, marginTop: 2, fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  totalRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 14, paddingTop: 14, borderTopWidth: 1 },
  totalLabel: { fontSize: 12, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.3 },
  totalValor: { fontSize: 18, fontWeight: '700', fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
})
