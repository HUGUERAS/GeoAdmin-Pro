import { useState, useEffect, useCallback } from 'react'
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  TouchableOpacity,
  Alert,
  Clipboard,
} from 'react-native'
import { useLocalSearchParams, useRouter } from 'expo-router'
import * as Linking from 'expo-linking'
import { Feather } from '@expo/vector-icons'
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

type SecaoProjeto = 'visao' | 'areas' | 'clientes' | 'confrontacoes' | 'documentos'

const SECOES: { id: SecaoProjeto; label: string; icone: keyof typeof Feather.glyphMap }[] = [
  { id: 'visao', label: 'Visão', icone: 'layout' },
  { id: 'areas', label: 'Áreas', icone: 'layers' },
  { id: 'clientes', label: 'Clientes', icone: 'users' },
  { id: 'confrontacoes', label: 'Confrontações', icone: 'git-merge' },
  { id: 'documentos', label: 'Documentos', icone: 'file-text' },
]

function formatarData(valor?: string | null, comHora = true) {
  if (!valor) return 'Sem registro'
  const data = new Date(valor)
  if (Number.isNaN(data.getTime())) return 'Sem registro'
  return data.toLocaleString('pt-BR', comHora ? {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  } : {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

function rotuloStatusArea(area: any) {
  if (area.status_geometria === 'geometria_final') {
    return { texto: 'Geometria final', cor: Colors.dark.success }
  }
  if (area.status_geometria === 'apenas_esboco') {
    return { texto: 'Só esboço do cliente', cor: Colors.dark.info }
  }
  return { texto: 'Sem geometria', cor: Colors.dark.muted }
}

function rotuloConfrontacao(item: any) {
  if (item.tipo === 'sobreposicao') {
    return { texto: 'Sobreposição', cor: Colors.dark.danger }
  }
  return { texto: 'Divisa detectada', cor: Colors.dark.success }
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
  const [secao, setSecao]           = useState<SecaoProjeto>('visao')

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
      Alert.alert('Link copiado', 'A mensagem pronta para WhatsApp foi copiada. Cole no chat do cliente para destravar o formulário.')
    } catch {
      Alert.alert('Erro', 'Não foi possível gerar o link agora.')
    }
  }

  const gerarDocumentos = async () => {
    if (!projeto.total_pontos || projeto.total_pontos === 0) {
      Alert.alert('Sem pontos', 'Este projeto ainda não tem pontos suficientes. Lance os vértices antes de gerar as peças.')
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
      Alert.alert('Documentos gerados', 'O pacote documental foi preparado com sucesso para este projeto.')
    } catch {
      Alert.alert('Erro', 'Falha ao gerar documentos.')
    } finally {
      setGerando(false)
    }
  }

  const abrirUrlOperacional = async (url: string, sucesso: string) => {
    try {
      const suportado = await Linking.canOpenURL(url)
      if (!suportado) throw new Error('URL nao suportada')
      await Linking.openURL(url)
      Alert.alert('Fluxo iniciado', sucesso)
    } catch {
      Clipboard.setString(url)
      Alert.alert('Link copiado', 'Não foi possível abrir automaticamente. O link foi copiado para uso no navegador do escritório.')
    }
  }

  const prepararParaMetrica = async () => {
    await abrirUrlOperacional(`${API_URL}/projetos/${id}/metrica/preparar`, 'O pacote do Métrica foi aberto para download no navegador.')
  }

  const abrirManifestoMetrica = async () => {
    await abrirUrlOperacional(`${API_URL}/projetos/${id}/metrica/manifesto`, 'O manifesto do bridge foi aberto para inspeção.')
  }

  const baixarCartasConfrontacao = async () => {
    await abrirUrlOperacional(`${API_URL}/projetos/${id}/confrontacoes/cartas`, 'O ZIP com as cartas de confrontação foi aberto no navegador.')
  }

  const abrirMapaProjeto = async () => {
    try {
      await salvarUltimoProjetoMapa(id)
    } catch {
      // segue a navegação mesmo sem persistir contexto
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
  const areas = projeto.areas || []
  const confrontacoes = projeto.confrontacoes || []
  const documentos = projeto.documentos || []
  const formulario = projeto.formulario || {}
  const checklist = projeto.checklist_documental?.itens || []
  const cliente = projeto.cliente || projeto.clientes?.[0] || null
  const resumoGeo = projeto.resumo_geo || {}

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
        descricao: 'Sem cliente vinculado, a parte documental fica travada. Cadastre ou vincule o cliente antes de avançar.',
        atalho: 'Atalho sugerido: Clientes',
        cor: C.success,
      }
    }
    if (!formulario.formulario_ok) {
      return {
        titulo: 'Cobrar preenchimento do cliente',
        descricao: 'O perímetro já existe. Agora a etapa crítica é garantir formulário, croqui e dados pessoais.',
        atalho: 'Atalho sugerido: Copiar Link do Cliente',
        cor: C.primary,
      }
    }
    if (!documentos.length) {
      return {
        titulo: 'Fechar documentação e confrontações',
        descricao: 'Com cadastro e áreas já recebidos, revise confrontações e gere as peças técnicas do processo.',
        atalho: 'Atalho sugerido: Documentos',
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
          <Text style={s.bannerTxt}>Offline — exibindo dados em cache</Text>
        </View>
      )}

      <View style={[s.header, { backgroundColor: C.card, borderBottomColor: C.cardBorder }]}>
        <View style={s.headerRow}>
          <View style={{ flex: 1 }}>
            <Text style={[s.titulo, { color: C.text }]} numberOfLines={2}>{projeto.projeto_nome}</Text>
            <Text style={[s.subtitulo, { color: C.muted }]}>{projeto.municipio || 'Município pendente'} · {projeto.total_pontos ?? 0} ponto(s)</Text>
          </View>
          <SyncBadge pendentes={pendentes} erros={erros} onPress={handleSyncBadgePress} sincronizando={sincronizando} />
        </View>
        <View style={s.badgesRow}>
          <StatusBadge status={projeto.status} />
          <View style={[s.inlineChip, { borderColor: C.cardBorder }]}>
            <Text style={[s.inlineChipTxt, { color: C.text }]}>{areas.length} área(s)</Text>
          </View>
          <View style={[s.inlineChip, { borderColor: C.cardBorder }]}>
            <Text style={[s.inlineChipTxt, { color: C.text }]}>{confrontacoes.length} confrontação(ões)</Text>
          </View>
        </View>
      </View>

      <View style={s.body}>
        <View style={[s.proximaEtapaCard, { backgroundColor: `${proximaEtapa.cor}14`, borderColor: proximaEtapa.cor }]}>
          <Text style={[s.proximaEtapaLabel, { color: proximaEtapa.cor }]}>Próxima etapa</Text>
          <Text style={[s.proximaEtapaTitulo, { color: C.text }]}>{proximaEtapa.titulo}</Text>
          <Text style={[s.proximaEtapaDescricao, { color: C.muted }]}>{proximaEtapa.descricao}</Text>
          <Text style={[s.proximaEtapaAtalho, { color: proximaEtapa.cor }]}>{proximaEtapa.atalho}</Text>
        </View>

        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={s.metricasRow}>
          {[
            { label: 'Áreas', valor: resumoGeo.areas_total ?? areas.length, cor: C.info },
            { label: 'Confrontações', valor: resumoGeo.confrontacoes_total ?? confrontacoes.length, cor: C.success },
            { label: 'Docs', valor: projeto.documentos_resumo?.total ?? documentos.length, cor: C.primary },
            { label: 'Esboços', valor: resumoGeo.esbocos_total ?? 0, cor: C.danger },
          ].map((item) => (
            <View key={item.label} style={[s.metaCard, { backgroundColor: C.card, borderColor: C.cardBorder }]}> 
              <Text style={[s.metaValor, { color: item.cor }]}>{item.valor}</Text>
              <Text style={[s.metaLabel, { color: C.muted }]}>{item.label}</Text>
            </View>
          ))}
        </ScrollView>

        <View style={s.actionsGrid}>
          <TouchableOpacity style={[s.actionCard, { backgroundColor: C.card, borderColor: C.cardBorder }]} onPress={abrirMapaProjeto}>
            <Feather name="map" size={18} color={C.info} />
            <Text style={[s.actionTitle, { color: C.text }]}>Ver no mapa</Text>
            <Text style={[s.actionDesc, { color: C.muted }]}>Abrir CAD e perímetro ativo</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[s.actionCard, { backgroundColor: C.card, borderColor: C.cardBorder }]} onPress={gerarMagicLink}>
            <Feather name="send" size={18} color={C.primary} />
            <Text style={[s.actionTitle, { color: C.text }]}>Copiar link do cliente</Text>
            <Text style={[s.actionDesc, { color: C.muted }]}>WhatsApp pronto para envio</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[s.actionCard, { backgroundColor: C.card, borderColor: C.cardBorder }]} onPress={prepararParaMetrica}>
            <Feather name="package" size={18} color={C.success} />
            <Text style={[s.actionTitle, { color: C.text }]}>Preparar para Métrica</Text>
            <Text style={[s.actionDesc, { color: C.muted }]}>Baixar pacote do bridge</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[s.actionCard, { backgroundColor: C.card, borderColor: C.cardBorder }]} onPress={abrirManifestoMetrica}>
            <Feather name="compass" size={18} color={C.primary} />
            <Text style={[s.actionTitle, { color: C.text }]}>Manifesto Métrica</Text>
            <Text style={[s.actionDesc, { color: C.muted }]}>Inspecionar checklist do pacote</Text>
          </TouchableOpacity>
        </View>

        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={s.secoesRow}>
          {SECOES.map((item) => {
            const ativa = secao === item.id
            return (
              <TouchableOpacity
                key={item.id}
                style={[
                  s.secaoChip,
                  ativa
                    ? { backgroundColor: C.primary, borderColor: C.primary }
                    : { backgroundColor: C.card, borderColor: C.cardBorder },
                ]}
                onPress={() => setSecao(item.id)}
              >
                <Feather name={item.icone} size={14} color={ativa ? C.primaryText : C.muted} />
                <Text style={[s.secaoChipTxt, { color: ativa ? C.primaryText : C.text }]}>{item.label}</Text>
              </TouchableOpacity>
            )
          })}
        </ScrollView>

        {secao === 'visao' && (
          <View style={s.sectionWrap}>
            <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
              <Text style={[s.cardTitle, { color: C.text }]}>Situação do projeto</Text>
              {[
                ['Cliente principal', projeto.cliente_nome || 'Sem cliente vinculado'],
                ['Município', projeto.municipio || 'Pendente'],
                ['Comarca', projeto.comarca || 'Pendente'],
                ['Matrícula', projeto.matricula || 'Pendente'],
                ['Job', projeto.numero_job || 'Não definido'],
                ['Perímetro ativo', projeto.perimetro_ativo?.tipo || 'Sem perímetro técnico'],
              ].map(([label, valor]) => (
                <View key={label as string} style={[s.campo, { borderBottomColor: C.cardBorder }]}> 
                  <Text style={[s.campoLabel, { color: C.muted }]}>{label}</Text>
                  <Text style={[s.campoValor, { color: C.text }]}>{valor}</Text>
                </View>
              ))}
            </View>

            <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
              <Text style={[s.cardTitle, { color: C.text }]}>Checklist documental</Text>
              {checklist.map((item: any) => (
                <View key={item.id} style={[s.checkItem, { borderColor: C.cardBorder }]}> 
                  <Feather name={item.ok ? 'check-circle' : 'circle'} size={16} color={item.ok ? C.success : C.muted} />
                  <View style={{ flex: 1 }}>
                    <Text style={[s.checkTitle, { color: C.text }]}>{item.label}</Text>
                    <Text style={[s.checkDesc, { color: C.muted }]}>{item.descricao}</Text>
                  </View>
                </View>
              ))}
            </View>
          </View>
        )}

        {secao === 'areas' && (
          <View style={s.sectionWrap}>
            {areas.length === 0 ? (
              <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}> 
                <Text style={[s.cardTitle, { color: C.text }]}>Nenhuma área conhecida ainda</Text>
                <Text style={[s.emptyTxt, { color: C.muted }]}>Quando o cliente preencher o formulário ou quando o perímetro técnico for salvo, as áreas aparecerão aqui.</Text>
              </View>
            ) : areas.map((area: any) => {
              const status = rotuloStatusArea(area)
              return (
                <View key={area.id} style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}> 
                  <View style={s.cardHeaderRow}>
                    <View style={{ flex: 1 }}>
                      <Text style={[s.cardTitle, { color: C.text }]}>{area.nome || 'Área sem nome'}</Text>
                      <Text style={[s.cardSubtitle, { color: C.muted }]}>{area.proprietario_nome || projeto.cliente_nome || 'Proprietário pendente'}</Text>
                    </View>
                    <View style={[s.inlineStatus, { backgroundColor: `${status.cor}16`, borderColor: status.cor }]}>
                      <Text style={[s.inlineStatusTxt, { color: status.cor }]}>{status.texto}</Text>
                    </View>
                  </View>
                  <View style={s.infoGrid}>
                    <View style={[s.infoMiniCard, { backgroundColor: C.background, borderColor: C.cardBorder }]}>
                      <Text style={[s.infoMiniLabel, { color: C.muted }]}>Área ativa</Text>
                      <Text style={[s.infoMiniValue, { color: C.text }]}>{area.resumo_ativo?.area_ha ? `${Number(area.resumo_ativo.area_ha).toFixed(4)} ha` : 'Sem cálculo'}</Text>
                    </View>
                    <View style={[s.infoMiniCard, { backgroundColor: C.background, borderColor: C.cardBorder }]}>
                      <Text style={[s.infoMiniLabel, { color: C.muted }]}>Vértices</Text>
                      <Text style={[s.infoMiniValue, { color: C.text }]}>{area.resumo_ativo?.vertices_total ?? 0}</Text>
                    </View>
                    <View style={[s.infoMiniCard, { backgroundColor: C.background, borderColor: C.cardBorder }]}>
                      <Text style={[s.infoMiniLabel, { color: C.muted }]}>Anexos</Text>
                      <Text style={[s.infoMiniValue, { color: C.text }]}>{area.anexos?.length ?? 0}</Text>
                    </View>
                  </View>
                  <Text style={[s.areaMeta, { color: C.muted }]}>Município: {area.municipio || projeto.municipio || 'Pendente'} · Matrícula: {area.matricula || 'Pendente'}</Text>
                </View>
              )
            })}
          </View>
        )}

        {secao === 'clientes' && (
          <View style={s.sectionWrap}>
            <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}> 
              <Text style={[s.cardTitle, { color: C.text }]}>Cliente principal</Text>
              {cliente ? (
                <>
                  <Text style={[s.clientName, { color: C.text }]}>{cliente.nome || projeto.cliente_nome || 'Cliente sem nome'}</Text>
                  <Text style={[s.clientMeta, { color: C.muted }]}>CPF: {cliente.cpf || cliente.cpf_cnpj || 'Pendente'} · Telefone: {cliente.telefone || 'Pendente'}</Text>
                  <Text style={[s.clientMeta, { color: C.muted }]}>Formulário: {formulario.formulario_ok ? `Recebido em ${formatarData(formulario.formulario_em)}` : 'Pendente'}</Text>
                  <TouchableOpacity style={[s.inlineBtn, { borderColor: C.success }]} onPress={() => router.push(`/(tabs)/clientes/${cliente.id}` as any)}>
                    <Text style={[s.inlineBtnTxt, { color: C.success }]}>Abrir cliente & documentação</Text>
                  </TouchableOpacity>
                </>
              ) : (
                <Text style={[s.emptyTxt, { color: C.muted }]}>Este projeto ainda não tem cliente principal vinculado.</Text>
              )}
            </View>
          </View>
        )}

        {secao === 'confrontacoes' && (
          <View style={s.sectionWrap}>
            <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}> 
              <View style={s.cardHeaderRow}>
                <View style={{ flex: 1 }}>
                  <Text style={[s.cardTitle, { color: C.text }]}>Confrontações detectadas</Text>
                  <Text style={[s.cardSubtitle, { color: C.muted }]}>Relações automáticas entre áreas do projeto e base para as cartas.</Text>
                </View>
                <TouchableOpacity style={[s.inlineBtn, { borderColor: C.primary }]} onPress={baixarCartasConfrontacao}>
                  <Text style={[s.inlineBtnTxt, { color: C.primary }]}>Gerar cartas ZIP</Text>
                </TouchableOpacity>
              </View>

              {confrontacoes.length === 0 ? (
                <Text style={[s.emptyTxt, { color: C.muted }]}>Nenhuma confrontação geométrica foi detectada ainda. Isso aparece quando existem áreas suficientes com esboço ou geometria final.</Text>
              ) : confrontacoes.map((item: any) => {
                const status = rotuloConfrontacao(item)
                return (
                  <View key={item.id} style={[s.confCard, { borderColor: C.cardBorder }]}> 
                    <View style={s.cardHeaderRow}>
                      <Text style={[s.confTitle, { color: C.text }]}>{item.area_a?.nome} ↔ {item.area_b?.nome}</Text>
                      <View style={[s.inlineStatus, { backgroundColor: `${status.cor}16`, borderColor: status.cor }]}>
                        <Text style={[s.inlineStatusTxt, { color: status.cor }]}>{status.texto}</Text>
                      </View>
                    </View>
                    <Text style={[s.confMeta, { color: C.muted }]}>Contato aproximado: {item.contato_m ?? 0} m · Interseção: {item.area_intersecao_ha ?? 0} ha</Text>
                  </View>
                )
              })}

              <View style={[s.manualBlock, { backgroundColor: C.background, borderColor: C.cardBorder }]}> 
                <Text style={[s.manualBlockTitle, { color: C.text }]}>Confrontantes cadastrais</Text>
                <Text style={[s.emptyTxt, { color: C.muted }]}>Há {projeto.confrontantes?.length ?? 0} confrontante(s) cadastrados manualmente para a parte declaratória.</Text>
              </View>
            </View>
          </View>
        )}

        {secao === 'documentos' && (
          <View style={s.sectionWrap}>
            <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}> 
              <Text style={[s.cardTitle, { color: C.text }]}>Status documental</Text>
              <View style={s.infoGrid}>
                <View style={[s.infoMiniCard, { backgroundColor: C.background, borderColor: C.cardBorder }]}>
                  <Text style={[s.infoMiniLabel, { color: C.muted }]}>Formulário</Text>
                  <Text style={[s.infoMiniValue, { color: C.text }]}>{formulario.formulario_ok ? 'Recebido' : 'Pendente'}</Text>
                </View>
                <View style={[s.infoMiniCard, { backgroundColor: C.background, borderColor: C.cardBorder }]}>
                  <Text style={[s.infoMiniLabel, { color: C.muted }]}>Magic link</Text>
                  <Text style={[s.infoMiniValue, { color: C.text }]}>{formatarData(formulario.magic_link_expira, false)}</Text>
                </View>
                <View style={[s.infoMiniCard, { backgroundColor: C.background, borderColor: C.cardBorder }]}>
                  <Text style={[s.infoMiniLabel, { color: C.muted }]}>Documentos</Text>
                  <Text style={[s.infoMiniValue, { color: C.text }]}>{projeto.documentos_resumo?.total ?? documentos.length}</Text>
                </View>
              </View>
              <TouchableOpacity
                style={[s.btnPrincipal, { backgroundColor: C.primary }]}
                onPress={gerarDocumentos}
                disabled={gerando}
              >
                {gerando ? <ActivityIndicator color={C.primaryText} /> : <Text style={[s.btnPrincipalTxt, { color: C.primaryText }]}>Gerar documentos GPRF</Text>}
              </TouchableOpacity>
            </View>

            <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}> 
              <Text style={[s.cardTitle, { color: C.text }]}>Histórico de documentos</Text>
              {documentos.length === 0 ? (
                <Text style={[s.emptyTxt, { color: C.muted }]}>Ainda não existem documentos gerados para este projeto.</Text>
              ) : documentos.map((doc: any) => (
                <View key={doc.id} style={[s.docItem, { borderBottomColor: C.cardBorder }]}> 
                  <Text style={[s.docNome, { color: C.text }]}>{doc.tipo || 'Documento'}</Text>
                  <Text style={[s.docData, { color: C.muted }]}>{formatarData(doc.gerado_em)}</Text>
                </View>
              ))}
            </View>
          </View>
        )}
      </View>
    </ScrollView>
  )
}

const s = StyleSheet.create({
  container: { flex: 1 },
  centro: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header: { padding: 20, paddingTop: 56, borderBottomWidth: 0.5, gap: 12 },
  headerRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 10 },
  titulo: { fontSize: 24, fontWeight: '700' },
  subtitulo: { fontSize: 13, marginTop: 4 },
  badgesRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  inlineChip: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 6 },
  inlineChipTxt: { fontSize: 12, fontWeight: '600' },
  body: { padding: 16, gap: 14 },
  proximaEtapaCard: { borderWidth: 1, borderRadius: 16, padding: 16, gap: 6 },
  proximaEtapaLabel: { fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.8, fontWeight: '700' },
  proximaEtapaTitulo: { fontSize: 17, fontWeight: '700' },
  proximaEtapaDescricao: { fontSize: 13, lineHeight: 20 },
  proximaEtapaAtalho: { fontSize: 12, fontWeight: '700' },
  metricasRow: { flexDirection: 'row', gap: 10 },
  metaCard: { minWidth: 108, borderWidth: 1, borderRadius: 14, padding: 12, gap: 6 },
  metaValor: { fontSize: 22, fontWeight: '700' },
  metaLabel: { fontSize: 12 },
  actionsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  actionCard: { width: '48%', minWidth: 150, borderWidth: 1, borderRadius: 14, padding: 14, gap: 8 },
  actionTitle: { fontSize: 14, fontWeight: '700' },
  actionDesc: { fontSize: 12, lineHeight: 18 },
  secoesRow: { flexDirection: 'row', gap: 8, paddingBottom: 4 },
  secaoChip: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 12, paddingVertical: 9, flexDirection: 'row', alignItems: 'center', gap: 8 },
  secaoChipTxt: { fontSize: 13, fontWeight: '600' },
  sectionWrap: { gap: 12 },
  card: { borderWidth: 1, borderRadius: 16, padding: 16, gap: 12 },
  cardHeaderRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 10 },
  cardTitle: { fontSize: 17, fontWeight: '700' },
  cardSubtitle: { fontSize: 12, lineHeight: 18, marginTop: 4 },
  campo: { paddingVertical: 10, borderBottomWidth: 0.5 },
  campoLabel: { fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 2 },
  campoValor: { fontSize: 15, fontWeight: '500' },
  checkItem: { borderWidth: 1, borderRadius: 12, padding: 12, flexDirection: 'row', alignItems: 'flex-start', gap: 10 },
  checkTitle: { fontSize: 14, fontWeight: '700' },
  checkDesc: { fontSize: 12, lineHeight: 18, marginTop: 2 },
  inlineStatus: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 6 },
  inlineStatusTxt: { fontSize: 11, fontWeight: '700' },
  infoGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  infoMiniCard: { width: '31%', minWidth: 90, borderWidth: 1, borderRadius: 12, padding: 12, gap: 6 },
  infoMiniLabel: { fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5 },
  infoMiniValue: { fontSize: 15, fontWeight: '700' },
  areaMeta: { fontSize: 12, lineHeight: 18 },
  clientName: { fontSize: 16, fontWeight: '700' },
  clientMeta: { fontSize: 13, lineHeight: 20 },
  inlineBtn: { borderWidth: 1, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 12, alignSelf: 'flex-start' },
  inlineBtnTxt: { fontSize: 13, fontWeight: '700' },
  confCard: { borderWidth: 1, borderRadius: 12, padding: 12, gap: 8 },
  confTitle: { flex: 1, fontSize: 14, fontWeight: '700', marginRight: 10 },
  confMeta: { fontSize: 12, lineHeight: 18 },
  manualBlock: { borderWidth: 1, borderRadius: 12, padding: 12, gap: 6 },
  manualBlockTitle: { fontSize: 14, fontWeight: '700' },
  btnPrincipal: { borderRadius: 12, paddingVertical: 15, alignItems: 'center', justifyContent: 'center' },
  btnPrincipalTxt: { fontSize: 15, fontWeight: '700' },
  docItem: { borderBottomWidth: 0.5, paddingVertical: 10 },
  docNome: { fontSize: 14, fontWeight: '700' },
  docData: { fontSize: 12, marginTop: 3 },
  emptyTxt: { fontSize: 13, lineHeight: 20 },
  bannerOffline: { backgroundColor: '#B8860B', paddingVertical: 6, paddingHorizontal: 14 },
  bannerTxt: { color: '#FFF8DC', fontSize: 12, fontWeight: '500', textAlign: 'center' },
  semCacheTxt: { fontSize: 14, textAlign: 'center', paddingHorizontal: 24 },
})
