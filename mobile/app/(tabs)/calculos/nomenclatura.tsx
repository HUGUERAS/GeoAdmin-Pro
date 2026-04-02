import { useState } from 'react'
import { View, Text, TouchableOpacity, ScrollView, StyleSheet } from 'react-native'
import * as Clipboard from 'expo-clipboard'
import { Feather } from '@expo/vector-icons'
import { Colors } from '../../../constants/Colors'
import { ScreenHeader } from '../../../components/ScreenHeader'
import { ss } from '@/styles/ss'
import { CampoInput } from '../../../components/CampoInput'

type Tipo = 'M' | 'P' | 'E' | 'MM'

const TIPOS: { id: Tipo; label: string; desc: string; cor: string }[] = [
  { id: 'M', label: 'Marco (M)', desc: 'Vértice com marco físico implantado em campo', cor: '#EF9F27' },
  { id: 'P', label: 'Ponto (P)', desc: 'Vértice sem marco físico — identificado apenas em planta', cor: '#4EA8DE' },
  { id: 'E', label: 'Estação (E)', desc: 'Estação de apoio geodésico / RN auxiliar', cor: '#69DB7C' },
  { id: 'MM', label: 'Marco-Mestre (MM)', desc: 'Marco principal de implantação e referência do perímetro', cor: '#DA77F2' },
]

export default function NomenclaturaScreen() {
  const C = Colors.dark
  const [tipo, setTipo] = useState<Tipo>('M')
  const [inicio, setInicio] = useState('1')
  const [quantidade, setQuantidade] = useState('10')
  const [nomes, setNomes] = useState<string[]>([])
  const [copiado, setCopiado] = useState(false)

  const gerar = () => {
    const n = parseInt(inicio) || 1
    const q = Math.min(parseInt(quantidade) || 5, 100)
    const lista: string[] = []
    for (let i = 0; i < q; i++) {
      lista.push(`${tipo}-${String(n + i).padStart(2, '0')}`)
    }
    setNomes(lista)
    setCopiado(false)
  }

  const copiar = () => {
    if (nomes.length === 0) return
    Clipboard.setStringAsync(nomes.join('\n'))
    setCopiado(true)
    setTimeout(() => setCopiado(false), 2000)
  }

  const tipoAtual = TIPOS.find(t => t.id === tipo)!

  return (
    <ScrollView style={[ss.container, { backgroundColor: C.background }]} keyboardShouldPersistTaps="handled">
      <ScreenHeader titulo="Nomenclatura" subtitulo="Gerador de nomes de vértices conforme padrão INCRA/SIGEF" />

      <View style={ss.body}>
        <Text style={[s.secao, { color: C.primary }]}>Tipo de vértice</Text>
        {TIPOS.map(t => (
          <TouchableOpacity
            key={t.id}
            style={[s.tipoCard, { backgroundColor: C.card, borderColor: tipo === t.id ? t.cor : C.cardBorder }]}
            onPress={() => { setTipo(t.id); setNomes([]) }}
          >
            <View style={[s.tipoBadge, { backgroundColor: tipo === t.id ? t.cor : C.cardBorder }]}>
              <Text style={[s.tipoBadgeTxt, { color: tipo === t.id ? '#000' : C.muted }]}>{t.id}</Text>
            </View>
            <View style={s.tipoTexto}>
              <Text style={[s.tipoLabel, { color: tipo === t.id ? t.cor : C.text }]}>{t.label}</Text>
              <Text style={[s.tipoDesc, { color: C.muted }]}>{t.desc}</Text>
            </View>
            {tipo === t.id && <Feather name="check" size={16} color={t.cor} />}
          </TouchableOpacity>
        ))}

        <Text style={[s.secao, { color: C.primary }]}>Parâmetros</Text>
        <View style={[ss.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
          <View style={s.paramRow}>
            <View style={s.paramHalf}>
              <CampoInput
                label="NÚMERO INICIAL"
                value={inicio}
                onChangeText={v => { setInicio(v); setNomes([]) }}
                placeholder="1"
              />
            </View>
            <View style={s.paramHalf}>
              <CampoInput
                label="QUANTIDADE (máx 100)"
                value={quantidade}
                onChangeText={v => { setQuantidade(v); setNomes([]) }}
                placeholder="10"
              />
            </View>
          </View>
        </View>

        <TouchableOpacity style={[ss.btnPri, { backgroundColor: C.primary, marginTop: 16 }]} onPress={gerar}>
          <Text style={[ss.btnPriTxt, { color: C.primaryText }]}>Gerar nomenclatura</Text>
        </TouchableOpacity>

        {nomes.length > 0 && (
          <View style={[ss.resultado, { backgroundColor: C.card, borderColor: tipoAtual.cor }]}>
            <View style={s.resHeader}>
              <Text style={[ss.resLabel, { color: C.muted }]}>{nomes.length} nomes — prefixo {tipo}</Text>
              <TouchableOpacity style={[s.btnCopiar, { borderColor: copiado ? tipoAtual.cor : C.cardBorder }]} onPress={copiar}>
                <Feather name={copiado ? 'check' : 'copy'} size={13} color={copiado ? tipoAtual.cor : C.muted} />
                <Text style={[s.btnCopiarTxt, { color: copiado ? tipoAtual.cor : C.muted }]}>{copiado ? 'Copiado!' : 'Copiar'}</Text>
              </TouchableOpacity>
            </View>
            <View style={s.nomeGrid}>
              {nomes.map((n, i) => (
                <View key={i} style={[s.nomePill, { borderColor: C.cardBorder }]}>
                  <Text style={[s.nomeTxt, { color: C.text }]}>{n}</Text>
                </View>
              ))}
            </View>
          </View>
        )}

        <View style={[s.referencia, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
          <Text style={[s.refTitulo, { color: C.muted }]}>Referência INCRA/SIGEF</Text>
          {[
            { sigla: 'M-01', sig: 'Marco físico (vértice implantado)', cor: '#EF9F27' },
            { sigla: 'P-01', sig: 'Ponto virtual (sem marco)', cor: '#4EA8DE' },
            { sigla: 'E-01', sig: 'Estação de apoio geodésico', cor: '#69DB7C' },
            { sigla: 'MM-01', sig: 'Marco-mestre do perímetro', cor: '#DA77F2' },
          ].map(r => (
            <View key={r.sigla} style={s.refRow}>
              <View style={[s.refBadge, { backgroundColor: r.cor + '22' }]}>
                <Text style={[s.refSigla, { color: r.cor }]}>{r.sigla}</Text>
              </View>
              <Text style={[s.refDesc, { color: C.muted }]}>{r.sig}</Text>
            </View>
          ))}
        </View>
      </View>
    </ScrollView>
  )
}

const s = StyleSheet.create({
  secao: { fontSize: 12, fontWeight: '700', marginBottom: 8, marginTop: 16, textTransform: 'uppercase', letterSpacing: 0.5 },
  tipoCard: { flexDirection: 'row', alignItems: 'center', gap: 12, borderWidth: 1, borderRadius: 10, padding: 14, marginBottom: 8 },
  tipoBadge: { width: 40, height: 40, borderRadius: 8, alignItems: 'center', justifyContent: 'center' },
  tipoBadgeTxt: { fontSize: 12, fontWeight: '700' },
  tipoTexto: { flex: 1 },
  tipoLabel: { fontSize: 14, fontWeight: '700' },
  tipoDesc: { fontSize: 12, marginTop: 2 },
  paramRow: { flexDirection: 'row', gap: 12 },
  paramHalf: { flex: 1 },
  resHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  btnCopiar: { flexDirection: 'row', alignItems: 'center', gap: 4, borderWidth: 0.5, borderRadius: 6, paddingHorizontal: 8, paddingVertical: 5 },
  btnCopiarTxt: { fontSize: 12, fontWeight: '600' },
  nomeGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  nomePill: { borderWidth: 0.5, borderRadius: 6, paddingHorizontal: 10, paddingVertical: 5 },
  nomeTxt: { fontSize: 13, fontWeight: '600', fontFamily: 'monospace' },
  referencia: { marginTop: 20, borderRadius: 10, borderWidth: 0.5, padding: 14, marginBottom: 16 },
  refTitulo: { fontSize: 10, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 12 },
  refRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 8 },
  refBadge: { borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4, minWidth: 56, alignItems: 'center' },
  refSigla: { fontSize: 12, fontWeight: '700', fontFamily: 'monospace' },
  refDesc: { fontSize: 12, flex: 1 },
})
