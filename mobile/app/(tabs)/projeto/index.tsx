import { useState, useCallback, useMemo, useEffect } from 'react'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
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

function metaDashboard(projetos: any[]) {
  const resumoLotes = projetos.reduce((acc, item) => {
    const resumo = item.resumo_lotes || {}
    acc.total += Number(resumo.total || item.areas_total || 0)
    acc.prontos += Number(resumo.prontos || item.lotes_prontos || 0)
    acc.pendentes += Number(resumo.pendentes || item.lotes_pendentes || 0)
    acc.semParticipante += Number(resumo.sem_participante || 0)
    acc.comGeometria += Number(resumo.com_geometria || 0)
    return acc
  }, { total: 0, prontos: 0, pendentes: 0, semParticipante: 0, comGeometria: 0 })

  const aguardandoCliente = resumoLotes.total > 0
    ? resumoLotes.semParticipante
    : projetos.filter((item) => !item.cliente_nome).length
  const emCampo = resumoLotes.total > 0
    ? Math.max(resumoLotes.total - resumoLotes.comGeometria, 0)
    : projetos.filter((item) => !item.total_pontos || item.status === 'medicao').length
  const prontosDocumental = resumoLotes.total > 0
    ? resumoLotes.prontos
    : projetos.filter((item) => (item.total_pontos ?? 0) > 0 && Boolean(item.cliente_nome)).length
  const concluidos = projetos.filter((item) => {
    const status = String(item.status || '').toLowerCase()
    return status.includes('aprovado') || status.includes('final') || status.includes('certificado')
  }).length
  return [
    { label: resumoLotes.total > 0 ? 'Lotes em campo' : 'Em campo', valor: emCampo, cor: Colors.dark.info, icone: 'map-pin' },
    { label: resumoLotes.total > 0 ? 'Sem participante' : 'Sem cliente', valor: aguardandoCliente, cor: Colors.dark.danger, icone: 'alert-circle' },
    { label: resumoLotes.total > 0 ? 'Lotes prontos' : 'Prontos p/ docs', valor: prontosDocumental, cor: Colors.dark.success, icone: 'file-text' },
    { label: 'Concluídos', valor: concluidos, cor: Colors.dark.primary, icone: 'check-circle' },
  ]
}

export default function ProjetosScreen() {
  const C = Colors.dark
  const insets = useSafeAreaInsets()
  const router = useRouter()
  const [projetos, setProjetos]     = useState<any[]>([])
  const [loading, setLoading]       = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [erro, setErro]             = useState('')
  const [offline, setOffline]       = useState(false)
  const [filtroStatus, setFiltroStatus] = useState<string | null>(null)
  const [busca, setBusca]           = useState('')
  // topInset starts at 0 matching the static HTML; updated after hydration
  const [topInset, setTopInset]     = useState(0)

  useEffect(() => {
    setTopInset(insets.top)
  }, [insets.top])

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
  const projetosFiltrados = useMemo(() => projetos.filter((item) => {
    if (filtroStatus && item.status !== filtroStatus) return false
    if (termo) {
      const nome    = String(item.nome ?? item.projeto_nome ?? '').toLowerCase()
      const cliente = String(item.cliente_nome ?? '').toLowerCase()
      if (!nome.includes(termo) && !cliente.includes(termo)) return false
    }
    return true
  }), [busca, filtroStatus, projetos, termo])

  const cardsMeta = useMemo(() => metaDashboard(projetos), [projetos])

  return (
    <View style={[s.container, { backgroundColor: C.background }]}>
      <FlatList
        data={projetosFiltrados}
        keyExtractor={p => p.id}
        contentContainerStyle={s.lista}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); carregar() }} tintColor={C.primary} />}
        renderItem={({ item }) => (
          <ProjetoCard projeto={item} onPress={() => router.push(`/projeto/${item.id}` as any)} />
        )}
        ListHeaderComponent={
          <>
            <View style={[s.header, { backgroundColor: C.card, borderBottomColor: C.cardBorder, paddingTop: Math.max(topInset + 12, 20) }]}>
              <View style={s.topRow}>
                <View style={{ flex: 1 }}>
                  <Text style={[s.titulo, { color: C.text }]}>Projetos</Text>
                  <Text style={[s.sub, { color: C.muted }]}>Painel de campo, documentação e operação por lote</Text>
                </View>
                <TouchableOpacity style={[s.novoBtn, { borderColor: C.primary }]} onPress={() => router.push('/projeto/novo' as any)} accessibilityRole="button" accessibilityLabel="Criar novo projeto">
                  <Feather name="plus" size={16} color={C.primary} />
                  <Text style={[s.novoBtnTxt, { color: C.primary }]}>Novo</Text>
                </TouchableOpacity>
              </View>

              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={s.metricasRow}>
                {cardsMeta.map((item) => (
                  <View key={item.label} style={[s.metaCard, { backgroundColor: C.background, borderColor: C.cardBorder }]}>
                    <View style={s.metaIconRow}>
                      <View style={[s.metaIcon, { backgroundColor: `${item.cor}18` }]}>
                        <Feather name={item.icone as any} size={16} color={item.cor} />
                      </View>
                      <Text style={[s.metaValor, { color: C.text }]}>{item.valor}</Text>
                    </View>
                    <Text style={[s.metaLabel, { color: C.muted }]}>{item.label}</Text>
                  </View>
                ))}
              </ScrollView>

              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={s.chipsRow}>
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
                      <Text style={[s.chipTxt, { color: selected ? '#fff' : C.muted }]}>{chip.label}</Text>
                    </TouchableOpacity>
                  )
                })}
              </ScrollView>

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
                <Text style={s.bannerTxt}>Offline — exibindo dados em cache</Text>
              </View>
            )}

            {loading && !refreshing ? (
              <View style={s.centro}>
                <ActivityIndicator color={C.primary} size="large" />
                <Text style={[s.msg, { color: C.muted }]}>Carregando...</Text>
              </View>
            ) : null}

            {!loading && erro ? (
              <View style={s.centro}>
                <Text style={[s.msg, { color: C.danger }]}>{erro}</Text>
                <TouchableOpacity onPress={carregar} style={[s.btnRetry, { borderColor: C.primary }]} accessibilityRole="button" accessibilityLabel="Tentar novamente">
                  <Text style={{ color: C.primary, fontWeight: '600' }}>Tentar novamente</Text>
                </TouchableOpacity>
              </View>
            ) : null}
          </>
        }
        ListEmptyComponent={!loading && !erro ? <Text style={[s.msg, { color: C.muted }]}>Nenhum projeto encontrado.</Text> : null}
      />
    </View>
  )
}

const s = StyleSheet.create({
  container: { flex: 1 },
  header: { padding: 20, borderBottomWidth: 0.5, gap: 14, marginBottom: 8 },
  topRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  titulo: { fontSize: 28, fontWeight: '700' },
  sub: { fontSize: 13, lineHeight: 20 },
  novoBtn: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 12, paddingVertical: 10, flexDirection: 'row', alignItems: 'center', gap: 6 },
  novoBtnTxt: { fontSize: 13, fontWeight: '700' },
  metricasRow: { flexDirection: 'row', gap: 10 },
  metaCard: { minWidth: 148, borderWidth: 1, borderRadius: 14, padding: 12, gap: 8 },
  metaIconRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  metaIcon: { width: 30, height: 30, borderRadius: 999, alignItems: 'center', justifyContent: 'center' },
  metaValor: { fontSize: 22, fontWeight: '700' },
  metaLabel: { fontSize: 12, fontWeight: '500' },
  chipsRow: { flexDirection: 'row', gap: 8, paddingVertical: 2 },
  chip: { paddingHorizontal: 14, paddingVertical: 7, borderRadius: 20 },
  chipTxt: { fontSize: 13, fontWeight: '500' },
  buscaBox: {
    minHeight: 48,
    borderRadius: 12,
    borderWidth: 1,
    paddingHorizontal: 14,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  buscaInput: { flex: 1, fontSize: 14, paddingVertical: 12 },
  lista: { paddingBottom: 28 },
  centro: { alignItems: 'center', justifyContent: 'center', padding: 24 },
  msg: { fontSize: 14, textAlign: 'center', marginTop: 12, lineHeight: 22, paddingHorizontal: 18 },
  btnRetry: { marginTop: 16, borderWidth: 1, borderRadius: 8, paddingHorizontal: 20, paddingVertical: 14 },
  bannerOffline: { backgroundColor: '#B8860B', paddingVertical: 6, paddingHorizontal: 14, marginBottom: 8 },
  bannerTxt: { color: '#FFF8DC', fontSize: 12, fontWeight: '500', textAlign: 'center' },
})
