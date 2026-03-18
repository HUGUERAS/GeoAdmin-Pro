import { View, Text, ScrollView, StyleSheet } from 'react-native'
import { useRouter } from 'expo-router'
import { Feather } from '@expo/vector-icons'
import { Colors } from '../../../constants/Colors'
import { FerramentaBtn } from '../../../components/FerramentaBtn'

const FERRAMENTAS = [
  { id: 'inverso',    label: 'Inverso',    icone: 'arrow-right',      rota: '/calculos/inverso' },
  { id: 'area',       label: 'Área',       icone: 'square',           rota: null },
  { id: 'subdivisao', label: 'Subdivisão', icone: 'scissors',         rota: null },
  { id: 'conversao',  label: 'Conversão',  icone: 'refresh-cw',       rota: null },
  { id: 'deflexao',   label: 'Deflexão',   icone: 'corner-down-right',rota: null },
  { id: 'intersecao', label: 'Interseção', icone: 'git-merge',        rota: null },
  { id: 'distancia',  label: 'Dist. P-L',  icone: 'move',             rota: null },
  { id: 'rotacao',    label: 'Rotação',    icone: 'rotate-cw',        rota: null },
  { id: 'media',      label: 'Média Pts',  icone: 'target',           rota: null },
  { id: 'irradiacao', label: 'Irradiação', icone: 'navigation',       rota: null },
  { id: 'angular',    label: 'Angular',    icone: 'activity',         rota: null },
  { id: 'mais',       label: '+ Mais',     icone: 'grid',             rota: null },
]

export default function CalculosScreen() {
  const C = Colors.dark
  const router = useRouter()
  const rows = []
  for (let i = 0; i < FERRAMENTAS.length; i += 3) rows.push(FERRAMENTAS.slice(i, i + 3))

  return (
    <View style={[s.container, { backgroundColor: C.background }]}>
      <View style={[s.header, { backgroundColor: C.card, borderBottomColor: C.cardBorder }]}>
        <Text style={[s.titulo, { color: C.text }]}>Ferramentas</Text>
        <Text style={[s.sub, { color: C.muted }]}>Laranja = disponível</Text>
      </View>
      <ScrollView contentContainerStyle={s.grid}>
        {rows.map((row, ri) => (
          <View key={ri} style={s.row}>
            {row.map(f => (
              <FerramentaBtn
                key={f.id}
                label={f.label}
                icone={<Feather name={f.icone as any} size={22} color={f.rota ? C.primary : C.muted} />}
                ativo={!!f.rota}
                onPress={() => { if (f.rota) router.push(f.rota as any) }}
              />
            ))}
          </View>
        ))}
      </ScrollView>
    </View>
  )
}

const s = StyleSheet.create({
  container: { flex: 1 },
  header:    { padding: 20, paddingTop: 56, borderBottomWidth: 0.5 },
  titulo:    { fontSize: 24, fontWeight: '700' },
  sub:       { fontSize: 12, marginTop: 2 },
  grid:      { padding: 10 },
  row:       { flexDirection: 'row' },
})
