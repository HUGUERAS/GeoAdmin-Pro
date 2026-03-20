/**
 * mobile/components/GpsIndicador.tsx
 * Indicador visual de qualidade do fix GPS para uso em campo.
 *
 * Otimizado para legibilidade sob sol e operação com luvas:
 * - Bolinha colorida grande + label grande
 * - Linha secundária com satélites e HDOP
 * - Estado "Aguardando GPS..." quando fix === null
 */

import { View, Text, StyleSheet } from 'react-native'
import { NmeaFix, labelQualidade, corQualidade } from '../lib/nmea'
import { Colors } from '../constants/Colors'

interface Props {
  fix: NmeaFix | null
}

export function GpsIndicador({ fix }: Props) {
  const C = Colors.dark

  if (fix === null) {
    return (
      <View style={[s.container, { backgroundColor: 'rgba(44,44,42,0.92)' }]}>
        <Text style={[s.aguardando, { color: C.muted }]}>Aguardando GPS...</Text>
      </View>
    )
  }

  const cor = corQualidade(fix.qualidade)
  const label = labelQualidade(fix.qualidade)

  return (
    <View style={[s.container, { backgroundColor: 'rgba(44,44,42,0.92)' }]}>
      {/* Linha principal: bolinha + label qualidade */}
      <View style={s.linhaQual}>
        <View style={[s.bolinha, { backgroundColor: cor }]} />
        <Text style={[s.labelQual, { color: cor }]}>{label}</Text>
      </View>

      {/* Linha secundária: satélites e HDOP */}
      <Text style={[s.infoSecundaria, { color: C.muted }]}>
        {fix.satelites} sat{'  '}HDOP {fix.hdop.toFixed(1)}
      </Text>
    </View>
  )
}

const s = StyleSheet.create({
  container: {
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  linhaQual: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  bolinha: {
    width: 14,
    height: 14,
    borderRadius: 7,
  },
  labelQual: {
    fontSize: 18,
    fontWeight: '700',
  },
  infoSecundaria: {
    fontSize: 13,
    marginTop: 4,
    marginLeft: 22, // alinha após a bolinha (14px) + gap (8px)
  },
  aguardando: {
    fontSize: 15,
    fontWeight: '500',
  },
})
