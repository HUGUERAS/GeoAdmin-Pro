import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, ScrollView, StyleSheet, Alert, Platform } from 'react-native'
import * as Clipboard from 'expo-clipboard'
import { Feather } from '@expo/vector-icons'
import { Colors } from '../../../constants/Colors'
import { ScreenHeader } from '../../../components/ScreenHeader'

type Ponto = { id: string; nome: string; norte: string; este: string; cota: string }

let _seq = 0
function novoId() { return String(++_seq) }

function novoPonto(n: number): Ponto {
  return { id: novoId(), nome: `P-${String(n).padStart(2, '0')}`, norte: '', este: '', cota: '' }
}

export default function PontosScreen() {
  const C = Colors.dark
  const [pontos, setPontos] = useState<Ponto[]>([novoPonto(1)])
  const [copiado, setCopiado] = useState(false)

  const adicionar = () => {
    setPontos(prev => [...prev, novoPonto(prev.length + 1)])
  }

  const remover = (id: string) => {
    if (pontos.length <= 1) return
    setPontos(prev => prev.filter(p => p.id !== id))
  }

  const atualizar = (id: string, campo: keyof Ponto, valor: string) => {
    setPontos(prev => prev.map(p => p.id === id ? { ...p, [campo]: valor } : p))
  }

  const limpar = () => {
    setPontos([novoPonto(1)])
    setCopiado(false)
  }

  const copiar = () => {
    const linhas = pontos
      .filter(p => p.nome && p.norte && p.este)
      .map(p => `${p.nome}\t${p.norte}\t${p.este}\t${p.cota || '0.000'}`)
    if (linhas.length === 0) {
      Alert.alert('Nada para copiar', 'Preencha ao menos um ponto completo (Nome, Norte e Este).')
      return
    }
    const cabecalho = 'Nome\tNorte\tEste\tCota'
    Clipboard.setStringAsync([cabecalho, ...linhas].join('\n'))
    setCopiado(true)
    setTimeout(() => setCopiado(false), 2000)
  }

  const preenchidos = pontos.filter(p => p.norte && p.este).length

  return (
    <ScrollView style={[s.container, { backgroundColor: C.background }]} keyboardShouldPersistTaps="handled">
      <ScreenHeader titulo="Pontos" subtitulo="Lista de pontos UTM — bloco de notas de campo" />

      <View style={s.body}>
        <View style={s.topBar}>
          <Text style={[s.secao, { color: C.primary, marginTop: 0 }]}>
            {preenchidos > 0 ? `${preenchidos} ponto${preenchidos > 1 ? 's' : ''}` : 'Nenhum ponto preenchido'}
          </Text>
          <TouchableOpacity style={[s.btnCopiar, { borderColor: copiado ? C.primary : C.cardBorder }]} onPress={copiar}>
            <Feather name={copiado ? 'check' : 'copy'} size={14} color={copiado ? C.primary : C.muted} />
            <Text style={[s.btnCopiarTxt, { color: copiado ? C.primary : C.muted }]}>{copiado ? 'Copiado!' : 'Copiar'}</Text>
          </TouchableOpacity>
        </View>

        {pontos.map((p, i) => (
          <View key={p.id} style={[s.pontoCard, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
            <View style={s.pontoHeader}>
              <Text style={[s.pontoIdx, { color: C.muted }]}>{i + 1}</Text>
              <TextInput
                style={[s.nomeInput, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
                value={p.nome}
                onChangeText={v => atualizar(p.id, 'nome', v)}
                placeholder={`P-${String(i + 1).padStart(2, '0')}`}
                placeholderTextColor={C.muted}
                returnKeyType="next"
              />
              <TouchableOpacity
                style={[s.btnRemover, { opacity: pontos.length <= 1 ? 0.3 : 1 }]}
                onPress={() => remover(p.id)}
                disabled={pontos.length <= 1}
              >
                <Feather name="trash-2" size={14} color={C.muted} />
              </TouchableOpacity>
            </View>
            <View style={s.coordRow}>
              <View style={s.coordThird}>
                <Text style={[s.label, { color: C.muted }]}>NORTE (m)</Text>
                <TextInput
                  style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
                  value={p.norte}
                  onChangeText={v => atualizar(p.id, 'norte', v)}
                  placeholder="7395000.000"
                  placeholderTextColor={C.muted}
                  keyboardType="numeric"
                  returnKeyType="next"
                />
              </View>
              <View style={s.coordThird}>
                <Text style={[s.label, { color: C.muted }]}>ESTE (m)</Text>
                <TextInput
                  style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
                  value={p.este}
                  onChangeText={v => atualizar(p.id, 'este', v)}
                  placeholder="313500.000"
                  placeholderTextColor={C.muted}
                  keyboardType="numeric"
                  returnKeyType="next"
                />
              </View>
              <View style={s.coordThird}>
                <Text style={[s.label, { color: C.muted }]}>COTA (m)</Text>
                <TextInput
                  style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
                  value={p.cota}
                  onChangeText={v => atualizar(p.id, 'cota', v)}
                  placeholder="750.000"
                  placeholderTextColor={C.muted}
                  keyboardType="numeric"
                  returnKeyType="done"
                />
              </View>
            </View>
          </View>
        ))}

        <TouchableOpacity style={[s.btnAdd, { borderColor: C.primary }]} onPress={adicionar}>
          <Feather name="plus" size={16} color={C.primary} />
          <Text style={[s.btnAddTxt, { color: C.primary }]}>Adicionar ponto</Text>
        </TouchableOpacity>

        <TouchableOpacity style={[s.btnLimpar, { borderColor: C.cardBorder }]} onPress={limpar}>
          <Text style={[s.btnLimparTxt, { color: C.muted }]}>Limpar tudo</Text>
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
  topBar: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  secao: { fontSize: 12, fontWeight: '700', marginTop: 16, textTransform: 'uppercase', letterSpacing: 0.5 },
  btnCopiar: { flexDirection: 'row', alignItems: 'center', gap: 5, borderWidth: 0.5, borderRadius: 6, paddingHorizontal: 10, paddingVertical: 6 },
  btnCopiarTxt: { fontSize: 12, fontWeight: '600' },
  pontoCard: { borderRadius: 10, borderWidth: 0.5, padding: 14, marginBottom: 8 },
  pontoHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 10, gap: 8 },
  pontoIdx: { fontSize: 12, fontWeight: '700', width: 18, textAlign: 'center' },
  nomeInput: { flex: 1, borderWidth: 0.5, borderRadius: 6, padding: 8, fontSize: 14, fontWeight: '600', fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  btnRemover: { padding: 4 },
  coordRow: { flexDirection: 'row', gap: 8 },
  coordThird: { flex: 1 },
  label: { fontSize: 10, fontWeight: '600', marginBottom: 5, textTransform: 'uppercase', letterSpacing: 0.3 },
  input: { borderWidth: 0.5, borderRadius: 8, padding: 10, fontSize: 13, fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  btnAdd: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, borderWidth: 0.5, borderRadius: 8, padding: 12, borderStyle: 'dashed', marginTop: 4 },
  btnAddTxt: { fontSize: 14, fontWeight: '600' },
  btnLimpar: { marginTop: 12, borderWidth: 0.5, borderRadius: 8, padding: 12, alignItems: 'center' },
  btnLimparTxt: { fontSize: 14 },
})
