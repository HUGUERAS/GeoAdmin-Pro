import { TouchableOpacity, View, Text, StyleSheet } from 'react-native'
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
      <View style={s.top}>
        <Text style={[s.nome, { color: C.text }]} numberOfLines={1}>{projeto.projeto_nome}</Text>
        <StatusBadge status={projeto.status} />
      </View>

      <Text style={[s.cliente, { color: C.muted }]} numberOfLines={1}>
        {projeto.cliente_nome || 'Sem cliente principal vinculado'}
      </Text>

      <View style={s.progressWrap}>
        <View style={[s.progressTrack, { backgroundColor: C.cardBorder }]}>
          <View style={[s.progressFill, { backgroundColor: C.primary, width: `${meta.progresso}%` }]} />
        </View>
        <Text style={[s.progressTxt, { color: C.primary }]}>{meta.progresso}%</Text>
      </View>

      <Text style={[s.acao, { color: C.text }]} numberOfLines={2}>Próxima ação: {meta.proximaAcao}</Text>
      <Text style={[s.loteResumo, { color: C.muted }]} numberOfLines={1}>{meta.loteResumo}</Text>

      <View style={s.footer}>
        <Text style={[s.info, { color: C.muted }]}>{projeto.municipio || 'Município pendente'}</Text>
        {totalLotes > 0 ? (
          <Text style={[s.pontos, { color: lotesPendentes > 0 ? C.primary : C.success }]}>{totalLotes} lotes</Text>
        ) : (
          <Text style={[s.pontos, { color: C.primary }]}>{projeto.total_pontos ?? 0} pts</Text>
        )}
      </View>
    </TouchableOpacity>
  )
}

const s = StyleSheet.create({
  card: { borderRadius: 14, padding: 14, marginBottom: 10, borderWidth: 0.5, gap: 8 },
  top: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
  nome: { fontSize: 15, fontWeight: '700', flex: 1 },
  cliente: { fontSize: 12 },
  progressWrap: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  progressTrack: { flex: 1, height: 8, borderRadius: 999, overflow: 'hidden' },
  progressFill: { height: '100%', borderRadius: 999 },
  progressTxt: { fontSize: 12, fontWeight: '700', minWidth: 36, textAlign: 'right' },
  acao: { fontSize: 12, lineHeight: 18, fontWeight: '600' },
  loteResumo: { fontSize: 12 },
  footer: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  info: { fontSize: 12 },
  pontos: { fontSize: 12, fontWeight: '700' },
})
