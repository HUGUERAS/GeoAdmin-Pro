import { useEffect, useMemo, useState } from 'react'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  TouchableOpacity,
  Alert,
  TextInput,
  Platform,
} from 'react-native'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { Feather } from '@expo/vector-icons'
import * as Linking from 'expo-linking'
import * as DocumentPicker from 'expo-document-picker'
import { Colors } from '../../../constants/Colors'
import { StatusBadge } from '../../../components/StatusBadge'
import { ClienteGeometryPreview } from '../../../components/ClienteGeometryPreview'
import { apiDelete, apiGet, apiPatch, apiPost, apiPostFormData } from '../../../lib/api'
import { initDB, salvarUltimoProjetoMapa } from '../../../lib/db'

type Cliente = {
  id: string
  nome?: string | null
  cpf?: string | null
  rg?: string | null
  estado_civil?: string | null
  profissao?: string | null
  telefone?: string | null
  email?: string | null
  endereco?: string | null
  endereco_numero?: string | null
  municipio?: string | null
  estado?: string | null
  setor?: string | null
  cep?: string | null
  conjuge_nome?: string | null
  conjuge_cpf?: string | null
}

type ProjetoCliente = {
  id: string
  projeto_nome?: string | null
  status: string
  municipio?: string | null
  estado?: string | null
  area_ha?: number | null
  total_pontos?: number | null
  documentos_total?: number
  documentos_tipos?: string[]
  ultimo_documento_em?: string | null
  confrontantes_total?: number
  formulario_ok?: boolean
  formulario_em?: string | null
  magic_link_expira?: string | null
  perimetro_tecnico_ok?: boolean
  perimetro_tecnico_tipo?: string | null
}

type ResumoCliente = {
  projetos_total?: number
  documentos_total?: number
  confrontantes_total?: number
  status_documentacao?: string | null
  formulario_em?: string | null
  ultimo_documento_em?: string | null
}

type ChecklistItem = { id: string; label: string; ok: boolean; descricao: string }
type ChecklistProjeto = {
  projeto_id: string
  projeto_nome?: string | null
  status: string
  concluidos: number
  total: number
  progresso_percentual: number
  pendencias: string[]
  itens: ChecklistItem[]
}

type Alerta = {
  nivel: 'alto' | 'medio' | 'baixo'
  tipo: string
  titulo: string
  descricao: string
  projeto_id?: string
  projeto_nome?: string
}

type TimelineEvento = {
  tipo: string
  titulo: string
  descricao: string
  em: string
  projeto_id?: string
}

type Confrontante = {
  id: string
  projeto_id: string
  projeto_nome?: string | null
  lado?: string | null
  tipo?: string | null
  nome?: string | null
  cpf?: string | null
  nome_imovel?: string | null
  matricula?: string | null
  origem?: string | null
  criado_em?: string | null
}

type GeometriaComparativo = {
  status?: string | null
  area_referencia_ha?: number
  area_tecnica_ha?: number
  diferenca_area_ha?: number
  diferenca_area_percentual?: number | null
  sobreposicao_percentual?: number
  area_intersecao_ha?: number
  perimetro_tecnico?: {
    tipo?: string | null
    vertices?: { lon: number; lat: number }[]
    area_ha?: number
    perimetro_m?: number
  }
}

type GeometriaReferencia = {
  nome?: string | null
  origem_tipo?: string | null
  formato?: string | null
  arquivo_nome?: string | null
  projeto_id?: string | null
  atualizado_em?: string | null
  persistencia?: string | null
  vertices?: { lon: number; lat: number }[]
  resumo?: {
    vertices_total?: number
    area_ha?: number
    area_m2?: number
    perimetro_m?: number
  }
  comparativo?: GeometriaComparativo | null
}

type ClienteDetalheResponse = {
  cliente: Cliente
  projetos: ProjetoCliente[]
  resumo: ResumoCliente
  confrontantes: Confrontante[]
  checklist: ChecklistProjeto[]
  alertas: Alerta[]
  timeline: TimelineEvento[]
  geometria_referencia: GeometriaReferencia | null
}

type FormCliente = {
  nome: string
  cpf: string
  rg: string
  estado_civil: string
  profissao: string
  telefone: string
  email: string
  endereco: string
  endereco_numero: string
  municipio: string
  estado: string
  setor: string
  cep: string
  conjuge_nome: string
  conjuge_cpf: string
}

type FormConfrontante = {
  nome: string
  cpf: string
  nome_imovel: string
  matricula: string
  lado: string
  tipo: string
  origem: string
}

function vazioParaTexto(valor?: string | null) {
  return valor ?? ''
}

function clienteParaForm(cliente: Cliente): FormCliente {
  return {
    nome: vazioParaTexto(cliente.nome),
    cpf: vazioParaTexto(cliente.cpf),
    rg: vazioParaTexto(cliente.rg),
    estado_civil: vazioParaTexto(cliente.estado_civil),
    profissao: vazioParaTexto(cliente.profissao),
    telefone: vazioParaTexto(cliente.telefone),
    email: vazioParaTexto(cliente.email),
    endereco: vazioParaTexto(cliente.endereco),
    endereco_numero: vazioParaTexto(cliente.endereco_numero),
    municipio: vazioParaTexto(cliente.municipio),
    estado: vazioParaTexto(cliente.estado),
    setor: vazioParaTexto(cliente.setor),
    cep: vazioParaTexto(cliente.cep),
    conjuge_nome: vazioParaTexto(cliente.conjuge_nome),
    conjuge_cpf: vazioParaTexto(cliente.conjuge_cpf),
  }
}

function confrontoInicial(): FormConfrontante {
  return {
    nome: '',
    cpf: '',
    nome_imovel: '',
    matricula: '',
    lado: 'Outros',
    tipo: 'particular',
    origem: 'fase2',
  }
}

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

function obterMetaStatus(status?: string | null) {
  const C = Colors.dark
  switch (status) {
    case 'pendente_formulario':
      return { cor: C.danger, titulo: 'Formulario pendente', descricao: 'O cliente ainda precisa concluir o preenchimento pelo magic link.' }
    case 'pronto_para_documentar':
      return { cor: C.info, titulo: 'Pronto para documentar', descricao: 'Cadastro recebido. O processo esta pronto para gerar documentos.' }
    case 'documentacao_em_andamento':
      return { cor: C.success, titulo: 'Documentacao em andamento', descricao: 'Ja existem documentos gerados ou movimentacao documental vinculada.' }
    default:
      return { cor: C.muted, titulo: 'Sem projetos vinculados', descricao: 'Vincule o cliente a um projeto para iniciar o acompanhamento.' }
  }
}

function chipDocumentos(tipos?: string[]) {
  if (!tipos || tipos.length === 0) return 'Nenhum documento gerado'
  return tipos.join(' | ')
}

function resumirPendencias(pendencias: string[]) {
  if (pendencias.length === 0) return 'Nenhuma pendencia no momento.'
  if (pendencias.length <= 2) return `Pendencias: ${pendencias.join(' · ')}`
  return `Pendencias: ${pendencias.slice(0, 2).join(' · ')} · +${pendencias.length - 2} itens`
}

function diasRestantesPara(valor?: string | null) {
  if (!valor) return null
  const data = new Date(valor)
  if (Number.isNaN(data.getTime())) return null
  const hoje = new Date()
  hoje.setHours(0, 0, 0, 0)
  data.setHours(0, 0, 0, 0)
  return Math.round((data.getTime() - hoje.getTime()) / 86400000)
}

function obterProximaAcaoProjeto(projeto: ProjetoCliente) {
  const C = Colors.dark
  const diasRestantes = diasRestantesPara(projeto.magic_link_expira)
  const expirado = diasRestantes !== null && diasRestantes < 0

  if (!projeto.formulario_ok && expirado) {
    return {
      cor: C.danger,
      titulo: 'Renovar o link do cliente',
      descricao: 'O magic link expirou e o formulário ainda não foi concluído.',
    }
  }

  if (!projeto.formulario_ok) {
    return {
      cor: C.primary,
      titulo: 'Cobrar o preenchimento do formulário',
      descricao: 'A parte documental depende do cliente concluir o cadastro pelo link.',
    }
  }

  if (!projeto.perimetro_tecnico_ok) {
    return {
      cor: C.info,
      titulo: 'Fechar o perímetro técnico no mapa',
      descricao: 'Os dados do cliente já ajudam, mas o desenho técnico ainda precisa ser revisado no CAD.',
    }
  }

  if ((projeto.documentos_total ?? 0) === 0) {
    return {
      cor: C.success,
      titulo: 'Gerar as peças técnicas',
      descricao: 'Cadastro e perímetro parecem encaminhados. O próximo passo é emitir a documentação do projeto.',
    }
  }

  return {
    cor: C.success,
    titulo: 'Revisar documentos e preparar para o escritório',
    descricao: 'A documentação já começou. Revise os arquivos e depois siga para o pacote do Métrica.',
  }
}

function confirmarAcao(
  titulo: string,
  mensagem: string,
  confirmarTexto: string,
  aoConfirmar: () => void | Promise<void>,
) {
  Alert.alert(titulo, mensagem, [
    { text: 'Cancelar', style: 'cancel' },
    { text: confirmarTexto, style: 'destructive', onPress: () => { void aoConfirmar() } },
  ])
}

function parseVerticesTexto(texto: string) {
  return texto
    .split(/\r?\n/)
    .map((linha) => linha.trim())
    .filter(Boolean)
    .map((linha) => linha.split(/[;, \t]+/).filter(Boolean))
    .filter((partes) => partes.length >= 2)
    .map((partes) => {
      const a = Number(partes[0].replace(',', '.'))
      const b = Number(partes[1].replace(',', '.'))
      if (Math.abs(a) <= 90 && Math.abs(b) <= 180) return { lat: a, lon: b }
      return { lon: a, lat: b }
    })
    .map((item) => ({ lon: item.lon, lat: item.lat }))
}

function inferirMimeTypeArquivo(nome: string, mimeType?: string | null) {
  if (mimeType) return mimeType

  const extensao = nome.split('.').pop()?.toLowerCase()
  if (extensao === 'geojson' || extensao === 'json') return 'application/json'
  if (extensao === 'kml') return 'application/vnd.google-earth.kml+xml'
  if (extensao === 'csv') return 'text/csv'
  if (extensao === 'txt') return 'text/plain'
  if (extensao === 'zip') return 'application/zip'
  return 'application/octet-stream'
}

async function anexarArquivoNoFormData(formData: FormData, asset: DocumentPicker.DocumentPickerAsset) {
  if (Platform.OS === 'web') {
    if (asset.file) {
      formData.append('arquivo', asset.file, asset.name)
      return
    }

    const response = await fetch(asset.uri)
    const blob = await response.blob()
    formData.append('arquivo', blob, asset.name)
    return
  }

  formData.append('arquivo', {
    uri: asset.uri,
    name: asset.name,
    type: inferirMimeTypeArquivo(asset.name, asset.mimeType),
  } as any)
}

export default function ClienteDetalheScreen() {
  const C = Colors.dark
  const insets = useSafeAreaInsets()
  const [topInset, setTopInset] = useState(0)
  useEffect(() => { setTopInset(insets.top) }, [insets.top])
  const router = useRouter()
  const { id } = useLocalSearchParams<{ id: string }>()
  const [detalhe, setDetalhe] = useState<ClienteDetalheResponse | null>(null)
  const [form, setForm] = useState<FormCliente>(clienteParaForm({ id: '' }))
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState('')
  const [salvando, setSalvando] = useState(false)
  const [reenviandoProjetoId, setReenviandoProjetoId] = useState<string | null>(null)
  const [formConfrontante, setFormConfrontante] = useState<FormConfrontante>(confrontoInicial())
  const [projetoConfrontanteId, setProjetoConfrontanteId] = useState('')
  const [confrontanteEditandoId, setConfrontanteEditandoId] = useState<string | null>(null)
  const [salvandoConfrontante, setSalvandoConfrontante] = useState(false)
  const [nomeReferencia, setNomeReferencia] = useState('Referencia do cliente')
  const [manualVerticesTexto, setManualVerticesTexto] = useState('')
  const [importacaoTexto, setImportacaoTexto] = useState('')
  const [formatoImportacao, setFormatoImportacao] = useState<'geojson' | 'kml' | 'csv' | 'txt'>('geojson')
  const [projetoReferenciaId, setProjetoReferenciaId] = useState('')
  const [salvandoReferencia, setSalvandoReferencia] = useState(false)
  const [removendoReferencia, setRemovendoReferencia] = useState(false)

  const carregar = async () => {
    try {
      setErro('')
      const data = await apiGet<ClienteDetalheResponse>(`/clientes/${id}`)
      setDetalhe(data)
      setForm(clienteParaForm(data.cliente))
      setProjetoConfrontanteId((atual) => atual || data.projetos[0]?.id || '')
      setProjetoReferenciaId((atual) => atual || data.geometria_referencia?.projeto_id || data.projetos[0]?.id || '')
      setNomeReferencia((atual) => atual || data.geometria_referencia?.nome || 'Referencia do cliente')
    } catch (e: any) {
      setErro(e?.message ?? 'Nao foi possivel carregar o cliente.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    carregar()
  }, [id])

  const abrirMapaProjeto = async (projetoId: string) => {
    try {
      await initDB()
      await salvarUltimoProjetoMapa(projetoId)
    } catch {
      // segue a navegacao mesmo sem persistir o ultimo contexto
    }
    router.push(`/(tabs)/mapa/${projetoId}` as any)
  }

  const confrontantesPorProjeto = useMemo(() => {
    const grupos: Record<string, Confrontante[]> = {}
    for (const item of detalhe?.confrontantes || []) {
      const chave = item.projeto_id
      grupos[chave] = grupos[chave] || []
      grupos[chave].push(item)
    }
    return grupos
  }, [detalhe])

  const atualizarCampo = (campo: keyof FormCliente, valor: string) => {
    setForm((atual) => ({ ...atual, [campo]: valor }))
  }

  const atualizarCampoConfrontante = (campo: keyof FormConfrontante, valor: string) => {
    setFormConfrontante((atual) => ({ ...atual, [campo]: valor }))
  }

  const salvarCadastro = async () => {
    try {
      setSalvando(true)
      await apiPatch(`/clientes/${id}`, form)
      Alert.alert('Cadastro atualizado', 'Os dados do cliente foram salvos com sucesso.')
      await carregar()
    } catch (e: any) {
      Alert.alert('Falha ao salvar', e?.message ?? 'Não foi possível salvar o cadastro. Verifique sua conexão e tente novamente.')
    } finally {
      setSalvando(false)
    }
  }

  const reenviarMagicLink = async (projeto: ProjetoCliente) => {
    try {
      setReenviandoProjetoId(projeto.id)
      const data = await apiPost<{ link: string; mensagem_whatsapp?: string }>(`/projetos/${projeto.id}/magic-link`, {})
      const mensagem = data.mensagem_whatsapp || data.link
      const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(mensagem)}`
      try {
        await Linking.openURL(whatsappUrl)
        Alert.alert('Magic link pronto', 'Abrimos a mensagem no WhatsApp para voce reenviar ao cliente.')
      } catch {
        const clipboard = (globalThis as any)?.navigator?.clipboard
        if (clipboard?.writeText) {
          await clipboard.writeText(mensagem)
          Alert.alert('Mensagem copiada', 'Cole o texto no WhatsApp do cliente para reenviar o link.')
        } else {
          Alert.alert('Magic link pronto', mensagem)
        }
      }
      await carregar()
    } catch (e: any) {
      Alert.alert('Falha ao gerar link', e?.message ?? 'Não foi possível gerar o magic link. Verifique sua conexão e tente novamente.')
    } finally {
      setReenviandoProjetoId(null)
    }
  }

  const limparConfrontante = () => {
    setConfrontanteEditandoId(null)
    setFormConfrontante(confrontoInicial())
  }

  const iniciarEdicaoConfrontante = (item: Confrontante) => {
    setConfrontanteEditandoId(item.id)
    setProjetoConfrontanteId(item.projeto_id)
    setFormConfrontante({
      nome: vazioParaTexto(item.nome),
      cpf: vazioParaTexto(item.cpf),
      nome_imovel: vazioParaTexto(item.nome_imovel),
      matricula: vazioParaTexto(item.matricula),
      lado: vazioParaTexto(item.lado) || 'Outros',
      tipo: vazioParaTexto(item.tipo) || 'particular',
      origem: vazioParaTexto(item.origem) || 'fase2',
    })
  }

  const salvarConfrontante = async () => {
    if (!projetoConfrontanteId) {
      Alert.alert('Projeto obrigatorio', 'Escolha o projeto ao qual o confrontante pertence.')
      return
    }
    if (!formConfrontante.nome.trim()) {
      Alert.alert('Nome obrigatorio', 'Informe o nome do confrontante.')
      return
    }

    try {
      setSalvandoConfrontante(true)
      const payload = { projeto_id: projetoConfrontanteId, ...formConfrontante }
      if (confrontanteEditandoId) {
        await apiPatch(`/clientes/${id}/confrontantes/${confrontanteEditandoId}`, payload)
      } else {
        await apiPost(`/clientes/${id}/confrontantes`, payload)
      }
      limparConfrontante()
      await carregar()
    } catch (e: any) {
      Alert.alert('Falha ao salvar confrontante', e?.message ?? 'Não foi possível salvar o confrontante. Verifique sua conexão e tente novamente.')
    } finally {
      setSalvandoConfrontante(false)
    }
  }

  const excluirConfrontante = (confrontante: Confrontante) => {
    confirmarAcao(
      'Excluir confrontante?',
      `Remover ${confrontante.nome || 'este confrontante'} do projeto ${confrontante.projeto_nome || 'selecionado'}?`,
      'Excluir',
      async () => {
        try {
          await apiDelete(`/clientes/${id}/confrontantes/${confrontante.id}`)
          if (confrontanteEditandoId === confrontante.id) limparConfrontante()
          await carregar()
          Alert.alert('Confrontante removido', `${confrontante.nome || 'O confrontante'} foi excluido com sucesso.`)
        } catch (e: any) {
          Alert.alert('Falha ao excluir confrontante', e?.message ?? 'Não foi possível excluir o confrontante. Verifique sua conexão e tente novamente.')
        }
      },
    )
  }

  const salvarReferenciaManual = async () => {
    const vertices = parseVerticesTexto(manualVerticesTexto)
    if (vertices.length < 3) {
      Alert.alert('Vertices insuficientes', 'Informe ao menos 3 linhas de coordenadas para o poligono.')
      return
    }
    try {
      setSalvandoReferencia(true)
      const salvo = await apiPost<GeometriaReferencia>(`/clientes/${id}/geometria-referencia/manual`, {
        projeto_id: projetoReferenciaId || null,
        nome: nomeReferencia,
        vertices,
      })
      setManualVerticesTexto('')
      await carregar()
      Alert.alert(
        'Referencia salva',
        `${salvo.nome || nomeReferencia} com ${salvo.resumo?.vertices_total ?? vertices.length} vertices foi salva em ${salvo.persistencia === 'supabase' ? 'Supabase' : 'arquivo local'}.`,
      )
    } catch (e: any) {
      Alert.alert('Falha ao salvar referência', e?.message ?? 'Não foi possível salvar a referência manual. Verifique sua conexão e tente novamente.')
    } finally {
      setSalvandoReferencia(false)
    }
  }

  const importarReferenciaTexto = async () => {
    if (!importacaoTexto.trim()) {
      Alert.alert('Conteudo vazio', 'Cole o conteudo do arquivo ou da geometria antes de importar.')
      return
    }
    try {
      setSalvandoReferencia(true)
      const salvo = await apiPost<GeometriaReferencia>(`/clientes/${id}/geometria-referencia/importar-texto`, {
        projeto_id: projetoReferenciaId || null,
        nome: nomeReferencia,
        formato: formatoImportacao,
        conteudo: importacaoTexto,
      })
      setImportacaoTexto('')
      await carregar()
      Alert.alert(
        'Importacao concluida',
        `${salvo.nome || nomeReferencia} foi importada como ${salvo.formato?.toUpperCase() || formatoImportacao.toUpperCase()} e salva em ${salvo.persistencia === 'supabase' ? 'Supabase' : 'arquivo local'}.`,
      )
    } catch (e: any) {
      Alert.alert('Falha na importação', e?.message ?? 'Não foi possível importar a geometria. Verifique o formato do conteúdo e sua conexão.')
    } finally {
      setSalvandoReferencia(false)
    }
  }

  const importarReferenciaArquivo = async () => {
    try {
      const resultado = await DocumentPicker.getDocumentAsync({
        type: '*/*',
        copyToCacheDirectory: true,
        base64: false,
      })

      if (resultado.canceled || !resultado.assets?.length) {
        return
      }

      const arquivo = resultado.assets[0]
      const formData = new FormData()
      await anexarArquivoNoFormData(formData, arquivo)
      if (projetoReferenciaId) formData.append('projeto_id', projetoReferenciaId)
      if (nomeReferencia.trim()) formData.append('nome', nomeReferencia.trim())

      setSalvandoReferencia(true)
      const salvo = await apiPostFormData<GeometriaReferencia>(`/clientes/${id}/geometria-referencia/importar`, formData)
      await carregar()
      Alert.alert(
        'Arquivo importado',
        `${salvo.nome || arquivo.name} foi importado com ${salvo.resumo?.vertices_total ?? 0} vertices em ${salvo.persistencia === 'supabase' ? 'Supabase' : 'arquivo local'}.`,
      )
    } catch (e: any) {
      Alert.alert('Falha na importação', e?.message ?? 'Não foi possível importar o arquivo. Verifique se o formato é suportado e sua conexão.')
    } finally {
      setSalvandoReferencia(false)
    }
  }

  const removerReferencia = async () => {
    if (!detalhe?.geometria_referencia) {
      Alert.alert('Sem referencia', 'Nao existe uma geometria de referencia salva para remover.')
      return
    }

    confirmarAcao(
      'Excluir referencia?',
      `Remover ${detalhe.geometria_referencia.nome || 'esta geometria'} do cliente e limpar o comparativo atual?`,
      'Excluir',
      async () => {
        try {
          setRemovendoReferencia(true)
          await apiDelete(`/clientes/${id}/geometria-referencia`)
          setManualVerticesTexto('')
          setImportacaoTexto('')
          await carregar()
          Alert.alert('Referencia removida', 'A geometria de referencia do cliente foi removida.')
        } catch (e: any) {
          Alert.alert('Falha ao remover referência', e?.message ?? 'Não foi possível remover a referência. Verifique sua conexão e tente novamente.')
        } finally {
          setRemovendoReferencia(false)
        }
      },
    )
  }

  if (loading) {
    return <View style={[s.centro, { backgroundColor: C.background }]}><ActivityIndicator color={C.primary} size="large" /></View>
  }

  if (erro || !detalhe) {
    return (
      <View style={[s.centro, { backgroundColor: C.background }]}>
        <Text style={[s.msgErro, { color: C.danger }]}>{erro || 'Cliente nao encontrado.'}</Text>
        <TouchableOpacity onPress={() => { setLoading(true); carregar() }} style={[s.btnSecundario, { borderColor: C.primary, marginTop: 16 }]}>
          <Text style={[s.btnSecundarioTxt, { color: C.primary }]}>Tentar novamente</Text>
        </TouchableOpacity>
      </View>
    )
  }

  const status = obterMetaStatus(detalhe.resumo?.status_documentacao)

  return (
    <ScrollView style={[s.container, { backgroundColor: C.background }]} contentContainerStyle={s.content}>
      <View style={[s.header, { backgroundColor: C.card, borderBottomColor: C.cardBorder, paddingTop: Math.max(topInset + 12, 20) }]}>
        <TouchableOpacity onPress={() => router.back()} style={s.voltar} accessibilityRole="button" accessibilityLabel="Voltar para a lista de clientes">
          <Feather name="arrow-left" size={20} color={C.text} />
        </TouchableOpacity>
        <View style={s.headerTexto}>
          <Text style={[s.titulo, { color: C.text }]} numberOfLines={2}>{detalhe.cliente.nome || 'Cliente sem nome'}</Text>
          <Text style={[s.subtitulo, { color: C.muted }]}>{detalhe.cliente.telefone || detalhe.cliente.email || detalhe.cliente.cpf || 'Sem contato cadastrado'}</Text>
        </View>
      </View>

      <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
        <Text style={[s.sectionTitulo, { color: C.text }]}>Status documental</Text>
        <View style={[s.statusPainel, { backgroundColor: `${status.cor}18`, borderColor: status.cor }]}>
          <Text style={[s.statusTitulo, { color: status.cor }]}>{status.titulo}</Text>
          <Text style={[s.statusDescricao, { color: C.text }]}>{status.descricao}</Text>
        </View>
        <View style={s.metricas}>
          <Metrica cor={C.primary} label="Projetos" valor={detalhe.resumo?.projetos_total ?? 0} />
          <Metrica cor={C.info} label="Documentos" valor={detalhe.resumo?.documentos_total ?? 0} />
          <Metrica cor={C.success} label="Confront." valor={detalhe.resumo?.confrontantes_total ?? 0} />
        </View>
        <Text style={[s.metaInfo, { color: C.muted }]}>Formulario recebido: {formatarData(detalhe.resumo?.formulario_em)}</Text>
        <Text style={[s.metaInfo, { color: C.muted }]}>Ultimo documento: {formatarData(detalhe.resumo?.ultimo_documento_em)}</Text>
      </View>

      <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
        <Text style={[s.sectionTitulo, { color: C.text }]}>Alertas e checklist</Text>
        {detalhe.alertas.length === 0 ? (
          <Text style={[s.metaInfo, { color: C.success }]}>Sem pendencias criticas no momento.</Text>
        ) : (
          detalhe.alertas.map((alerta, idx) => (
            <View key={`${alerta.tipo}-${idx}`} style={[s.alertaCard, { borderColor: corAlerta(alerta.nivel, C), backgroundColor: `${corAlerta(alerta.nivel, C)}15` }]}>
              <Text style={[s.alertaTitulo, { color: corAlerta(alerta.nivel, C) }]}>{alerta.titulo}</Text>
              <Text style={[s.metaInfo, { color: C.text }]}>{alerta.descricao}</Text>
            </View>
          ))
        )}

        {detalhe.checklist.map((item) => (
          <View key={item.projeto_id} style={[s.projetoCard, { backgroundColor: C.background, borderColor: C.cardBorder }]}>
            <Text style={[s.projetoTitulo, { color: C.text }]}>{item.projeto_nome || 'Projeto sem nome'}</Text>
            <Text style={[s.metaInfo, { color: C.muted }]}>
              {item.concluidos}/{item.total} itens concluidos ({item.progresso_percentual}%)
            </Text>
            <Text style={[s.metaInfo, { color: item.pendencias.length ? C.muted : C.success }]}>
              {resumirPendencias(item.pendencias)}
            </Text>
            <View style={s.checklistLista}>
              {item.itens.map((check) => (
                <Text key={check.id} style={[s.checkItem, { color: check.ok ? C.success : C.muted }]}>
                  {check.ok ? 'OK' : 'Pendente'} - {check.label}
                </Text>
              ))}
            </View>
          </View>
        ))}
      </View>

      <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
        <Text style={[s.sectionTitulo, { color: C.text }]}>Cadastro do cliente</Text>
        <View style={s.grid}>
          <CampoFormulario label="Nome" valor={form.nome} onChangeText={(valor) => atualizarCampo('nome', valor)} />
          <CampoFormulario label="CPF" valor={form.cpf} onChangeText={(valor) => atualizarCampo('cpf', valor)} />
          <CampoFormulario label="RG" valor={form.rg} onChangeText={(valor) => atualizarCampo('rg', valor)} />
          <CampoFormulario label="Estado civil" valor={form.estado_civil} onChangeText={(valor) => atualizarCampo('estado_civil', valor)} />
          <CampoFormulario label="Profissao" valor={form.profissao} onChangeText={(valor) => atualizarCampo('profissao', valor)} />
          <CampoFormulario label="Telefone" valor={form.telefone} onChangeText={(valor) => atualizarCampo('telefone', valor)} keyboardType="phone-pad" />
          <CampoFormulario label="Email" valor={form.email} onChangeText={(valor) => atualizarCampo('email', valor)} keyboardType="email-address" />
          <CampoFormulario label="Endereco" valor={form.endereco} onChangeText={(valor) => atualizarCampo('endereco', valor)} />
          <CampoFormulario label="Numero" valor={form.endereco_numero} onChangeText={(valor) => atualizarCampo('endereco_numero', valor)} />
          <CampoFormulario label="Municipio" valor={form.municipio} onChangeText={(valor) => atualizarCampo('municipio', valor)} />
          <CampoFormulario label="Estado" valor={form.estado} onChangeText={(valor) => atualizarCampo('estado', valor)} autoCapitalize="characters" />
          <CampoFormulario label="Setor" valor={form.setor} onChangeText={(valor) => atualizarCampo('setor', valor)} />
          <CampoFormulario label="CEP" valor={form.cep} onChangeText={(valor) => atualizarCampo('cep', valor)} keyboardType="number-pad" />
          <CampoFormulario label="Conjuge" valor={form.conjuge_nome} onChangeText={(valor) => atualizarCampo('conjuge_nome', valor)} />
          <CampoFormulario label="CPF do conjuge" valor={form.conjuge_cpf} onChangeText={(valor) => atualizarCampo('conjuge_cpf', valor)} />
        </View>
        <TouchableOpacity style={[s.btnPrimario, { backgroundColor: salvando ? C.primaryDark : C.primary }]} onPress={salvarCadastro} disabled={salvando}>
          {salvando ? <ActivityIndicator color={C.primaryText} /> : <Text style={[s.btnPrimarioTxt, { color: C.primaryText }]}>Salvar cadastro</Text>}
        </TouchableOpacity>
      </View>

      <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}> 
        <Text style={[s.sectionTitulo, { color: C.text }]}>Projetos vinculados</Text>
        {detalhe.projetos.map((projeto) => {
          const proximaAcao = obterProximaAcaoProjeto(projeto)
          return (
            <View key={projeto.id} style={[s.projetoCard, { backgroundColor: C.background, borderColor: C.cardBorder }]}> 
              <View style={s.projetoTopo}>
                <View style={s.projetoTopoTexto}>
                  <Text style={[s.projetoTitulo, { color: C.text }]}>{projeto.projeto_nome || 'Projeto sem nome'}</Text>
                  <Text style={[s.metaInfo, { color: C.muted }]}>{[projeto.municipio, projeto.estado].filter(Boolean).join(' / ') || 'Localizacao nao informada'}</Text>
                </View>
                <StatusBadge status={projeto.status} />
              </View>
              <Text style={[s.metaInfo, { color: C.muted }]}>Tipos: {chipDocumentos(projeto.documentos_tipos)}</Text>
              <View style={[s.proximaAcaoCard, { borderColor: proximaAcao.cor, backgroundColor: `${proximaAcao.cor}15` }]}> 
                <Text style={[s.proximaAcaoLabel, { color: proximaAcao.cor }]}>Próxima ação</Text>
                <Text style={[s.metaInfo, { color: C.text, fontWeight: '700' }]}>{proximaAcao.titulo}</Text>
                <Text style={[s.metaInfo, { color: C.muted }]}>{proximaAcao.descricao}</Text>
              </View>
              {projeto.magic_link_expira ? (() => {
                const expira = new Date(projeto.magic_link_expira)
                const hoje = new Date()
                hoje.setHours(0, 0, 0, 0)
                expira.setHours(0, 0, 0, 0)
                const diasRestantes = Math.round((expira.getTime() - hoje.getTime()) / 86400000)
                const expirado = diasRestantes < 0
                return (
                  <View style={[s.magicLinkStatus, { backgroundColor: expirado ? `${C.danger}18` : `${C.success}18`, borderColor: expirado ? C.danger : C.success }]}> 
                    <Text style={[s.metaInfo, { color: expirado ? C.danger : C.success, fontWeight: '700' }]}>
                      {expirado ? 'Link expirado' : `Válido até ${expira.toLocaleDateString('pt-BR')} · Expira em ${diasRestantes} dia${diasRestantes === 1 ? '' : 's'}`}
                    </Text>
                  </View>
                )
              })() : null}
              <View style={[s.projetoAcoes, s.projetoAcoesWrap]}>
                <TouchableOpacity style={[s.btnSecundario, s.projetoAcaoBtn, { borderColor: C.success }]} onPress={() => abrirMapaProjeto(projeto.id)}>
                  <Text style={[s.btnSecundarioTxt, { color: C.success }]}>Ver no mapa</Text>
                </TouchableOpacity>
                <TouchableOpacity style={[s.btnSecundario, s.projetoAcaoBtn, { borderColor: C.info }]} onPress={() => router.push(`/(tabs)/projeto/${projeto.id}` as any)}>
                  <Text style={[s.btnSecundarioTxt, { color: C.info }]}>Abrir projeto</Text>
                </TouchableOpacity>
                {(() => {
                  const expira = projeto.magic_link_expira ? new Date(projeto.magic_link_expira) : null
                  const hoje = new Date()
                  hoje.setHours(0, 0, 0, 0)
                  if (expira) expira.setHours(0, 0, 0, 0)
                  const expirado = expira ? expira.getTime() < hoje.getTime() : false
                  return (
                    <TouchableOpacity style={[s.btnSecundario, s.projetoAcaoBtn, { borderColor: expirado ? C.danger : C.primary }]} onPress={() => reenviarMagicLink(projeto)} disabled={reenviandoProjetoId === projeto.id}>
                      {reenviandoProjetoId === projeto.id
                        ? <ActivityIndicator color={expirado ? C.danger : C.primary} />
                        : <Text style={[s.btnSecundarioTxt, { color: expirado ? C.danger : C.primary }]}>{expirado ? 'Renovar link' : 'Reenviar magic link'}</Text>}
                    </TouchableOpacity>
                  )
                })()}
              </View>
            </View>
          )
        })}
      </View>

      <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}> 
        <Text style={[s.sectionTitulo, { color: C.text }]}>Confrontantes e vizinhos</Text>
        <ProjetoSelector projetos={detalhe.projetos} projetoId={projetoConfrontanteId} onSelect={setProjetoConfrontanteId} />
        <View style={s.grid}>
          <CampoFormulario label="Nome" valor={formConfrontante.nome} onChangeText={(valor) => atualizarCampoConfrontante('nome', valor)} />
          <CampoFormulario label="CPF" valor={formConfrontante.cpf} onChangeText={(valor) => atualizarCampoConfrontante('cpf', valor)} />
          <CampoFormulario label="Imovel" valor={formConfrontante.nome_imovel} onChangeText={(valor) => atualizarCampoConfrontante('nome_imovel', valor)} />
          <CampoFormulario label="Matricula" valor={formConfrontante.matricula} onChangeText={(valor) => atualizarCampoConfrontante('matricula', valor)} />
          <CampoFormulario label="Lado" valor={formConfrontante.lado} onChangeText={(valor) => atualizarCampoConfrontante('lado', valor)} />
          <CampoFormulario label="Tipo" valor={formConfrontante.tipo} onChangeText={(valor) => atualizarCampoConfrontante('tipo', valor)} />
        </View>
        <View style={s.projetoAcoes}>
          <TouchableOpacity style={[s.btnPrimario, { flex: 1, backgroundColor: salvandoConfrontante ? C.primaryDark : C.primary }]} onPress={salvarConfrontante} disabled={salvandoConfrontante}>
            {salvandoConfrontante ? <ActivityIndicator color={C.primaryText} /> : <Text style={[s.btnPrimarioTxt, { color: C.primaryText }]}>{confrontanteEditandoId ? 'Atualizar confrontante' : 'Adicionar confrontante'}</Text>}
          </TouchableOpacity>
          {confrontanteEditandoId ? (
            <TouchableOpacity style={[s.btnSecundario, { borderColor: C.muted, flex: 1 }]} onPress={limparConfrontante}>
              <Text style={[s.btnSecundarioTxt, { color: C.muted }]}>Cancelar edicao</Text>
            </TouchableOpacity>
          ) : null}
        </View>
        {detalhe.confrontantes.length === 0 ? (
          <Text style={[s.metaInfo, { color: C.muted }]}>Nenhum confrontante cadastrado ainda.</Text>
        ) : (
          detalhe.projetos.map((projeto) => (
            <View key={`confs-${projeto.id}`} style={{ gap: 8 }}>
              <Text style={[s.subSectionTitulo, { color: C.text }]}>{projeto.projeto_nome}</Text>
              {(confrontantesPorProjeto[projeto.id] || []).map((item) => (
                <View key={item.id} style={[s.confrontanteCard, { backgroundColor: C.background, borderColor: C.cardBorder }]}>
                  <Text style={[s.projetoTitulo, { color: C.text }]}>{item.nome || 'Confrontante sem nome'}</Text>
                  <Text style={[s.metaInfo, { color: C.muted }]}>{[item.lado, item.tipo, item.nome_imovel].filter(Boolean).join(' | ') || 'Sem detalhes'}</Text>
                  <View style={s.projetoAcoes}>
                    <TouchableOpacity style={[s.btnSecundario, { borderColor: C.info }]} onPress={() => iniciarEdicaoConfrontante(item)}>
                      <Text style={[s.btnSecundarioTxt, { color: C.info }]}>Editar</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={[s.btnSecundario, { borderColor: C.danger }]} onPress={() => excluirConfrontante(item)}>
                      <Text style={[s.btnSecundarioTxt, { color: C.danger }]}>Excluir</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              ))}
            </View>
          ))
        )}
      </View>

      <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
        <Text style={[s.sectionTitulo, { color: C.text }]}>Area de referencia do cliente</Text>
        <ProjetoSelector projetos={detalhe.projetos} projetoId={projetoReferenciaId} onSelect={setProjetoReferenciaId} />
        <CampoFormulario label="Nome da referencia" valor={nomeReferencia} onChangeText={setNomeReferencia} />
        {detalhe.geometria_referencia ? (
          <>
            <Text style={[s.metaInfo, { color: C.muted }]}>Origem: {detalhe.geometria_referencia.origem_tipo} | formato: {detalhe.geometria_referencia.formato} | salvo em: {formatarData(detalhe.geometria_referencia.atualizado_em)}</Text>
            <Text style={[s.metaInfo, { color: C.muted }]}>Vertices: {detalhe.geometria_referencia.resumo?.vertices_total ?? 0} | area: {detalhe.geometria_referencia.resumo?.area_ha ?? 0} ha | perimetro: {detalhe.geometria_referencia.resumo?.perimetro_m ?? 0} m</Text>
            <Text style={[s.metaInfo, { color: C.muted }]}>Persistencia: {detalhe.geometria_referencia.persistencia === 'supabase' ? 'Supabase' : 'Arquivo local'}</Text>
            <ClienteGeometryPreview
              referencia={detalhe.geometria_referencia.vertices}
              tecnico={detalhe.geometria_referencia.comparativo?.perimetro_tecnico?.vertices}
            />
            {detalhe.geometria_referencia.comparativo ? (
              <View style={[s.alertaCard, { borderColor: C.info, backgroundColor: `${C.info}15` }]}>
                <Text style={[s.alertaTitulo, { color: C.info }]}>Comparativo com perimetro tecnico</Text>
                <Text style={[s.metaInfo, { color: C.text }]}>Status: {detalhe.geometria_referencia.comparativo.status}</Text>
                <Text style={[s.metaInfo, { color: C.text }]}>Sobreposicao: {detalhe.geometria_referencia.comparativo.sobreposicao_percentual ?? 0}%</Text>
                <Text style={[s.metaInfo, { color: C.text }]}>Diferenca de area: {detalhe.geometria_referencia.comparativo.diferenca_area_ha ?? 0} ha</Text>
              </View>
            ) : null}
            <TouchableOpacity style={[s.btnSecundario, { borderColor: C.danger }]} onPress={removerReferencia} disabled={removendoReferencia}>
              {removendoReferencia ? <ActivityIndicator color={C.danger} /> : <Text style={[s.btnSecundarioTxt, { color: C.danger }]}>Excluir referencia salva</Text>}
            </TouchableOpacity>
          </>
        ) : (
          <View style={[s.vazioGeo, { borderColor: C.cardBorder, backgroundColor: C.background }]}>
            <Text style={[s.metaInfo, { color: C.text }]}>Nenhuma referencia salva ainda.</Text>
            <Text style={[s.metaInfo, { color: C.muted }]}>Use desenho manual, colagem de texto ou arquivo para iniciar o comparativo.</Text>
          </View>
        )}

        <Text style={[s.subSectionTitulo, { color: C.text }]}>Salvar desenho manual</Text>
        <TextInput style={[s.inputMulti, { backgroundColor: C.background, color: C.text, borderColor: C.cardBorder }]} multiline value={manualVerticesTexto} onChangeText={setManualVerticesTexto} placeholder="Uma linha por vertice: lon,lat ou lat,lon" placeholderTextColor={C.muted} />
        <TouchableOpacity style={[s.btnPrimario, { backgroundColor: salvandoReferencia ? C.primaryDark : C.primary }]} onPress={salvarReferenciaManual} disabled={salvandoReferencia}>
          <Text style={[s.btnPrimarioTxt, { color: C.primaryText }]}>Salvar referencia manual</Text>
        </TouchableOpacity>

        <Text style={[s.subSectionTitulo, { color: C.text }]}>Importar por conteudo</Text>
        <View style={s.formatoRow}>
          {(['geojson', 'kml', 'csv', 'txt'] as const).map((formato) => (
            <TouchableOpacity key={formato} style={[s.chip, { borderColor: C.cardBorder, backgroundColor: formatoImportacao === formato ? C.primary : C.background }]} onPress={() => setFormatoImportacao(formato)}>
              <Text style={{ color: formatoImportacao === formato ? C.primaryText : C.muted, fontWeight: '700', fontSize: 12 }}>{formato.toUpperCase()}</Text>
            </TouchableOpacity>
          ))}
        </View>
        <TextInput style={[s.inputMulti, { backgroundColor: C.background, color: C.text, borderColor: C.cardBorder }]} multiline value={importacaoTexto} onChangeText={setImportacaoTexto} placeholder="Cole aqui o conteudo GeoJSON, KML, CSV ou TXT" placeholderTextColor={C.muted} />
        <View style={s.projetoAcoes}>
          <TouchableOpacity style={[s.btnPrimario, { flex: 1, backgroundColor: salvandoReferencia ? C.primaryDark : C.primary }]} onPress={importarReferenciaTexto} disabled={salvandoReferencia}>
            <Text style={[s.btnPrimarioTxt, { color: C.primaryText }]}>Importar texto</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[s.btnSecundario, { flex: 1, borderColor: C.info }]} onPress={importarReferenciaArquivo} disabled={salvandoReferencia}>
            <Text style={[s.btnSecundarioTxt, { color: C.info }]}>Selecionar arquivo</Text>
          </TouchableOpacity>
        </View>
        <Text style={[s.metaInfo, { color: C.muted }]}>Arquivos aceitos: KML, GeoJSON/JSON, CSV, TXT e SHP em .zip.</Text>
      </View>

      <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
        <Text style={[s.sectionTitulo, { color: C.text }]}>Timeline do atendimento</Text>
        {detalhe.timeline.map((evento, idx) => (
          <View key={`${evento.tipo}-${idx}`} style={s.timelineItem}>
            <View style={[s.timelineDot, { backgroundColor: C.primary }]} />
            <View style={s.timelineConteudo}>
              <Text style={[s.projetoTitulo, { color: C.text }]}>{evento.titulo}</Text>
              <Text style={[s.metaInfo, { color: C.muted }]}>{evento.descricao}</Text>
              <Text style={[s.metaInfo, { color: C.muted }]}>{formatarData(evento.em)}</Text>
            </View>
          </View>
        ))}
      </View>
    </ScrollView>
  )
}

function CampoFormulario({
  label,
  valor,
  onChangeText,
  keyboardType,
  autoCapitalize,
}: {
  label: string
  valor: string
  onChangeText: (valor: string) => void
  keyboardType?: 'default' | 'email-address' | 'number-pad' | 'phone-pad'
  autoCapitalize?: 'none' | 'sentences' | 'words' | 'characters'
}) {
  const C = Colors.dark
  return (
    <View style={s.campoBox}>
      <Text style={[s.campoLabel, { color: C.muted }]}>{label}</Text>
      <TextInput style={[s.input, { backgroundColor: C.background, color: C.text, borderColor: C.cardBorder }]} value={valor} onChangeText={onChangeText} keyboardType={keyboardType || 'default'} autoCapitalize={autoCapitalize || 'words'} placeholder={label} placeholderTextColor={C.muted} />
    </View>
  )
}

function ProjetoSelector({ projetos, projetoId, onSelect }: { projetos: ProjetoCliente[]; projetoId: string; onSelect: (id: string) => void }) {
  const C = Colors.dark
  return (
    <View style={s.formatoRow}>
      {projetos.map((projeto) => (
        <TouchableOpacity key={projeto.id} style={[s.chip, { borderColor: C.cardBorder, backgroundColor: projetoId === projeto.id ? C.primary : C.background }]} onPress={() => onSelect(projeto.id)}>
          <Text style={{ color: projetoId === projeto.id ? C.primaryText : C.muted, fontWeight: '700', fontSize: 12 }}>{projeto.projeto_nome || 'Projeto'}</Text>
        </TouchableOpacity>
      ))}
    </View>
  )
}

function Metrica({ cor, label, valor }: { cor: string; label: string; valor: number }) {
  const C = Colors.dark
  return <View style={[s.metrica, { backgroundColor: C.background }]}><Text style={[s.metricaValor, { color: cor }]}>{valor}</Text><Text style={[s.metricaLabel, { color: C.muted }]}>{label}</Text></View>
}

function corAlerta(nivel: Alerta['nivel'], C: typeof Colors.dark) {
  if (nivel === 'alto') return C.danger
  if (nivel === 'medio') return C.primary
  return C.info
}

const s = StyleSheet.create({
  container: { flex: 1 },
  content: { paddingBottom: 24 },
  centro: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  msgErro: { fontSize: 14, textAlign: 'center', lineHeight: 22 },
  header: { paddingTop: 0, paddingHorizontal: 20, paddingBottom: 18, borderBottomWidth: 0.5, flexDirection: 'row', gap: 14, alignItems: 'flex-start' },
  voltar: { width: 38, height: 38, borderRadius: 19, alignItems: 'center', justifyContent: 'center' },
  headerTexto: { flex: 1, gap: 4 },
  titulo: { fontSize: 22, fontWeight: '700' },
  subtitulo: { fontSize: 13 },
  card: { marginHorizontal: 14, marginTop: 14, borderWidth: 0.5, borderRadius: 14, padding: 14, gap: 12 },
  sectionTitulo: { fontSize: 16, fontWeight: '700' },
  subSectionTitulo: { fontSize: 14, fontWeight: '700' },
  statusPainel: { borderWidth: 1, borderRadius: 12, padding: 12, gap: 6 },
  statusTitulo: { fontSize: 14, fontWeight: '700' },
  statusDescricao: { fontSize: 13, lineHeight: 20 },
  metricas: { flexDirection: 'row', gap: 8 },
  metrica: { flex: 1, borderRadius: 10, paddingVertical: 12, paddingHorizontal: 10, alignItems: 'center' },
  metricaValor: { fontSize: 18, fontWeight: '700' },
  metricaLabel: { fontSize: 11, marginTop: 2 },
  metaInfo: { fontSize: 12, lineHeight: 18 },
  alertaCard: { borderWidth: 1, borderRadius: 12, padding: 12, gap: 6 },
  alertaTitulo: { fontSize: 13, fontWeight: '700' },
  checklistLista: { gap: 4 },
  checkItem: { fontSize: 12 },
  grid: { gap: 10 },
  campoBox: { gap: 6 },
  campoLabel: { fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5 },
  input: { borderWidth: 1, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 12, fontSize: 14 },
  inputMulti: { borderWidth: 1, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 12, fontSize: 14, minHeight: 120, textAlignVertical: 'top' },
  btnPrimario: { borderRadius: 10, minHeight: 48, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 14 },
  btnPrimarioTxt: { fontSize: 14, fontWeight: '700', textAlign: 'center' },
  projetoCard: { borderWidth: 0.5, borderRadius: 12, padding: 12, gap: 8 },
  confrontanteCard: { borderWidth: 0.5, borderRadius: 12, padding: 12, gap: 8 },
  vazioGeo: { borderWidth: 0.5, borderRadius: 12, padding: 12, gap: 4 },
  proximaAcaoCard: { borderWidth: 1, borderRadius: 12, padding: 12, gap: 4 },
  proximaAcaoLabel: { fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.6, fontWeight: '700' },
  projetoTopo: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 },
  projetoTopoTexto: { flex: 1, gap: 4 },
  projetoTitulo: { fontSize: 15, fontWeight: '700' },
  projetoAcoes: { flexDirection: 'row', gap: 10 },
  projetoAcoesWrap: { flexWrap: 'wrap' },
  projetoAcaoBtn: { minWidth: 148, flexGrow: 1 },
  btnSecundario: { flex: 1, minHeight: 46, borderRadius: 10, borderWidth: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 12 },
  btnSecundarioTxt: { fontSize: 13, fontWeight: '700', textAlign: 'center' },
  formatoRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 8 },
  timelineItem: { flexDirection: 'row', gap: 10, alignItems: 'flex-start' },
  timelineDot: { width: 10, height: 10, borderRadius: 999, marginTop: 6 },
  timelineConteudo: { flex: 1, gap: 3, paddingBottom: 10 },
  magicLinkStatus: { borderWidth: 1, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 6 },
})




