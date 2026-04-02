export const Colors = {
  dark: {
    background:  '#1a1a18',
    card:        '#2c2c2a',
    cardBorder:  '#444441',
    primary:     '#EF9F27',
    primaryDark: '#BA7517',
    primaryText: '#412402',
    text:        '#e8e6de',
    muted:       '#aba99f',  // era #9c9a92 — corrigido para ratio ≥ 4.5:1 sobre card (#2c2c2a)
    success:     '#1D9E75',
    danger:      '#E24B4A',
    info:        '#378ADD',
    purple:      '#7F77DD',
    gray:        '#969490',  // era #888780 — corrigido para ratio ≥ 4.5:1 sobre card
  }
}

export const StatusColors: Record<string, string> = {
  medicao:     '#378ADD',
  montagem:    '#EF9F27',
  protocolado: '#7F77DD',
  aprovado:    '#1D9E75',
  finalizado:  '#888780',
}

export const StatusLabels: Record<string, string> = {
  medicao:     'Medição',
  montagem:    'Montagem',
  protocolado: 'Protocolado',
  aprovado:    'Aprovado',
  finalizado:  'Finalizado',
}
