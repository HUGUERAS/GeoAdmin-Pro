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

export function ProjetoCard({ projeto, onPress }: { projeto: Projeto; onPress: () => void }) {
  const C = Colors.dark
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
      {projeto.cliente_nome ? (
        <Text style={[s.cliente, { color: C.muted }]} numberOfLines={1}>{projeto.cliente_nome}</Text>
      ) : null}
      <View style={s.footer}>
        {projeto.municipio ? (
          <Text style={[s.info, { color: C.muted }]}>{projeto.municipio}</Text>
        ) : null}
        <Text style={[s.pontos, { color: C.primary }]}>{projeto.total_pontos ?? 0} pts</Text>
      </View>
    </TouchableOpacity>
  )
}

const s = StyleSheet.create({
  card:   { borderRadius: 10, padding: 14, marginBottom: 8, borderWidth: 0.5 },
  top:    { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  nome:   { fontSize: 15, fontWeight: '600', flex: 1, marginRight: 8 },
  cliente:{ fontSize: 12, marginBottom: 8 },
  footer: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  info:   { fontSize: 12 },
  pontos: { fontSize: 12, fontWeight: '600' },
})
