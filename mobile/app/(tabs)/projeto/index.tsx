import { useState, useCallback } from 'react'
import {
  View,
  Text,
  FlatList,
  RefreshControl,
  StyleSheet,
  ActivityIndicator,
  TouchableOpacity,
  ScrollView,
  TextInput,
} from 'react-native'
import { useRouter } from 'expo-router'
import { Feather } from '@expo/vector-icons'
import { useFocusEffect } from '@react-navigation/native'
import { Colors } from '../../../constants/Colors'
import { API_URL } from '../../../constants/Api'
import { ProjetoCard } from '../../../components/ProjetoCard'
import { initDB, cacheProjetos, getCachedProjetos } from '../../../lib/db'

const CHIPS: { label: string; value: string | null }[] = [
  { label: 'Todos',       value: null          },
  { label: 'Medição',     value: 'medicao'     },
  { label: 'Montagem',    value: 'montagem'    },
  { label: 'Protocolado', value: 'protocolado' },
  { label: 'Aprovado',    value: 'aprovado'    },
  { label: 'Finalizado',  value: 'finalizado'  },
]

export default function ProjetosScreen() {
  const C = Colors.dark
  const router = useRouter()
  const [projetos, setProjetos]     = useState<any[]>([])
  const [loading, setLoading]       = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [erro, setErro]             = useState('')
  const [offline, setOffline]       = useState(false)
  const [filtroStatus, setFiltroStatus] = useState<string | null>(null)
  const [busca, setBusca]           = useState('')

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

  const termo = busca.trim().toLowerCase()
  const projetosFiltrados = projetos.filter((item) => {
    if (filtroStatus && item.status !== filtroStatus) return false
    if (termo) {
      const nome    = String(item.nome          ?? '').toLowerCase()
      const cliente = String(item.cliente_nome  ?? '').toLowerCase()
      if (!nome.includes(termo) && !cliente.includes(termo)) return false
    }
    return true
  })

  return (
    <View style={[s.container, { backgroundColor: C.background }]}>
      <View style={[s.header, { backgroundColor: C.card, borderBottomColor: C.cardBorder }]}>
        <Text style={[s.titulo, { color: C.text }]}>Projetos</Text>
        <Text style={[s.sub, { color: C.muted }]}>
          {projetosFiltrados.length} de {projetos.length} projetos
        </Text>

        {/* Filter chips */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={s.chipsRow}
        >
          {CHIPS.map((chip) => {
            const selected = filtroStatus === chip.value
            return (
              <TouchableOpacity
                key={String(chip.value)}
                onPress={() => setFiltroStatus(chip.value)}
                style={[
                  s.chip,
                  selected
                    ? { backgroundColor: C.primary }
                    : { backgroundColor: 'transparent', borderColor: C.cardBorder, borderWidth: 1 },
                ]}
                accessibilityRole="button"
                accessibilityLabel={`Filtrar por ${chip.label}`}
              >
                <Text style={[s.chipTxt, { color: selected ? '#fff' : C.muted }]}>
                  {chip.label}
                </Text>
              </TouchableOpacity>
            )
          })}
        </ScrollView>

        {/* Search bar */}
        <View style={[s.buscaBox, { backgroundColor: C.background, borderColor: C.cardBorder }]}>
          <Feather name="search" size={16} color={C.muted} />
          <TextInput
            style={[s.buscaInput, { color: C.text }]}
            placeholder="Buscar por nome ou cliente"
            placeholderTextColor={C.muted}
            value={busca}
            onChangeText={setBusca}
            autoCapitalize="none"
            autoCorrect={false}
          />
        </View>
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
          data={projetosFiltrados}
          keyExtractor={p => p.id}
          contentContainerStyle={s.lista}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); carregar() }} tintColor={C.primary} />}
          renderItem={({ item }) => (
            <ProjetoCard projeto={item} onPress={() => router.push(`/projeto/${item.id}` as any)} />
          )}
          ListEmptyComponent={<Text style={[s.msg, { color: C.muted }]}>Nenhum projeto encontrado.</Text>}
        />
      )}
    </View>
  )
}

const s = StyleSheet.create({
  container:     { flex: 1 },
  header:        { padding: 20, paddingTop: 56, borderBottomWidth: 0.5, gap: 12 },
  titulo:        { fontSize: 24, fontWeight: '700' },
  sub:           { fontSize: 13 },
  chipsRow:      { flexDirection: 'row', gap: 8, paddingVertical: 2 },
  chip:          { paddingHorizontal: 14, paddingVertical: 7, borderRadius: 20 },
  chipTxt:       { fontSize: 13, fontWeight: '500' },
  buscaBox: {
    minHeight: 48,
    borderRadius: 12,
    borderWidth: 1,
    paddingHorizontal: 14,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  buscaInput:    { flex: 1, fontSize: 14, paddingVertical: 12 },
  lista:         { padding: 14 },
  centro:        { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  msg:           { fontSize: 14, textAlign: 'center', marginTop: 12, lineHeight: 22 },
  btnRetry:      { marginTop: 16, borderWidth: 1, borderRadius: 8, paddingHorizontal: 20, paddingVertical: 14 },
  bannerOffline: { backgroundColor: '#B8860B', paddingVertical: 6, paddingHorizontal: 14 },
  bannerTxt:     { color: '#FFF8DC', fontSize: 12, fontWeight: '500', textAlign: 'center' },
})
