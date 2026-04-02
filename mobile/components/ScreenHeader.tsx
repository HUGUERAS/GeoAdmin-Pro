/**
 * mobile/components/ScreenHeader.tsx
 * Header padronizado com safe area automática.
 * Substitui o bloco View+paddingTop:56 repetido em cada tela.
 *
 * Uso simples:
 *   <ScreenHeader titulo="Área" subtitulo="Área e perímetro de polígono UTM" />
 *
 * Uso com ação no canto direito:
 *   <ScreenHeader titulo="Projetos" direita={<BotaoNovo />} />
 */
import { View, Text, StyleSheet } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { Colors } from '../constants/Colors'

interface Props {
  titulo: string
  subtitulo?: string
  /** Elemento renderizado no lado direito do header (ex: botão Novo, SyncBadge) */
  direita?: React.ReactNode
}

export function ScreenHeader({ titulo, subtitulo, direita }: Props) {
  const C = Colors.dark
  const insets = useSafeAreaInsets()
  const paddingTop = Math.max(insets.top + 12, 20)

  return (
    <View
      style={[
        s.header,
        {
          backgroundColor: C.card,
          borderBottomColor: C.cardBorder,
          paddingTop,
        },
      ]}
    >
      <View style={s.row}>
        <View style={s.textos}>
          <Text style={[s.titulo, { color: C.text }]}>{titulo}</Text>
          {subtitulo ? (
            <Text style={[s.sub, { color: C.muted }]}>{subtitulo}</Text>
          ) : null}
        </View>
        {direita ? <View style={s.direitaWrap}>{direita}</View> : null}
      </View>
    </View>
  )
}

const s = StyleSheet.create({
  header: {
    paddingHorizontal: 20,
    paddingBottom: 16,
    borderBottomWidth: 0.5,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  textos: { flex: 1 },
  titulo: { fontSize: 24, fontWeight: '700', lineHeight: 30 },
  sub:    { fontSize: 13, marginTop: 2, lineHeight: 18 },
  direitaWrap: { flexShrink: 0, paddingTop: 2 },
})
