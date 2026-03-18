import { Stack } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { Colors } from '../constants/Colors'

export default function RootLayout() {
  const C = Colors.dark
  return (
    <>
      <StatusBar style="light" backgroundColor={C.background} />
      <Stack screenOptions={{
        headerStyle:      { backgroundColor: C.card },
        headerTintColor:  C.text,
        headerTitleStyle: { fontWeight: '600' },
        contentStyle:     { backgroundColor: C.background },
      }} />
    </>
  )
}
