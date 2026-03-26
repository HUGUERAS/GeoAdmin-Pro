import { useState, useCallback } from 'react'
import {
  View,
  Text,
  FlatList,
  RefreshControl,
  StyleSheet,
  ActivityIndicator,
  TouchableOpacity,
  TextInput,
} from 'react-native'
import { useRouter } from 'expo-router'
import { Feather } from '@expo/vector-icons'
import { useFocusEffect } from '@react-navigation/native'
import { Colors } from '../../../constants/Colors'
import { apiGet } from '../../../lib/api'
import { ClienteCard } from '../../../components/ClienteCard'

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
  const router = useRouter()
  const [clientes, setClientes] = useState<ClienteResumo[]>([])
  const [busca, setBusca] = useState('')
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [erro, setErro] = useState('')

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
  const clientesFiltrados = clientes.filter((cliente) => {
    if (!termo) return true

    return [cliente.nome, cliente.telefone, cliente.email, cliente.cpf]
      .filter(Boolean)
      .some((valor) => String(valor).toLowerCase().includes(termo))
  })
  const totalVisiveis = clientesFiltrados.length

  return (
    <View style={[s.container, { backgroundColor: C.background }]}>
      <View style={[s.header, { backgroundColor: C.card, borderBottomColor: C.cardBorder }]}>
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
                {busca.trim() ? 'Nenhum cliente encontrado' : 'Nenhum cliente cadastrado'}
              </Text>
              <Text style={[s.emptySub, { color: C.muted }]}>
                {busca.trim()
                  ? 'Tente ajustar a busca, limpar o filtro ou puxar para atualizar.'
                  : 'Quando houver clientes vinculados aos projetos, eles aparecerao aqui com status documental.'}
              </Text>
              {busca.trim() ? (
                <TouchableOpacity
                  onPress={() => setBusca('')}
                  style={[s.btnRetry, { borderColor: C.info, marginTop: 6 }]}
                  accessibilityRole="button"
                  accessibilityLabel="Limpar busca de clientes"
                >
                  <Text style={{ color: C.info, fontWeight: '600' }}>Limpar busca</Text>
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
  header: { padding: 20, paddingTop: 56, borderBottomWidth: 0.5, gap: 12 },
  titulo: { fontSize: 24, fontWeight: '700' },
  sub: { fontSize: 13 },
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
