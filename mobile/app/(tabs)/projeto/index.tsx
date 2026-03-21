import { useState, useCallback } from 'react'
import { View, Text, FlatList, RefreshControl, StyleSheet, ActivityIndicator, TouchableOpacity } from 'react-native'
import { useRouter } from 'expo-router'
import { useFocusEffect } from '@react-navigation/native'
import { Colors } from '../../../constants/Colors'
import { API_URL } from '../../../constants/Api'
import { ProjetoCard } from '../../../components/ProjetoCard'
import { initDB, cacheProjetos, getCachedProjetos } from '../../../lib/db'

export default function ProjetosScreen() {
  const C = Colors.dark
  const router = useRouter()
  const [projetos, setProjetos]   = useState<any[]>([])
  const [loading, setLoading]     = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [erro, setErro]           = useState('')
  const [offline, setOffline]     = useState(false)

  const carregar = async () => {
    try {
      setErro('')
      setOffline(false)
      await initDB()
      const res  = await fetch(`${API_URL}/projetos`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      const lista = data.projetos || []
      await cacheProjetos(lista)
      setProjetos(lista)
    } catch {
      try {
        const cached = await getCachedProjetos()
        if (cached.length > 0) {
          setProjetos(cached)
          setOffline(true)
        } else {
          setErro('Sem conexão e sem cache disponível.\nVerifique sua internet ou tente novamente.')
        }
      } catch {
        setErro('Não foi possível carregar os projetos.\nVerifique se o backend está rodando.')
      }
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

      {offline && (
        <View style={s.bannerOffline}>
          <Text style={s.bannerTxt}>📡 Offline — exibindo dados em cache</Text>
        </View>
      )}

      {loading && !refreshing ? (
        <View style={s.centro}>
          <ActivityIndicator color={C.primary} size="large" />
          <Text style={[s.msg, { color: C.muted }]}>Carregando...</Text>
        </View>
      ) : erro ? (
        <View style={s.centro}>
          <Text style={[s.msg, { color: C.danger }]}>{erro}</Text>
          <TouchableOpacity onPress={carregar} style={[s.btnRetry, { borderColor: C.primary }]} accessibilityRole="button" accessibilityLabel="Tentar novamente">
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
  container:     { flex: 1 },
  header:        { padding: 20, paddingTop: 56, borderBottomWidth: 0.5 },
  titulo:        { fontSize: 24, fontWeight: '700' },
  sub:           { fontSize: 13, marginTop: 2 },
  lista:         { padding: 14 },
  centro:        { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  msg:           { fontSize: 14, textAlign: 'center', marginTop: 12, lineHeight: 22 },
  btnRetry:      { marginTop: 16, borderWidth: 1, borderRadius: 8, paddingHorizontal: 20, paddingVertical: 14 },
  bannerOffline: { backgroundColor: '#B8860B', paddingVertical: 6, paddingHorizontal: 14 },
  bannerTxt:     { color: '#FFF8DC', fontSize: 12, fontWeight: '500', textAlign: 'center' },
})
