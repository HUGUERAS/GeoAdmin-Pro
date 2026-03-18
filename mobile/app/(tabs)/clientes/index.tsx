import { View, Text, StyleSheet } from 'react-native'
import { Feather } from '@expo/vector-icons'
import { Colors } from '../../../constants/Colors'

export default function ClientesScreen() {
  const C = Colors.dark
  return (
    <View style={[s.container, { backgroundColor: C.background }]}>
      <View style={[s.header, { backgroundColor: C.card, borderBottomColor: C.cardBorder }]}>
        <Text style={[s.titulo, { color: C.text }]}>Clientes</Text>
      </View>
      <View style={s.centro}>
        <Feather name="users" size={48} color={C.muted} />
        <Text style={[s.msg, { color: C.muted }]}>Gestão de clientes</Text>
        <Text style={[s.sub, { color: C.muted }]}>Em breve</Text>
      </View>
    </View>
  )
}

const s = StyleSheet.create({
  container: { flex: 1 },
  header:    { padding: 20, paddingTop: 56, borderBottomWidth: 0.5 },
  titulo:    { fontSize: 24, fontWeight: '700' },
  centro:    { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12 },
  msg:       { fontSize: 18, fontWeight: '600' },
  sub:       { fontSize: 14 },
})
