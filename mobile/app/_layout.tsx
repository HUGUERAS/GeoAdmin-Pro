import { useEffect } from 'react'
import { Stack } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { Colors } from '../constants/Colors'
import { initDB } from '../lib/db'

export default function RootLayout() {
  const C = Colors.dark

  useEffect(() => {
    initDB().catch(console.error)
  }, [])

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
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      </Stack>
    </>
  )
}
