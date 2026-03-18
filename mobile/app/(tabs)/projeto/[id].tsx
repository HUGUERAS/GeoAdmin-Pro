import { useState, useEffect } from 'react'
import { View, Text, ScrollView, StyleSheet, ActivityIndicator, TouchableOpacity, Alert, Clipboard } from 'react-native'
import { useLocalSearchParams } from 'expo-router'
import { Colors } from '../../../constants/Colors'
import { API_URL } from '../../../constants/Api'
import { StatusBadge } from '../../../components/StatusBadge'

export default function DetalheProjetoScreen() {
  const C = Colors.dark
  const { id } = useLocalSearchParams<{ id: string }>()
  const [projeto, setProjeto]   = useState<any>(null)
  const [loading, setLoading]   = useState(true)
  const [gerando, setGerando]   = useState(false)

  useEffect(() => {
    fetch(`${API_URL}/projetos/${id}`)
      .then(r => r.json())
      .then(setProjeto)
      .catch(() => Alert.alert('Erro', 'Projeto não encontrado'))
      .finally(() => setLoading(false))
  }, [id])

  const gerarMagicLink = async () => {
    try {
      const res  = await fetch(`${API_URL}/projetos/${id}/magic-link`, { method: 'POST' })
      const data = await res.json()
      Clipboard.setString(data.mensagem_whatsapp || data.link)
      Alert.alert('Link copiado!', 'Mensagem para WhatsApp copiada.\nCole direto no chat do cliente.')
    } catch {
      Alert.alert('Erro', 'Não foi possível gerar o link.')
    }
  }

  const gerarDocumentos = async () => {
    setGerando(true)
    try {
      const res = await fetch(`${API_URL}/projetos/${id}/gerar-documentos`, { method: 'POST' })
      if (!res.ok) {
        const err = await res.json()
        Alert.alert('Atenção', err.erro || 'Erro ao gerar documentos.')
        return
      }
      Alert.alert('Pronto!', 'Documentos gerados. Acesse pelo computador em /projetos/' + id + '/documentos')
    } catch {
      Alert.alert('Erro', 'Falha ao gerar documentos.')
    } finally {
      setGerando(false)
    }
  }

  if (loading) return (
    <View style={[s.centro, { backgroundColor: C.background }]}>
      <ActivityIndicator color={C.primary} size="large" />
    </View>
  )

  if (!projeto) return (
    <View style={[s.centro, { backgroundColor: C.background }]}>
      <Text style={{ color: C.muted }}>Projeto não encontrado.</Text>
    </View>
  )

  return (
    <ScrollView style={[s.container, { backgroundColor: C.background }]}>
      <View style={[s.header, { backgroundColor: C.card, borderBottomColor: C.cardBorder }]}>
        <Text style={[s.titulo, { color: C.text }]} numberOfLines={2}>{projeto.projeto_nome}</Text>
        <View style={{ marginTop: 8 }}><StatusBadge status={projeto.status} /></View>
      </View>

      <View style={s.body}>
        {[
          ['Cliente',   projeto.cliente_nome],
          ['Município', projeto.municipio],
          ['Comarca',   projeto.comarca],
          ['Matrícula', projeto.matricula],
          ['Job',       projeto.numero_job],
          ['Área',      projeto.area_ha ? `${projeto.area_ha} ha` : null],
          ['Pontos',    projeto.total_pontos?.toString()],
        ].filter(([,v]) => v).map(([label, valor]) => (
          <View key={label as string} style={[s.campo, { borderBottomColor: C.cardBorder }]}>
            <Text style={[s.campoLabel, { color: C.muted }]}>{label}</Text>
            <Text style={[s.campoValor, { color: C.text }]}>{valor}</Text>
          </View>
        ))}

        <TouchableOpacity style={[s.btn, { backgroundColor: C.card, borderColor: C.primary }]} onPress={gerarMagicLink}>
          <Text style={[s.btnTxt, { color: C.primary }]}>📱 Copiar Link do Cliente</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[s.btn, { backgroundColor: C.primary }]}
          onPress={gerarDocumentos}
          disabled={gerando}
        >
          {gerando
            ? <ActivityIndicator color={C.primaryText} />
            : <Text style={[s.btnTxt, { color: C.primaryText }]}>📄 Gerar Documentos GPRF</Text>
          }
        </TouchableOpacity>
      </View>
    </ScrollView>
  )
}

const s = StyleSheet.create({
  container:  { flex: 1 },
  centro:     { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header:     { padding: 20, paddingTop: 56, borderBottomWidth: 0.5 },
  titulo:     { fontSize: 22, fontWeight: '700' },
  body:       { padding: 16 },
  campo:      { paddingVertical: 12, borderBottomWidth: 0.5 },
  campoLabel: { fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 2 },
  campoValor: { fontSize: 15, fontWeight: '500' },
  btn:        { borderRadius: 10, padding: 16, alignItems: 'center', marginTop: 12, borderWidth: 1 },
  btnTxt:     { fontSize: 15, fontWeight: '700' },
})
