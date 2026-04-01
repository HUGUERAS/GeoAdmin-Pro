import { useEffect, useState } from 'react'
import { Stack, useRouter, useSegments } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { Colors } from '../constants/Colors'
import { initDB } from '../lib/db'
import { carregarSessao } from '../lib/auth'

export default function RootLayout() {
  const C = Colors.dark
  const router = useRouter()
  const segments = useSegments()
  const [pronto, setPronto] = useState(false)

  useEffect(() => {
    async function inicializar() {
      await initDB().catch(console.error)

      const sessao = await carregarSessao()
      const naTelaLogin = segments[0] === 'login'

      if (!sessao && !naTelaLogin) {
        router.replace('/login')
      } else if (sessao && naTelaLogin) {
        router.replace('/(tabs)/projeto')
      }
      setPronto(true)
    }
    inicializar()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (!pronto) return null

  return (
    <>
      <StatusBar style="light" backgroundColor={C.background} />
      <Stack
        screenOptions={{
          headerStyle:      { backgroundColor: C.card },
          headerTintColor:  C.text,
          headerTitleStyle: { fontWeight: '600' },
          contentStyle:     { backgroundColor: C.background },
        }}
      >
        <Stack.Screen name="login" options={{ headerShown: false }} />
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      </Stack>
    </>
  )
}
