import { TouchableOpacity, View, Text, StyleSheet } from 'react-native'
import { Colors } from '../constants/Colors'

export function FerramentaBtn({
  icone, label, onPress, ativo,
}: {
  icone: React.ReactNode; label: string; onPress: () => void; ativo?: boolean
}) {
  const C = Colors.dark
  return (
    <TouchableOpacity
      style={[s.btn, { borderColor: ativo ? C.primary : C.cardBorder, backgroundColor: C.card }]}
      onPress={onPress}
      activeOpacity={0.7}
      accessibilityRole="button"
      accessibilityLabel={label}
    >
      <View style={s.icone}>{icone}</View>
      <Text style={[s.label, { color: ativo ? C.primary : C.muted }]} numberOfLines={2}>{label}</Text>
    </TouchableOpacity>
  )
}

const s = StyleSheet.create({
  btn:   { borderRadius: 10, borderWidth: 0.5, padding: 12, alignItems: 'center', justifyContent: 'center', minHeight: 80, flex: 1, margin: 4 },
  icone: { marginBottom: 6 },
  label: { fontSize: 12, fontWeight: '500', textAlign: 'center' },
})
