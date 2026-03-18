import { useState, useCallback } from 'react'
import { View, Text, FlatList, RefreshControl, StyleSheet, ActivityIndicator, TouchableOpacity } from 'react-native'
import { useRouter } from 'expo-router'
import { useFocusEffect } from '@react-navigation/native'
import { Colors } from '../../../constants/Colors'
import { API_URL } from '../../../constants/Api'
import { ProjetoCard } from '../../../components/ProjetoCard'

export default function ProjetosScreen() {
  const C = Colors.dark
  const router = useRouter()
  const [projetos, setProjetos]   = useState<any[]>([])
  const [loading, setLoading]     = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [erro, setErro]           = useState('')

  const carregar = async () => {
    try {
      setErro('')
      const res  = await fetch(`${API_URL}/projetos`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setProjetos(data.projetos || [])
    } catch (e: any) {
      setErro('Não foi possível carregar os projetos.\nVerifique se o backend está rodando.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useFocusEffect(useCallback(() => { carregar() }, []))

  return (
    <View style={[s.container, { backgroundColor: C.background }]}>
      <View style={[s.header, { backgroundColor: C.card, borderBottomColor: C.cardBorder }]}>
        <Text style={[s.titulo, { color: C.text }]}>Projetos</Text>
        <Text style={[s.sub, { color: C.muted }]}>{projetos.length} cadastrados</Text>
      </View>

      {loading && !refreshing ? (
        <View style={s.centro}>
          <ActivityIndicator color={C.primary} size="large" />
          <Text style={[s.msg, { color: C.muted }]}>Carregando...</Text>
        </View>
      ) : erro ? (
        <View style={s.centro}>
          <Text style={[s.msg, { color: C.danger }]}>{erro}</Text>
          <TouchableOpacity onPress={carregar} style={[s.btnRetry, { borderColor: C.primary }]}>
            <Text style={{ color: C.primary, fontWeight: '600' }}>Tentar novamente</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={projetos}
          keyExtractor={p => p.id}
          contentContainerStyle={s.lista}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); carregar() }} tintColor={C.primary} />}
          renderItem={({ item }) => (
            <ProjetoCard projeto={item} onPress={() => router.push(`/projeto/${item.id}` as any)} />
          )}
          ListEmptyComponent={<Text style={[s.msg, { color: C.muted }]}>Nenhum projeto cadastrado.</Text>}
        />
      )}
    </View>
  )
}

const s = StyleSheet.create({
  container: { flex: 1 },
  header:    { padding: 20, paddingTop: 56, borderBottomWidth: 0.5 },
  titulo:    { fontSize: 24, fontWeight: '700' },
  sub:       { fontSize: 13, marginTop: 2 },
  lista:     { padding: 14 },
  centro:    { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  msg:       { fontSize: 14, textAlign: 'center', marginTop: 12, lineHeight: 22 },
  btnRetry:  { marginTop: 16, borderWidth: 1, borderRadius: 8, paddingHorizontal: 20, paddingVertical: 10 },
})
