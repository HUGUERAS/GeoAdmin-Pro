import { useEffect, useState } from 'react'
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native'
import { useRouter } from 'expo-router'
import { Feather } from '@expo/vector-icons'
import { Colors } from '../../../constants/Colors'
import { initDB, obterUltimoProjetoMapa } from '../../../lib/db'
import { ScreenHeader } from '../../../components/ScreenHeader'

export default function MapaScreen() {
  const C = Colors.dark
  const router = useRouter()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let ativo = true
      ; (async () => {
        await initDB()
        const ultimoProjetoId = await obterUltimoProjetoMapa()
        if (!ativo) return
        if (ultimoProjetoId) {
          router.replace(`/(tabs)/mapa/${ultimoProjetoId}` as any)
          return
        }
        setLoading(false)
      })()
    return () => { ativo = false }
  }, [router])

  if (loading) {
    return (
      <View style={[s.container, s.centro, { backgroundColor: C.background }]}>
        <ActivityIndicator color={C.primary} size="large" />
        <Text style={[s.sub, { color: C.muted }]}>Recuperando último projeto do mapa...</Text>
      </View>
    )
  }

  return (
    <View style={[s.container, { backgroundColor: C.background }]}>
      <ScreenHeader titulo="Mapa / CAD" />
      <View style={s.centro}>
        <Feather name="map" size={48} color={C.muted} />
        <Text style={[s.msg, { color: C.muted }]}>Nenhum projeto recente no mapa</Text>
        <Text style={[s.sub, { color: C.muted }]}>Abra um projeto ou cliente e toque em{`\n`}"Ver no mapa"</Text>
      </View>
    </View>
  )
}

const s = StyleSheet.create({
  container: { flex: 1 },
  header: { padding: 20, borderBottomWidth: 0.5 },
  titulo: { fontSize: 24, fontWeight: '700' },
  centro: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12, paddingHorizontal: 24 },
  msg: { fontSize: 16, fontWeight: '600', textAlign: 'center' },
  sub: { fontSize: 13, textAlign: 'center', lineHeight: 20 },
})
