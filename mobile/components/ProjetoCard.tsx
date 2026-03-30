import { TouchableOpacity, View, Text, StyleSheet } from 'react-native'
import { Colors } from '../constants/Colors'
import { StatusBadge } from './StatusBadge'

type Projeto = {
  id: string
  projeto_nome: string
  cliente_nome?: string
  status: string
  total_pontos?: number
  municipio?: string
}

function metaProjeto(projeto: Projeto) {
  const status = String(projeto.status || '').toLowerCase()
  if (!projeto.cliente_nome) {
    return { progresso: 12, proximaAcao: 'Vincular cliente e liberar formulário' }
  }
  if (!projeto.total_pontos) {
    return { progresso: 24, proximaAcao: 'Abrir mapa e lançar o perímetro' }
  }
  if (status.includes('medicao')) {
    return { progresso: 42, proximaAcao: 'Conferir CAD e organizar área técnica' }
  }
  if (status.includes('montagem') || status.includes('analise')) {
    return { progresso: 63, proximaAcao: 'Fechar documentação e confrontantes' }
  }
  if (status.includes('protocolado')) {
    return { progresso: 82, proximaAcao: 'Acompanhar protocolo e pendências' }
  }
  if (status.includes('aprovado') || status.includes('certificado')) {
    return { progresso: 94, proximaAcao: 'Preparar entrega final e bridge Métrica' }
  }
  if (status.includes('final')) {
    return { progresso: 100, proximaAcao: 'Projeto concluído' }
  }
  return { progresso: 54, proximaAcao: 'Revisar situação documental' }
}

export function ProjetoCard({ projeto, onPress }: { projeto: Projeto; onPress: () => void }) {
  const C = Colors.dark
  const meta = metaProjeto(projeto)
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

      <View style={s.footer}>
        <Text style={[s.info, { color: C.muted }]}>{projeto.municipio || 'Município pendente'}</Text>
        <Text style={[s.pontos, { color: C.primary }]}>{projeto.total_pontos ?? 0} pts</Text>
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
  footer: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  info: { fontSize: 12 },
  pontos: { fontSize: 12, fontWeight: '700' },
})
