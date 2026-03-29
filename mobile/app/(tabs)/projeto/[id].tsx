import { useState, useEffect, useCallback } from 'react'
import { View, Text, ScrollView, StyleSheet, ActivityIndicator, TouchableOpacity, Alert, Clipboard } from 'react-native'
import { useLocalSearchParams, useRouter } from 'expo-router'
import * as Linking from 'expo-linking'
import { Colors } from '../../../constants/Colors'
import { API_URL } from '../../../constants/Api'
import { StatusBadge } from '../../../components/StatusBadge'
import { SyncBadge } from '../../../components/SyncBadge'
import { contarPendentes, initDB, cacheProjetoDetalhe, getCachedProjetoDetalhe, contarErros, resetarErros, salvarUltimoProjetoMapa } from '../../../lib/db'
import { sincronizar } from '../../../lib/sync'

type ProximaEtapa = {
  titulo: string
  descricao: string
  atalho: string
  cor: string
}

export default function DetalheProjetoScreen() {
  const C = Colors.dark
  const { id } = useLocalSearchParams<{ id: string }>()
  const router  = useRouter()
  const [projeto, setProjeto]       = useState<any>(null)
  const [loading, setLoading]       = useState(true)
  const [gerando, setGerando]       = useState(false)
  const [pendentes, setPendentes]   = useState(0)
  const [erros, setErros]           = useState(0)
  const [sincronizando, setSinc]    = useState(false)
  const [offline, setOffline]       = useState(false)
  const [semCache, setSemCache]     = useState(false)

  const atualizarPendentes = useCallback(async () => {
    const n = await contarPendentes(id)
    setPendentes(n)
    const e = await contarErros(id)
    setErros(e)
  }, [id])

  const handleSync = async () => {
    setSinc(true)
    const r = await sincronizar(id)
    await atualizarPendentes()
    setSinc(false)
    if (r.semConexao) {
      Alert.alert('Sem conexão', 'Sem conexão — pontos mantidos para sincronização posterior.')
    } else if (r.sincronizados > 0) {
      Alert.alert('Sincronizado', `${r.sincronizados} ponto(s) enviado(s).`)
    }
  }

  const handleSyncBadgePress = async () => {
    if (erros > 0) {
      await resetarErros(id)
      await atualizarPendentes()
    }
    await handleSync()
  }

  useEffect(() => {
    const iniciar = async () => {
      try {
        await initDB()
        setOffline(false)
        setSemCache(false)
        const res = await fetch(`${API_URL}/projetos/${id}`)
        const data = await res.json()
        await cacheProjetoDetalhe(id, data)
        setProjeto(data)
      } catch {
        try {
          const cached = await getCachedProjetoDetalhe(id)
          if (cached) {
            setProjeto(cached)
            setOffline(true)
          } else {
            setSemCache(true)
          }
        } catch {
          setSemCache(true)
        }
      } finally {
        setLoading(false)
      }
    }
    iniciar()
    atualizarPendentes()
  }, [id, atualizarPendentes])

  const gerarMagicLink = async () => {
    try {
      const res  = await fetch(`${API_URL}/projetos/${id}/magic-link`, { method: 'POST' })
      const data = await res.json()
      Clipboard.setString(data.mensagem_whatsapp || data.link)
      Alert.alert('Link copiado!', 'Mensagem para WhatsApp copiada.\nCole direto no chat do cliente.')
    } catch {
      Alert.alert('Erro', 'Não foi possível gerar o link.')
    }
  }

  const gerarDocumentos = async () => {
    if (!projeto.total_pontos || projeto.total_pontos === 0) {
      Alert.alert('Sem pontos', 'Este projeto não tem pontos coletados. Colete os pontos antes de gerar os documentos.')
      return
    }
    setGerando(true)
    try {
      const res = await fetch(`${API_URL}/projetos/${id}/gerar-documentos`, { method: 'POST' })
      if (!res.ok) {
        const err = await res.json()
        Alert.alert('Atenção', err.erro || 'Erro ao gerar documentos.')
        return
      }
      Alert.alert('Pronto!', 'Documentos gerados. Acesse pelo computador em /projetos/' + id + '/documentos')
    } catch {
      Alert.alert('Erro', 'Falha ao gerar documentos.')
    } finally {
      setGerando(false)
    }
  }

  const abrirUrlOperacional = async (url: string, sucesso: string) => {
    try {
      const suportado = await Linking.canOpenURL(url)
      if (!suportado) {
        throw new Error('URL nao suportada')
      }
      await Linking.openURL(url)
      Alert.alert('Fluxo iniciado', sucesso)
    } catch {
      Clipboard.setString(url)
      Alert.alert('Link copiado', 'Nao foi possivel abrir automaticamente. O link foi copiado para uso no navegador do escritorio.')
    }
  }

  const prepararParaMetrica = async () => {
    await abrirUrlOperacional(
      `${API_URL}/projetos/${id}/metrica/preparar`,
      'O pacote do Métrica foi aberto para download no navegador.',
    )
  }

  const abrirManifestoMetrica = async () => {
    await abrirUrlOperacional(
      `${API_URL}/projetos/${id}/metrica/manifesto`,
      'O manifesto do bridge foi aberto para inspeção.',
    )
  }

  const abrirMapaProjeto = async () => {
    try {
      await salvarUltimoProjetoMapa(id)
    } catch {
      // segue a navegacao mesmo sem persistir o contexto
    }
    router.push(`/(tabs)/mapa/${id}` as any)
  }

  if (loading) return (
    <View style={[s.centro, { backgroundColor: C.background }]}> 
      <ActivityIndicator color={C.primary} size="large" />
    </View>
  )

  if (semCache) return (
    <View style={[s.centro, { backgroundColor: C.background }]}> 
      <Text style={[s.semCacheTxt, { color: C.muted }]}>Sem conexão e sem cache para este projeto.</Text>
    </View>
  )

  if (!projeto) return (
    <View style={[s.centro, { backgroundColor: C.background }]}> 
      <Text style={{ color: C.muted }}>Projeto não encontrado.</Text>
    </View>
  )

  const clienteVinculado = Boolean(projeto.cliente_id || projeto.cliente_nome)
  const statusProjeto = String(projeto.status || '').toLowerCase()
  const proximaEtapa: ProximaEtapa = (() => {
    if (erros > 0) {
      return {
        titulo: 'Revisar pontos com falha de sincronização',
        descricao: 'Há medições com erro pendente. Limpe o erro pela nuvem e tente sincronizar antes de seguir.',
        atalho: 'Atalho sugerido: badge de sincronização',
        cor: C.danger,
      }
    }
    if (pendentes > 0) {
      return {
        titulo: 'Sincronizar coleta de campo',
        descricao: 'Ainda existem pontos locais aguardando envio. Feche isso antes de gerar peças e documentos.',
        atalho: 'Atalho sugerido: badge de sincronização',
        cor: C.primary,
      }
    }
    if (!projeto.total_pontos || projeto.total_pontos === 0) {
      return {
        titulo: 'Começar pelo mapa / CAD',
        descricao: 'O projeto ainda não tem pontos suficientes. Abra o mapa, lance os vértices e salve o perímetro com confiança.',
        atalho: 'Atalho sugerido: Ver no Mapa',
        cor: C.info,
      }
    }
    if (!clienteVinculado) {
      return {
        titulo: 'Vincular cliente e destravar documentação',
        descricao: 'Sem cliente vinculado a parte documental fica travada. Cadastre ou vincule o cliente antes de avançar.',
        atalho: 'Atalho sugerido: Cliente & Documentação',
        cor: C.success,
      }
    }
    if (statusProjeto.includes('formulario') || statusProjeto.includes('pendente')) {
      return {
        titulo: 'Cobrar preenchimento do cliente',
        descricao: 'O perímetro já existe, agora a etapa crítica é garantir que o cliente conclua o formulário e os dados pessoais.',
        atalho: 'Atalho sugerido: Copiar Link do Cliente',
        cor: C.primary,
      }
    }
    if (statusProjeto.includes('documentacao') || statusProjeto.includes('andamento')) {
      return {
        titulo: 'Fechar a parte documental',
        descricao: 'A documentação está em andamento. Revise o cadastro, confronte pendências e gere as peças finais com calma.',
        atalho: 'Atalho sugerido: Gerar Documentos GPRF',
        cor: C.success,
      }
    }
    return {
      titulo: 'Preparar entrega para o escritório',
      descricao: 'Projeto, cliente e documentos parecem encaminhados. O próximo passo é baixar o pacote mastigado para o Métrica.',
      atalho: 'Atalho sugerido: Preparar para Métrica',
      cor: C.primary,
    }
  })()

  return (
    <ScrollView style={[s.container, { backgroundColor: C.background }]}>
      {offline && (
        <View style={s.bannerOffline}>
          <Text style={s.bannerTxt}>📡 Offline — exibindo dados em cache</Text>
        </View>
      )}

      <View style={[s.header, { backgroundColor: C.card, borderBottomColor: C.cardBorder }]}> 
        <View style={s.headerRow}>
          <Text style={[s.titulo, { color: C.text, flex: 1 }]} numberOfLines={2}>{projeto.projeto_nome}</Text>
          <SyncBadge pendentes={pendentes} erros={erros} onPress={handleSyncBadgePress} sincronizando={sincronizando} />
        </View>
        <View style={{ marginTop: 8 }}><StatusBadge status={projeto.status} /></View>
      </View>

      <View style={s.body}>
        <View style={[s.proximaEtapaCard, { backgroundColor: `${proximaEtapa.cor}14`, borderColor: proximaEtapa.cor }]}> 
          <Text style={[s.proximaEtapaLabel, { color: proximaEtapa.cor }]}>Próxima etapa</Text>
          <Text style={[s.proximaEtapaTitulo, { color: C.text }]}>{proximaEtapa.titulo}</Text>
          <Text style={[s.proximaEtapaDescricao, { color: C.muted }]}>{proximaEtapa.descricao}</Text>
          <Text style={[s.proximaEtapaAtalho, { color: proximaEtapa.cor }]}>{proximaEtapa.atalho}</Text>
        </View>

        {[
          ['Cliente',   projeto.cliente_nome],
          ['Município', projeto.municipio],
          ['Comarca',   projeto.comarca],
          ['Matrícula', projeto.matricula],
          ['Job',       projeto.numero_job],
          ['Área',      projeto.area_ha ? `${projeto.area_ha} ha` : null],
          ['Pontos',    projeto.total_pontos?.toString()],
        ].filter(([,v]) => v).map(([label, valor]) => (
          <View key={label as string} style={[s.campo, { borderBottomColor: C.cardBorder }]}> 
            <Text style={[s.campoLabel, { color: C.muted }]}>{label}</Text>
            <Text style={[s.campoValor, { color: C.text }]}>{valor}</Text>
          </View>
        ))}

        {projeto.cliente_id ? (
          <TouchableOpacity
            style={[s.btn, { backgroundColor: C.card, borderColor: C.success }]}
            onPress={() => router.push(`/(tabs)/clientes/${projeto.cliente_id}` as any)}
            accessibilityRole="button"
            accessibilityLabel="Abrir cliente e documentacao"
          >
            <Text style={[s.btnTxt, { color: C.success }]}>👤 Cliente & Documentação</Text>
          </TouchableOpacity>
        ) : null}

        <TouchableOpacity
          style={[s.btn, { backgroundColor: C.card, borderColor: C.info }]}
          onPress={abrirMapaProjeto}
          accessibilityRole="button"
          accessibilityLabel="Ver projeto no mapa"
        >
          <Text style={[s.btnTxt, { color: C.info }]}>🗺 Ver no Mapa</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[s.btn, { backgroundColor: C.card, borderColor: C.primary }]}
          onPress={gerarMagicLink}
          accessibilityRole="button"
          accessibilityLabel="Copiar link do cliente para WhatsApp"
        >
          <Text style={[s.btnTxt, { color: C.primary }]}>📱 Copiar Link do Cliente</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[s.btn, { backgroundColor: C.card, borderColor: C.primaryDark }]}
          onPress={prepararParaMetrica}
          accessibilityRole="button"
          accessibilityLabel="Preparar pacote para o Métrica TOPO"
        >
          <Text style={[s.btnTxt, { color: C.primary }]}>📦 Preparar para Métrica</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[s.btn, { backgroundColor: C.card, borderColor: C.muted }]}
          onPress={abrirManifestoMetrica}
          accessibilityRole="button"
          accessibilityLabel="Abrir manifesto do bridge do Métrica"
        >
          <Text style={[s.btnTxt, { color: C.text }]}>🧭 Ver Manifesto Métrica</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[s.btn, { backgroundColor: C.primary }]}
          onPress={gerarDocumentos}
          disabled={gerando}
          accessibilityRole="button"
          accessibilityLabel="Gerar documentos GPRF"
          accessibilityState={{ disabled: gerando }}
        >
          {gerando
            ? <ActivityIndicator color={C.primaryText} />
            : <Text style={[s.btnTxt, { color: C.primaryText }]}>📄 Gerar Documentos GPRF</Text>
          }
        </TouchableOpacity>
      </View>
    </ScrollView>
  )
}

const s = StyleSheet.create({
  container:     { flex: 1 },
  centro:        { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header:        { padding: 20, paddingTop: 56, borderBottomWidth: 0.5 },
  headerRow:     { flexDirection: 'row', alignItems: 'flex-start' },
  titulo:        { fontSize: 22, fontWeight: '700' },
  body:          { padding: 16 },
  proximaEtapaCard: { borderWidth: 1, borderRadius: 14, padding: 14, marginBottom: 12, gap: 6 },
  proximaEtapaLabel: { fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.8, fontWeight: '700' },
  proximaEtapaTitulo: { fontSize: 17, fontWeight: '700' },
  proximaEtapaDescricao: { fontSize: 13, lineHeight: 20 },
  proximaEtapaAtalho: { fontSize: 12, fontWeight: '700' },
  campo:         { paddingVertical: 12, borderBottomWidth: 0.5 },
  campoLabel:    { fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 2 },
  campoValor:    { fontSize: 15, fontWeight: '500' },
  btn:           { borderRadius: 10, padding: 16, alignItems: 'center', marginTop: 12, borderWidth: 1 },
  btnTxt:        { fontSize: 15, fontWeight: '700' },
  bannerOffline: { backgroundColor: '#B8860B', paddingVertical: 6, paddingHorizontal: 14 },
  bannerTxt:     { color: '#FFF8DC', fontSize: 12, fontWeight: '500', textAlign: 'center' },
  semCacheTxt:   { fontSize: 14, textAlign: 'center', paddingHorizontal: 24 },
})
