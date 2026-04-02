/**
 * mobile/app/bluetooth.web.tsx
 * Stub web — Bluetooth clássico não está disponível no navegador.
 * Metro resolve este arquivo automaticamente na plataforma web.
 */
import { View, Text, StyleSheet } from 'react-native'
import { Colors } from '../constants/Colors'

export default function BluetoothWebScreen() {
  const C = Colors.dark
  return (
    <View style={[s.container, { backgroundColor: C.background }]}>
      <Text style={[s.icone, { color: C.muted }]}>📡</Text>
      <Text style={[s.titulo, { color: C.text }]}>Bluetooth não disponível</Text>
      <Text style={[s.sub, { color: C.muted }]}>
        A coleta GNSS via Bluetooth requer o aplicativo Android instalado via APK.
        No navegador, use a aba Projetos para acessar os dados coletados em campo.
      </Text>
    </View>
  )
}

const s = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32 },
  icone: { fontSize: 48, marginBottom: 16 },
  titulo: { fontSize: 20, fontWeight: '700', marginBottom: 8, textAlign: 'center' },
  sub: { fontSize: 14, lineHeight: 22, textAlign: 'center' },
})
