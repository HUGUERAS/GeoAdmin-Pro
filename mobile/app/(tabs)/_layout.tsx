import { Tabs } from 'expo-router';

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        sceneStyle: { backgroundColor: '#0b0b0b' },
        tabBarStyle: {
          backgroundColor: '#111111',
          borderTopColor: '#1f1f1f',
        },
        tabBarActiveTintColor: '#FFFFFF',
        tabBarInactiveTintColor: '#8A8A8A',
      }}>
      <Tabs.Screen name="projeto" options={{ title: 'Projeto' }} />
      <Tabs.Screen name="mapa" options={{ title: 'Mapa' }} />
      <Tabs.Screen name="calculos" options={{ title: 'Cálculos' }} />
      <Tabs.Screen name="clientes" options={{ title: 'Clientes' }} />
    </Tabs>
  );
}
