export const Colors = {
  dark: {
    background: '#07131B', // Azul petróleo escuro para dar cara mais técnica
    card: '#0D1E29', // Cartões com contraste limpo sobre o fundo
    cardBorder: '#183445', // Borda fria e sutil
    primary: '#28C76F', // Verde operacional mais vivo
    primaryDark: '#149553', // Variação para estados de toque
    primaryText: '#04110A', // Texto escuro sobre botões claros
    text: '#F3FBF7', // Branco levemente esverdeado
    muted: '#8FA4B2', // Cinza azulado para apoio
    success: '#34D399', // Verde de sucesso mais luminoso
    danger: '#EF4444',
    info: '#38BDF8',
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
