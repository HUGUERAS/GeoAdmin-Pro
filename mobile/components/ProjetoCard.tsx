import { TouchableOpacity, View, Text, StyleSheet } from 'react-native'
import { Feather } from '@expo/vector-icons'
import { Colors } from '../constants/Colors'
import { StatusBadge } from './StatusBadge'

type ResumoLotes = {
  total?: number
  sem_participante?: number
  com_geometria?: number
  prontos?: number
  pendentes?: number
}

type Projeto = {
  id: string
  projeto_nome: string
  cliente_nome?: string
  status: string
  total_pontos?: number
  municipio?: string
  resumo_lotes?: ResumoLotes
  areas_total?: number
  lotes_prontos?: number
  lotes_pendentes?: number
}

function metaProjeto(projeto: Projeto) {
  const status = String(projeto.status || '').toLowerCase()
  const resumoLotes = projeto.resumo_lotes
  const totalLotes = resumoLotes?.total ?? projeto.areas_total ?? 0
  const lotesProntos = resumoLotes?.prontos ?? projeto.lotes_prontos ?? 0
  const lotesPendentes = resumoLotes?.pendentes ?? projeto.lotes_pendentes ?? 0
  const semParticipante = resumoLotes?.sem_participante ?? 0

  if (totalLotes > 0) {
    const progresso = totalLotes > 0 ? Math.max(8, Math.min(100, Math.round((lotesProntos / totalLotes) * 100))) : 12
    if (semParticipante > 0) {
      return { progresso, proximaAcao: `Vincular participantes em ${semParticipante} lote(s)`, loteResumo: `${totalLotes} lotes · ${lotesProntos} prontos` }
    }
    if (lotesPendentes > 0) {
      return { progresso, proximaAcao: `Avançar ${lotesPendentes} lote(s) pendentes`, loteResumo: `${totalLotes} lotes · ${lotesProntos} prontos` }
    }
    return { progresso, proximaAcao: 'Conferir lotes prontos e preparar operação em lote', loteResumo: `${totalLotes} lotes em controle` }
  }

  if (!projeto.cliente_nome) {
    return { progresso: 12, proximaAcao: 'Vincular cliente e liberar formulário', loteResumo: 'Sem lotes organizados ainda' }
  }
  if (!projeto.total_pontos) {
    return { progresso: 24, proximaAcao: 'Abrir mapa e lançar o perímetro', loteResumo: 'Base cartográfica pendente' }
  }
  if (status.includes('medicao')) {
    return { progresso: 42, proximaAcao: 'Conferir CAD e organizar área técnica', loteResumo: 'Projeto unitário em campo' }
  }
  if (status.includes('montagem') || status.includes('analise')) {
    return { progresso: 63, proximaAcao: 'Fechar documentação e confrontantes', loteResumo: 'Projeto unitário em escritório' }
  }
  if (status.includes('protocolado')) {
    return { progresso: 82, proximaAcao: 'Acompanhar protocolo e pendências', loteResumo: 'Projeto em andamento' }
  }
  if (status.includes('aprovado') || status.includes('certificado')) {
    return { progresso: 94, proximaAcao: 'Preparar entrega final e bridge Métrica', loteResumo: 'Projeto quase concluído' }
  }
  if (status.includes('final')) {
    return { progresso: 100, proximaAcao: 'Projeto concluído', loteResumo: 'Entrega encerrada' }
  }
  return { progresso: 54, proximaAcao: 'Revisar situação documental', loteResumo: 'Sem leitura por lote' }
}

export function ProjetoCard({ projeto, onPress }: { projeto: Projeto; onPress: () => void }) {
  const C = Colors.dark
  const meta = metaProjeto(projeto)
  const totalLotes = projeto.resumo_lotes?.total ?? projeto.areas_total ?? 0
  const lotesPendentes = projeto.resumo_lotes?.pendentes ?? projeto.lotes_pendentes ?? 0

  return (
    <TouchableOpacity
      style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}
      onPress={onPress}
      activeOpacity={0.7}
      accessibilityRole="button"
      accessibilityLabel={`Projeto ${projeto.projeto_nome}`}
    >
      <View style={[s.rail, { backgroundColor: lotesPendentes > 0 ? C.warning : C.primary }]} />
      <View style={s.body}>
        <View style={s.top}>
          <View style={s.titleGroup}>
            <Text style={[s.nome, { color: C.text }]} numberOfLines={1}>{projeto.projeto_nome}</Text>
            <Text style={[s.cliente, { color: C.muted }]} numberOfLines={1}>
              {projeto.cliente_nome || 'Cliente principal pendente'}
            </Text>
          </View>
          <StatusBadge status={projeto.status} />
        </View>

        <View style={s.progressWrap}>
          <View style={[s.progressTrack, { backgroundColor: C.line }]}>
            <View style={[s.progressFill, { backgroundColor: C.primary, width: `${meta.progresso}%` }]} />
          </View>
          <Text style={[s.progressTxt, { color: C.primary }]}>{meta.progresso}%</Text>
        </View>

        <View style={[s.actionBox, { backgroundColor: C.surfaceAlt, borderColor: C.line }]}>
          <Feather name="target" size={14} color={C.primary} />
          <Text style={[s.acao, { color: C.text }]} numberOfLines={2}>{meta.proximaAcao}</Text>
        </View>

        <View style={s.footer}>
          <View style={s.metaItem}>
            <Feather name="map-pin" size={13} color={C.muted} />
            <Text style={[s.info, { color: C.muted }]} numberOfLines={1}>{projeto.municipio || 'Município pendente'}</Text>
          </View>
          <View style={s.metaItem}>
            <Feather name={totalLotes > 0 ? 'layers' : 'crosshair'} size={13} color={totalLotes > 0 && lotesPendentes === 0 ? C.success : C.primary} />
            <Text style={[s.pontos, { color: totalLotes > 0 && lotesPendentes === 0 ? C.success : C.primary }]} numberOfLines={1}>
              {totalLotes > 0 ? `${totalLotes} lotes` : `${projeto.total_pontos ?? 0} pts`}
            </Text>
          </View>
        </View>
        <Text style={[s.loteResumo, { color: C.muted }]} numberOfLines={1}>{meta.loteResumo}</Text>
      </View>
    </TouchableOpacity>
  )
}

const s = StyleSheet.create({
  card: { borderRadius: 10, marginHorizontal: 16, marginBottom: 10, borderWidth: 1, overflow: 'hidden', flexDirection: 'row' },
  rail: { width: 4 },
  body: { flex: 1, padding: 14, gap: 10 },
  top: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
  titleGroup: { flex: 1, gap: 3 },
  nome: { fontSize: 15, fontWeight: '800', flex: 1 },
  cliente: { fontSize: 12 },
  progressWrap: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  progressTrack: { flex: 1, height: 6, borderRadius: 6, overflow: 'hidden' },
  progressFill: { height: '100%', borderRadius: 6 },
  progressTxt: { fontSize: 12, fontWeight: '700', minWidth: 36, textAlign: 'right' },
  actionBox: { borderWidth: 1, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 9, flexDirection: 'row', gap: 8, alignItems: 'flex-start' },
  acao: { flex: 1, fontSize: 12, lineHeight: 18, fontWeight: '700' },
  loteResumo: { fontSize: 12 },
  footer: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  metaItem: { flexDirection: 'row', alignItems: 'center', gap: 5, maxWidth: '52%' },
  info: { fontSize: 12, flexShrink: 1 },
  pontos: { fontSize: 12, fontWeight: '700' },
})
