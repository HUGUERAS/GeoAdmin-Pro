import { View, Text, StyleSheet } from 'react-native'
import { StatusColors, StatusLabels } from '../constants/Colors'

export function StatusBadge({ status }: { status: string }) {
  const cor   = StatusColors[status] || '#888780'
  const label = StatusLabels[status] || status
  return (
    <View style={[s.badge, { backgroundColor: cor + '25', borderColor: cor }]}>
      <Text style={[s.text, { color: cor }]}>{label}</Text>
    </View>
  )
}

const s = StyleSheet.create({
  badge: { borderRadius: 6, borderWidth: 0.5, paddingHorizontal: 8, paddingVertical: 3 },
  text:  { fontSize: 11, fontWeight: '600' },
})
