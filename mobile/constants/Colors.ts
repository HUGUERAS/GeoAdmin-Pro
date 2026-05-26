export const Colors = {
  dark: {
    background: '#061017',
    surface: '#081923',
    surfaceAlt: '#0A202B',
    panel: '#0D1E29',
    panelStrong: '#102B38',
    card: '#0D1E29',
    cardBorder: '#1A3341',
    line: '#16303E',
    lineStrong: '#275064',
    field: '#081721',
    fieldBorder: '#224557',
    accentSoft: '#123825',
    cyanSoft: '#0E3140',
    shadow: '#02070A',
    grid: '#12303D',
    primary: '#35D07F',
    primaryDark: '#149553',
    primaryText: '#03140A',
    text: '#F3FBF7',
    muted: '#93A9B6',
    success: '#34D399',
    danger: '#EF4444',
    info: '#36C5F0',
    warning: '#FBBF24',
    purple: '#7C6CF2',
    gray: '#6B7C88',
  }
}

export const StatusColors: Record<string, string> = {
  medicao: '#38BDF8', // Azul ciano: campo e captura
  montagem: '#F59E0B', // Ambar: montagem e processamento
  protocolado: '#7C6CF2', // Violeta frio: aguardando análise
  aprovado: '#22C55E', // Verde forte: aprovado
  finalizado: '#6B7C88', // Cinza azulado: encerrado
}

export const StatusLabels: Record<string, string> = {
  medicao: 'Medição',
  montagem: 'Montagem',
  protocolado: 'Protocolado',
  aprovado: 'Aprovado',
  finalizado: 'Finalizado',
}
