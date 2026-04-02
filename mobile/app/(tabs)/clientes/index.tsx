import { useMemo, useState, useCallback, useEffect } from 'react'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import {
  View,
  Text,
  FlatList,
  RefreshControl,
  StyleSheet,
  ActivityIndicator,
  TouchableOpacity,
  TextInput,
  ScrollView,
} from 'react-native'
import { useRouter } from 'expo-router'
import { Feather } from '@expo/vector-icons'
import { useFocusEffect } from '@react-navigation/native'
import { Colors } from '../../../constants/Colors'
import { apiGet } from '../../../lib/api'
import { ClienteCard } from '../../../components/ClienteCard'

const FILTROS = [
  { label: 'Todos', valor: null },
  { label: 'Formulario', valor: 'pendente_formulario' },
  { label: 'Pronto p/ docs', valor: 'pronto_para_documentar' },
  { label: 'Em andamento', valor: 'documentacao_em_andamento' },
] as const

type ClienteResumo = {
  id: string
  nome?: string | null
  telefone?: string | null
  email?: string | null
  cpf?: string | null
  projetos_total?: number
  documentos_total?: number
  confrontantes_total?: number
  status_documentacao?: string | null
  formulario_em?: string | null
  ultimo_documento_em?: string | null
}

type ClientesResponse = {
  total: number
  clientes: ClienteResumo[]
}

export default function ClientesScreen() {
  const C = Colors.dark
  const insets = useSafeAreaInsets()
  const [topInset, setTopInset] = useState(0)
  useEffect(() => { setTopInset(insets.top) }, [insets.top])
  const router = useRouter()
  const [clientes, setClientes] = useState<ClienteResumo[]>([])
  const [busca, setBusca] = useState('')
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [erro, setErro] = useState('')
  const [filtroStatus, setFiltroStatus] = useState<string | null>(null)

  const carregar = async () => {
    try {
      setErro('')
      const data = await apiGet<ClientesResponse>('/clientes')
      setClientes(data.clientes || [])
    } catch (e: any) {
      setErro(e?.message ?? 'Nao foi possivel carregar os clientes.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useFocusEffect(useCallback(() => { carregar() }, []))

  const termo = busca.trim().toLowerCase()
  const clientesFiltrados = useMemo(() => clientes.filter((cliente) => {
    if (filtroStatus && cliente.status_documentacao !== filtroStatus) return false
    if (!termo) return true

    return [cliente.nome, cliente.telefone, cliente.email, cliente.cpf]
      .filter(Boolean)
      .some((valor) => String(valor).toLowerCase().includes(termo))
  }), [clientes, filtroStatus, termo])

  const totalVisiveis = clientesFiltrados.length
  const pendentesFormulario = clientes.filter((item) => item.status_documentacao === 'pendente_formulario').length
  const prontosDocs = clientes.filter((item) => item.status_documentacao === 'pronto_para_documentar').length
  const emAndamento = clientes.filter((item) => item.status_documentacao === 'documentacao_em_andamento').length
  const resumoOperacional = pendentesFormulario > 0
    ? `${pendentesFormulario} cliente(s) ainda aguardam formulário.`
    : prontosDocs > 0
      ? `${prontosDocs} cliente(s) já podem avançar para documentos.`
      : emAndamento > 0
        ? `${emAndamento} cliente(s) estão com documentação em andamento.`
        : 'Use esta aba para saber quem precisa de formulário, confrontantes ou documentação.'

  return (
    <View style={[s.container, { backgroundColor: C.background }]}>
      <View style={[s.header, { backgroundColor: C.card, borderBottomColor: C.cardBorder, paddingTop: Math.max(topInset + 12, 20) }]}>
        <Text style={[s.titulo, { color: C.text }]}>Clientes & Documentacao</Text>
        <Text style={[s.sub, { color: C.muted }]}>
          {totalVisiveis} de {clientes.length} clientes visiveis
        </Text>

        <View style={[s.buscaBox, { backgroundColor: C.background, borderColor: C.cardBorder }]}>
          <Feather name="search" size={16} color={C.muted} />
          <TextInput
            style={[s.buscaInput, { color: C.text }]}
            placeholder="Buscar por nome, telefone, email ou CPF"
            placeholderTextColor={C.muted}
            value={busca}
            onChangeText={setBusca}
            autoCapitalize="none"
            autoCorrect={false}
          />
        </View>

        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={s.filtrosRow}>
          {FILTROS.map((filtro) => {
            const ativo = filtroStatus === filtro.valor
            return (
              <TouchableOpacity
                key={String(filtro.valor)}
                onPress={() => setFiltroStatus(filtro.valor)}
                style={[
                  s.filtroChip,
                  ativo
                    ? { backgroundColor: C.primary, borderColor: C.primary }
                    : { backgroundColor: 'transparent', borderColor: C.cardBorder },
                ]}
              >
                <Text style={{ color: ativo ? C.primaryText : C.muted, fontWeight: '700', fontSize: 12 }}>{filtro.label}</Text>
              </TouchableOpacity>
            )
          })}
        </ScrollView>
      </View>

      <View style={[s.resumoDia, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
        <Text style={[s.resumoDiaTitulo, { color: C.text }]}>Painel de hoje</Text>
        <Text style={[s.resumoDiaTexto, { color: C.text }]}>{resumoOperacional}</Text>
        <Text style={[s.resumoDiaSub, { color: C.muted }]}>Pendentes: {pendentesFormulario} · Prontos: {prontosDocs} · Em andamento: {emAndamento}</Text>
      </View>

      {loading && !refreshing ? (
        <View style={s.centro}>
          <ActivityIndicator color={C.primary} size="large" />
          <Text style={[s.msg, { color: C.muted }]}>Carregando clientes...</Text>
        </View>
      ) : erro ? (
        <View style={s.centro}>
          <Text style={[s.msg, { color: C.danger }]}>{erro}</Text>
          <TouchableOpacity
            onPress={carregar}
            style={[s.btnRetry, { borderColor: C.primary }]}
            accessibilityRole="button"
            accessibilityLabel="Tentar carregar clientes novamente"
          >
            <Text style={{ color: C.primary, fontWeight: '600' }}>Tentar novamente</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={clientesFiltrados}
          keyExtractor={(cliente) => cliente.id}
          contentContainerStyle={s.lista}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => {
                setRefreshing(true)
                carregar()
              }}
              tintColor={C.primary}
            />
          }
          renderItem={({ item }) => (
            <ClienteCard
              cliente={item}
              onPress={() => router.push(`/clientes/${item.id}` as any)}
            />
          )}
          ListEmptyComponent={
            <View style={s.emptyBox}>
              <Text style={[s.emptyTitulo, { color: C.text }]}> 
                {busca.trim() || filtroStatus ? 'Nenhum cliente encontrado' : 'Nenhum cliente cadastrado'}
              </Text>
              <Text style={[s.emptySub, { color: C.muted }]}> 
                {busca.trim() || filtroStatus
                  ? 'Tente ajustar a busca, limpar o filtro ou puxar para atualizar.'
                  : 'Quando houver clientes vinculados aos projetos, eles aparecerao aqui com status documental.'}
              </Text>
              {busca.trim() || filtroStatus ? (
                <TouchableOpacity
                  onPress={() => {
                    setBusca('')
                    setFiltroStatus(null)
                  }}
                  style={[s.btnRetry, { borderColor: C.info, marginTop: 6 }]}
                  accessibilityRole="button"
                  accessibilityLabel="Limpar filtros de clientes"
                >
                  <Text style={{ color: C.info, fontWeight: '600' }}>Limpar filtros</Text>
                </TouchableOpacity>
              ) : null}
            </View>
          }
        />
      )}
    </View>
  )
}

const s = StyleSheet.create({
  container: { flex: 1 },
  header: { padding: 20, borderBottomWidth: 0.5, gap: 12 },
  titulo: { fontSize: 24, fontWeight: '700' },
  sub: { fontSize: 13 },
  filtrosRow: { flexDirection: 'row', gap: 8, paddingVertical: 2 },
  filtroChip: {
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  resumoDia: { marginHorizontal: 14, marginTop: 14, borderWidth: 0.5, borderRadius: 12, padding: 14, gap: 4 },
  resumoDiaTitulo: { fontSize: 12, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.6 },
  resumoDiaTexto: { fontSize: 15, fontWeight: '700', lineHeight: 22 },
  resumoDiaSub: { fontSize: 12, lineHeight: 18 },
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
  lista: { padding: 14, paddingBottom: 24 },
  centro: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  msg: { fontSize: 14, textAlign: 'center', marginTop: 12, lineHeight: 22 },
  btnRetry: { marginTop: 16, borderWidth: 1, borderRadius: 8, paddingHorizontal: 20, paddingVertical: 14 },
  emptyBox: {
    marginTop: 40,
    padding: 20,
    borderRadius: 12,
    alignItems: 'center',
    gap: 8,
  },
  emptyTitulo: { fontSize: 16, fontWeight: '700' },
  emptySub: { fontSize: 13, textAlign: 'center', lineHeight: 20 },
})
