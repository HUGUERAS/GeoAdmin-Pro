/**
 * mobile/app/(tabs)/calculos/rag.tsx
 * Consulta às normas INCRA via RAG (IA).
 */

import { useState } from 'react'
import {
  View, Text, TextInput, TouchableOpacity, ScrollView,
  StyleSheet, ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native'
import { Colors } from '../constants/Colors'
import { apiPost } from '../lib/api'

interface ConsultaResponse {
  resposta: string
  fonte: string
  trecho: string
}

export default function RagScreen() {
  const C = Colors.dark
  const [pergunta, setPergunta]   = useState('')
  const [resultado, setResultado] = useState<ConsultaResponse | null>(null)
  const [loading, setLoading]     = useState(false)
  const [erro, setErro]           = useState<string | null>(null)

  const consultar = async () => {
    if (!pergunta.trim()) return
    setLoading(true)
    setErro(null)
    setResultado(null)
    try {
      const data = await apiPost<ConsultaResponse>('/rag/consultar', { pergunta })
      setResultado(data)
    } catch (e: any) {
      setErro(e?.message ?? 'Erro ao consultar.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <KeyboardAvoidingView
      style={[s.flex, { backgroundColor: C.background }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={[s.header, { backgroundColor: C.card, borderBottomColor: C.cardBorder }]}>
        <Text style={[s.titulo, { color: C.text }]}>Normas INCRA</Text>
        <Text style={[s.sub, { color: C.muted }]}>Consulta por IA — Norma Técnica 3ª Ed., Lei 13.465/2017, SIGEF</Text>
      </View>

      <ScrollView contentContainerStyle={s.body} keyboardShouldPersistTaps="handled">
        <TextInput
          style={[s.input, { backgroundColor: C.card, color: C.text, borderColor: C.cardBorder }]}
          placeholder="Digite sua dúvida técnica..."
          placeholderTextColor={C.muted}
          value={pergunta}
          onChangeText={setPergunta}
          multiline
          numberOfLines={3}
          textAlignVertical="top"
        />

        <TouchableOpacity
          style={[s.btn, { backgroundColor: loading ? C.muted : C.primary }]}
          onPress={consultar}
          disabled={loading || !pergunta.trim()}
          activeOpacity={0.8}
        >
          {loading
            ? <ActivityIndicator color="#fff" />
            : <Text style={[s.btnTxt, { color: C.primaryText }]}>Consultar</Text>
          }
        </TouchableOpacity>

        {erro && (
          <View style={[s.erroCard, { backgroundColor: C.card, borderColor: '#c0392b' }]}>
            <Text style={[s.erroTxt, { color: '#e74c3c' }]}>{erro}</Text>
          </View>
        )}

        {resultado && (
          <View style={[s.card, { backgroundColor: C.card, borderColor: C.primary }]}>
            <Text style={[s.fonteLabel, { color: C.muted }]}>FONTE</Text>
            <Text style={[s.fonteValor, { color: C.primary }]}>{resultado.fonte}</Text>

            <View style={[s.divider, { backgroundColor: C.cardBorder }]} />

            <Text style={[s.resposta, { color: C.text }]}>{resultado.resposta}</Text>

            {resultado.trecho ? (
              <View style={[s.trechoBox, { backgroundColor: C.background }]}>
                <Text style={[s.trechoTxt, { color: C.muted }]}>{resultado.trecho}</Text>
              </View>
            ) : null}
          </View>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  )
}

const s = StyleSheet.create({
  flex:       { flex: 1 },
  header:     { padding: 20, paddingTop: 56, borderBottomWidth: 0.5 },
  titulo:     { fontSize: 24, fontWeight: '700' },
  sub:        { fontSize: 12, marginTop: 4 },
  body:       { padding: 16, gap: 12 },
  input:      { borderRadius: 10, borderWidth: 1, padding: 14, fontSize: 15, minHeight: 90 },
  btn:        { borderRadius: 10, padding: 16, alignItems: 'center', minHeight: 56, justifyContent: 'center' },
  btnTxt:     { fontSize: 16, fontWeight: '700' },
  erroCard:   { borderRadius: 10, borderWidth: 1, padding: 14 },
  erroTxt:    { fontSize: 14 },
  card:       { borderRadius: 10, borderWidth: 1.5, padding: 16, gap: 8 },
  fonteLabel: { fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 },
  fonteValor: { fontSize: 13, fontWeight: '600' },
  divider:    { height: 0.5, marginVertical: 4 },
  resposta:   { fontSize: 15, lineHeight: 24 },
  trechoBox:  { borderRadius: 8, padding: 10, marginTop: 4 },
  trechoTxt:  { fontSize: 12, fontStyle: 'italic', lineHeight: 18 },
})


