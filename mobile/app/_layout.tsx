import { useEffect, useState } from 'react'
import { Stack } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { Colors } from '../constants/Colors'
import { initDB } from '../lib/db'
import * as Font from 'expo-font'
import {
  Feather,
  MaterialIcons,
  MaterialCommunityIcons,
  Ionicons,
  FontAwesome,
  FontAwesome5,
} from '@expo/vector-icons'

export default function RootLayout() {
  const C = Colors.dark
  const [fontsLoaded, setFontsLoaded] = useState(false)

  useEffect(() => {
    initDB().catch(console.error)
    Font.loadAsync({
      ...Feather.font,
      ...MaterialIcons.font,
      ...MaterialCommunityIcons.font,
      ...Ionicons.font,
      ...FontAwesome.font,
      ...FontAwesome5.font,
    })
      .catch(() => {})
      .finally(() => setFontsLoaded(true))
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
