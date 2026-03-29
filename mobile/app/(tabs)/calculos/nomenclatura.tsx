import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, ScrollView, StyleSheet, Clipboard } from 'react-native'
import { Feather } from '@expo/vector-icons'
import { Colors } from '../../../constants/Colors'

type Tipo = 'M' | 'P' | 'E' | 'MM'

const TIPOS: { id: Tipo; label: string; desc: string; cor: string }[] = [
  { id: 'M',  label: 'Marco (M)',          desc: 'Vértice com marco físico implantado em campo',              cor: '#EF9F27' },
  { id: 'P',  label: 'Ponto (P)',           desc: 'Vértice sem marco físico — identificado apenas em planta',  cor: '#4EA8DE' },
  { id: 'E',  label: 'Estação (E)',         desc: 'Estação de apoio geodésico / RN auxiliar',                  cor: '#69DB7C' },
  { id: 'MM', label: 'Marco-Mestre (MM)',   desc: 'Marco principal de implantação e referência do perímetro',  cor: '#DA77F2' },
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
    Clipboard.setString(nomes.join('\n'))
    setCopiado(true)
    setTimeout(() => setCopiado(false), 2000)
  }

  const tipoAtual = TIPOS.find(t => t.id === tipo)!

  return (
    <ScrollView style={[s.container, { backgroundColor: C.background }]} keyboardShouldPersistTaps="handled">
      <View style={[s.header, { backgroundColor: C.card, borderBottomColor: C.cardBorder }]}>
        <Text style={[s.titulo, { color: C.text }]}>Nomenclatura</Text>
        <Text style={[s.sub, { color: C.muted }]}>Gerador de nomes de vértices conforme padrão INCRA/SIGEF</Text>
      </View>

      <View style={s.body}>
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
        <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
          <View style={s.paramRow}>
            <View style={s.paramHalf}>
              <Text style={[s.label, { color: C.muted }]}>NÚMERO INICIAL</Text>
              <TextInput
                style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
                value={inicio}
                onChangeText={v => { setInicio(v); setNomes([]) }}
                placeholder="1"
                placeholderTextColor={C.muted}
                keyboardType="numeric"
                returnKeyType="next"
              />
            </View>
            <View style={s.paramHalf}>
              <Text style={[s.label, { color: C.muted }]}>QUANTIDADE (máx 100)</Text>
              <TextInput
                style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
                value={quantidade}
                onChangeText={v => { setQuantidade(v); setNomes([]) }}
                placeholder="10"
                placeholderTextColor={C.muted}
                keyboardType="numeric"
                returnKeyType="done"
              />
            </View>
          </View>
        </View>

        <TouchableOpacity style={[s.btnPri, { backgroundColor: C.primary, marginTop: 16 }]} onPress={gerar}>
          <Text style={[s.btnPriTxt, { color: C.primaryText }]}>Gerar nomenclatura</Text>
        </TouchableOpacity>

        {nomes.length > 0 && (
          <View style={[s.resultado, { backgroundColor: C.card, borderColor: tipoAtual.cor }]}>
            <View style={s.resHeader}>
              <Text style={[s.resLabel, { color: C.muted }]}>{nomes.length} nomes — prefixo {tipo}</Text>
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
            { sigla: 'P-01', sig: 'Ponto virtual (sem marco)',          cor: '#4EA8DE' },
            { sigla: 'E-01', sig: 'Estação de apoio geodésico',         cor: '#69DB7C' },
            { sigla: 'MM-01',sig: 'Marco-mestre do perímetro',          cor: '#DA77F2' },
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
  container:    { flex: 1 },
  header:       { padding: 20, paddingTop: 56, borderBottomWidth: 0.5 },
  titulo:       { fontSize: 24, fontWeight: '700' },
  sub:          { fontSize: 13, marginTop: 2 },
  body:         { padding: 16 },
  secao:        { fontSize: 12, fontWeight: '700', marginBottom: 8, marginTop: 16, textTransform: 'uppercase', letterSpacing: 0.5 },
  tipoCard:     { flexDirection: 'row', alignItems: 'center', gap: 12, borderWidth: 1, borderRadius: 10, padding: 14, marginBottom: 8 },
  tipoBadge:    { width: 40, height: 40, borderRadius: 8, alignItems: 'center', justifyContent: 'center' },
  tipoBadgeTxt: { fontSize: 12, fontWeight: '700' },
  tipoTexto:    { flex: 1 },
  tipoLabel:    { fontSize: 14, fontWeight: '700' },
  tipoDesc:     { fontSize: 12, marginTop: 2 },
  card:         { borderRadius: 10, borderWidth: 0.5, padding: 14 },
  paramRow:     { flexDirection: 'row', gap: 12 },
  paramHalf:    { flex: 1 },
  label:        { fontSize: 10, fontWeight: '600', marginBottom: 5, textTransform: 'uppercase', letterSpacing: 0.3 },
  input:        { borderWidth: 0.5, borderRadius: 8, padding: 12, fontSize: 15 },
  btnPri:       { padding: 16, borderRadius: 10, alignItems: 'center', justifyContent: 'center', minHeight: 52 },
  btnPriTxt:    { fontSize: 16, fontWeight: '700' },
  resultado:    { marginTop: 20, borderRadius: 12, borderWidth: 1, padding: 16 },
  resHeader:    { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  resLabel:     { fontSize: 10, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5 },
  btnCopiar:    { flexDirection: 'row', alignItems: 'center', gap: 4, borderWidth: 0.5, borderRadius: 6, paddingHorizontal: 8, paddingVertical: 5 },
  btnCopiarTxt: { fontSize: 12, fontWeight: '600' },
  nomeGrid:     { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  nomePill:     { borderWidth: 0.5, borderRadius: 6, paddingHorizontal: 10, paddingVertical: 5 },
  nomeTxt:      { fontSize: 13, fontWeight: '600', fontFamily: 'monospace' },
  referencia:   { marginTop: 20, borderRadius: 10, borderWidth: 0.5, padding: 14, marginBottom: 16 },
  refTitulo:    { fontSize: 10, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 12 },
  refRow:       { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 8 },
  refBadge:     { borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4, minWidth: 56, alignItems: 'center' },
  refSigla:     { fontSize: 12, fontWeight: '700', fontFamily: 'monospace' },
  refDesc:      { fontSize: 12, flex: 1 },
})
