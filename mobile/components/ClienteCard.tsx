import { TouchableOpacity, View, Text, StyleSheet } from 'react-native'
import { Feather } from '@expo/vector-icons'
import { Colors } from '../constants/Colors'

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
  magic_link_token?: string | null
  magic_link_expira?: string | null
}

function obterMetaStatus(status?: string | null) {
  const C = Colors.dark

  switch (status) {
    case 'pendente_formulario':
      return { cor: C.danger, label: 'Formulário pendente' }
    case 'pronto_para_documentar':
      return { cor: C.info, label: 'Pronto para documentar' }
    case 'documentacao_em_andamento':
      return { cor: C.success, label: 'Documentação em andamento' }
    default:
      return { cor: C.muted, label: 'Sem projetos vinculados' }
  }
}

function obterProximaAcao(
  status?: string | null,
  magic_link_expira?: string | null,
) {
  const C = Colors.dark

  if (status === 'pendente_formulario') {
    if (!magic_link_expira) {
      return { texto: 'Enviar formulário', icone: 'send', cor: C.danger }
    }
    const expira = new Date(magic_link_expira)
    if (expira < new Date()) {
      return { texto: 'Link expirado — renovar', icone: 'alert-circle', cor: C.danger }
    }
    return { texto: 'Aguardando preenchimento', icone: 'clock', cor: C.primary }
  }

  if (status === 'pronto_para_documentar') {
    return { texto: 'Gerar documentos', icone: 'file-text', cor: C.info }
  }

  if (status === 'documentacao_em_andamento') {
    return { texto: 'Documentação em andamento', icone: 'check-circle', cor: C.success }
  }

  return { texto: 'Sem projetos', icone: 'user', cor: C.muted }
}

export function ClienteCard({ cliente, onPress }: { cliente: ClienteResumo; onPress: () => void }) {
  const C = Colors.dark
  const status = obterMetaStatus(cliente.status_documentacao)
  const proximaAcao = obterProximaAcao(cliente.status_documentacao, cliente.magic_link_expira)

  return (
    <TouchableOpacity
      style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}
      onPress={onPress}
      activeOpacity={0.8}
      accessibilityRole="button"
      accessibilityLabel={`Cliente ${cliente.nome || 'sem nome'}`}
    >
      <View style={s.topo}>
        <View style={s.topoTexto}>
          <Text style={[s.nome, { color: C.text }]} numberOfLines={1}>
            {cliente.nome || 'Cliente sem nome'}
          </Text>
          <Text style={[s.contato, { color: C.muted }]} numberOfLines={1}>
            {cliente.telefone || cliente.email || cliente.cpf || 'Sem contato cadastrado'}
          </Text>
        </View>
        <Feather name="chevron-right" size={18} color={C.muted} />
      </View>

      <View style={[s.statusBadge, { borderColor: status.cor, backgroundColor: `${status.cor}20` }]}>
        <Text style={[s.statusTexto, { color: status.cor }]}>{status.label}</Text>
      </View>

      <View style={s.metricas}>
        <View style={[s.metrica, { backgroundColor: C.background }]}>
          <Text style={[s.metricaValor, { color: C.primary }]}>{cliente.projetos_total ?? 0}</Text>
          <Text style={[s.metricaLabel, { color: C.muted }]}>Projetos</Text>
        </View>
        <View style={[s.metrica, { backgroundColor: C.background }]}>
          <Text style={[s.metricaValor, { color: C.info }]}>{cliente.documentos_total ?? 0}</Text>
          <Text style={[s.metricaLabel, { color: C.muted }]}>Documentos</Text>
        </View>
        <View style={[s.metrica, { backgroundColor: C.background }]}>
          <Text style={[s.metricaValor, { color: C.success }]}>{cliente.confrontantes_total ?? 0}</Text>
          <Text style={[s.metricaLabel, { color: C.muted }]}>Confront.</Text>
        </View>
      </View>

      <View style={s.proximaAcaoRow}>
        <Feather name={proximaAcao.icone as any} size={12} color={proximaAcao.cor} />
        <Text style={[s.proximaAcaoTexto, { color: proximaAcao.cor }]}>{proximaAcao.texto}</Text>
      </View>
    </TouchableOpacity>
  )
}

const s = StyleSheet.create({
  card: { borderRadius: 12, borderWidth: 0.5, padding: 14, marginBottom: 10, gap: 12 },
  topo: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 },
  topoTexto: { flex: 1, gap: 3 },
  nome: { fontSize: 16, fontWeight: '700' },
  contato: { fontSize: 12 },
  statusBadge: {
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 6,
    alignSelf: 'flex-start',
  },
  statusTexto: { fontSize: 11, fontWeight: '700' },
  metricas: { flexDirection: 'row', gap: 8 },
  metrica: {
    flex: 1,
    borderRadius: 10,
    paddingVertical: 12,
    paddingHorizontal: 10,
    alignItems: 'center',
  },
  metricaValor: { fontSize: 18, fontWeight: '700' },
  metricaLabel: { fontSize: 11, marginTop: 2 },
  proximaAcaoRow: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  proximaAcaoTexto: { fontSize: 11, fontWeight: '600' },
})
