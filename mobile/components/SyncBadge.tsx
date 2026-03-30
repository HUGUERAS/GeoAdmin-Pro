/**
 * mobile/components/SyncBadge.tsx
 * Ícone de nuvem com badge mostrando pontos pendentes de sincronização.
 */

import { TouchableOpacity, View, Text, ActivityIndicator, StyleSheet } from 'react-native'
import { Feather } from '@expo/vector-icons'
import { Colors } from '../constants/Colors'

interface Props {
  pendentes: number
  erros?: number
  onPress: () => void
  sincronizando: boolean
}

export function SyncBadge({ pendentes, erros = 0, onPress, sincronizando }: Props) {
  const C = Colors.dark
  const temErro = erros > 0
  const cor = temErro ? C.danger : pendentes > 0 ? C.primary : C.muted
  const total = pendentes + erros
  const label = sincronizando
    ? 'Sincronizando'
    : temErro
      ? `${erros} ponto(s) com erro — toque para retentar`
      : pendentes > 0
        ? `Sincronizar ${pendentes} ponto(s) pendente(s)`
        : 'Sincronizado'

  return (
    <TouchableOpacity
      onPress={onPress}
      style={s.container}
      activeOpacity={0.7}
      accessibilityRole="button"
      accessibilityLabel={label}
    >
      {sincronizando
        ? <ActivityIndicator size="small" color={C.primary} />
        : <Feather name={temErro ? 'cloud-off' : 'cloud'} size={22} color={cor} />
      }
      {total > 0 && !sincronizando && (
        <View style={[s.badge, { backgroundColor: cor }]}>
          <Text style={s.badgeTxt}>{total > 99 ? '99+' : String(total)}</Text>
        </View>
      )}
    </TouchableOpacity>
  )
}

const s = StyleSheet.create({
  container: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badge: {
    position: 'absolute',
    top: 4,
    right: 4,
    minWidth: 16,
    height: 16,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 3,
  },
  badgeTxt: {
    color: '#fff',
    fontSize: 9,
    fontWeight: '700',
  },
})
