import { useState } from 'react'
import {
  Alert,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native'
import * as DocumentPicker from 'expo-document-picker'
import { useRouter } from 'expo-router'
import { Colors } from '../../../constants/Colors'
import { apiPost, apiPostFormData } from '../../../lib/api'

type PapelParticipante = 'principal' | 'coproprietario' | 'possuidor' | 'herdeiro' | 'representante' | 'outro'
type OrigemArquivo = 'topografo' | 'cliente' | 'escritorio' | 'sistema'
type ClassificacaoArquivo = 'referencia_visual' | 'esboco_area' | 'perimetro_tecnico' | 'camada_auxiliar' | 'documento_croqui'

type FormProjeto = {
  nome: string
  municipio: string
  estado: string
  status: string
  zona_utm: string
}

type ParticipanteProjeto = {
  id: string
  nome: string
  cpf: string
  telefone: string
  papel: PapelParticipante
  gerar_magic_link: boolean
}

type ArquivoBase = {
  id: string
  nome: string
  uri: string
  mimeType?: string | null
  origem: OrigemArquivo
  classificacao: ClassificacaoArquivo
}

type ProjetoCriado = {
  id: string
  magic_link?: { link?: string }
}

const STATUS = [
  { label: 'Medição', value: 'medicao' },
  { label: 'Montagem', value: 'montagem' },
  { label: 'Protocolado', value: 'protocolado' },
]

const PAPEL_OPTIONS: Array<{ label: string; value: PapelParticipante }> = [
  { label: 'Principal', value: 'principal' },
  { label: 'Coproprietário', value: 'coproprietario' },
  { label: 'Possuidor', value: 'possuidor' },
  { label: 'Herdeiro', value: 'herdeiro' },
  { label: 'Representante', value: 'representante' },
  { label: 'Outro', value: 'outro' },
]

const ORIGEM_OPTIONS: Array<{ label: string; value: OrigemArquivo }> = [
  { label: 'Topógrafo', value: 'topografo' },
  { label: 'Cliente', value: 'cliente' },
  { label: 'Escritório', value: 'escritorio' },
  { label: 'Sistema', value: 'sistema' },
]

const CLASSIFICACAO_OPTIONS: Array<{ label: string; value: ClassificacaoArquivo }> = [
  { label: 'Referência', value: 'referencia_visual' },
  { label: 'Esboço', value: 'esboco_area' },
  { label: 'Perímetro', value: 'perimetro_tecnico' },
  { label: 'Camada', value: 'camada_auxiliar' },
  { label: 'Croqui', value: 'documento_croqui' },
]

function novoId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

function criarParticipanteInicial(): ParticipanteProjeto {
  return {
    id: novoId(),
    nome: '',
    cpf: '',
    telefone: '',
    papel: 'principal',
    gerar_magic_link: true,
  }
}

function criarParticipanteAdicional(): ParticipanteProjeto {
  return {
    id: novoId(),
    nome: '',
    cpf: '',
    telefone: '',
    papel: 'coproprietario',
    gerar_magic_link: false,
  }
}



function normalizarCpf(valor: string) {
  return valor.replace(/\D+/g, '').slice(0, 11)
}

function inferirMimeTypeArquivo(nome: string, mimeType?: string | null) {
  if (mimeType) return mimeType

  const extensao = nome.split('.').pop()?.toLowerCase()
  if (extensao === 'geojson' || extensao === 'json') return 'application/json'
  if (extensao === 'kml') return 'application/vnd.google-earth.kml+xml'
  if (extensao === 'kmz') return 'application/vnd.google-earth.kmz'
  if (extensao === 'csv') return 'text/csv'
  if (extensao === 'txt') return 'text/plain'
  if (extensao === 'zip') return 'application/zip'
  if (extensao === 'dxf') return 'application/dxf'
  if (extensao === 'pdf') return 'application/pdf'
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

function chipStyleAtivo(ativo: boolean, C: typeof Colors.dark) {
  return ativo
    ? { backgroundColor: C.primary, borderColor: C.primary }
    : { backgroundColor: C.background, borderColor: C.cardBorder }
}

export default function NovoProjetoScreen() {
  const C = Colors.dark
  const router = useRouter()
  const [salvando, setSalvando] = useState(false)
  const [form, setForm] = useState<FormProjeto>({
    nome: '',
    municipio: '',
    estado: 'GO',
    status: 'medicao',
    zona_utm: '23S',
  })
  const [participantes, setParticipantes] = useState<ParticipanteProjeto[]>([criarParticipanteInicial()])
  const [arquivosBase, setArquivosBase] = useState<ArquivoBase[]>([])

  const atualizar = (campo: keyof FormProjeto, valor: string) => {
    setForm((atual) => ({ ...atual, [campo]: valor }))
  }

  const atualizarParticipante = (
    id: string,
    campo: keyof Omit<ParticipanteProjeto, 'id'>,
    valor: string | boolean,
  ) => {
    setParticipantes((atual) =>
      atual.map((item) => (item.id === id ? { ...item, [campo]: valor } : item)),
    )
  }

  const adicionarParticipante = () => {
    setParticipantes((atual) => [...atual, criarParticipanteAdicional()])
  }

  const removerParticipante = (id: string) => {
    setParticipantes((atual) => (atual.length > 1 ? atual.filter((item) => item.id !== id) : atual))
  }

  const adicionarArquivo = async () => {
    try {
      const resultado = await DocumentPicker.getDocumentAsync({
        type: '*/*',
        copyToCacheDirectory: true,
        base64: false,
      })

      if (resultado.canceled || !resultado.assets?.length) {
        return
      }

      const asset = resultado.assets[0]
      setArquivosBase((atual) => [
        ...atual,
        {
          id: novoId(),
          nome: asset.name || 'arquivo-sem-nome',
          uri: asset.uri,
          mimeType: asset.mimeType ?? null,
          origem: 'topografo',
          classificacao: 'referencia_visual',
        },
      ])
    } catch (error: any) {
      Alert.alert('Falha ao escolher arquivo', error?.message || 'Nao foi possivel abrir o seletor de arquivos.')
    }
  }

  const atualizarArquivo = (id: string, campo: keyof Omit<ArquivoBase, 'id'>, valor: string) => {
    setArquivosBase((atual) =>
      atual.map((item) => {
        if (item.id !== id) return item
        if (campo === 'origem' || campo === 'classificacao') {
          return { ...item, [campo]: valor }
        }
        return { ...item, [campo]: valor }
      }),
    )
  }

  const removerArquivo = (id: string) => {
    setArquivosBase((atual) => atual.filter((item) => item.id !== id))
  }

  const enviarArquivoCartografico = async (projetoId: string, arquivo: ArquivoBase) => {
    const asset = {
      name: arquivo.nome,
      uri: arquivo.uri,
      mimeType: arquivo.mimeType ?? inferirMimeTypeArquivo(arquivo.nome, arquivo.mimeType),
    } as DocumentPicker.DocumentPickerAsset

    const formData = new FormData()
    await anexarArquivoNoFormData(formData, asset)
    formData.append('nome', arquivo.nome)
    formData.append('origem', arquivo.origem)
    formData.append('classificacao', arquivo.classificacao)
    formData.append('mime_type', arquivo.mimeType || inferirMimeTypeArquivo(arquivo.nome, arquivo.mimeType))
    formData.append('nome_arquivo', arquivo.nome)

    await apiPostFormData(`/projetos/${projetoId}/arquivos`, formData)
  }

  const salvar = async () => {
    if (!form.nome.trim()) {
      Alert.alert('Projeto sem nome', 'Informe o nome do projeto antes de continuar.')
      return
    }

    setSalvando(true)
    try {
      const participantesValidos = participantes
        .map((item, indice) => ({
          id: item.id,
          nome: item.nome.trim(),
          cpf: normalizarCpf(item.cpf),
          telefone: item.telefone.trim(),
          papel: item.papel,
          gerar_magic_link: item.gerar_magic_link,
          principal: indice === 0,
          ordem: indice,
        }))
        .filter((item) => item.nome || item.cpf || item.telefone)

      const principal = participantesValidos[0]
      const projeto = await apiPost<ProjetoCriado>('/projetos', {
        nome: form.nome,
        municipio: form.municipio || null,
        estado: form.estado || null,
        status: form.status,
        zona_utm: form.zona_utm,
        cliente_nome: principal?.nome || null,
        cliente_cpf: principal?.cpf || null,
        cliente_telefone: principal?.telefone || null,
        gerar_magic_link: principal?.gerar_magic_link ?? false,
        participantes: participantesValidos,
      })

      let enviados = 0
      const falhas: string[] = []
      for (const arquivo of arquivosBase) {
        try {
          await enviarArquivoCartografico(projeto.id, arquivo)
          enviados += 1
        } catch {
          falhas.push(arquivo.nome)
        }
      }

      const possuiMagicLink = Boolean(projeto.magic_link?.link)
      if (arquivosBase.length > 0 && falhas.length > 0) {
        Alert.alert(
          'Projeto criado',
          `${participantesValidos.length > 0 ? 'Participantes enviados.' : 'Projeto salvo sem participantes.'} ${enviados}/${arquivosBase.length} arquivo(s) foram enviados. Alguns anexos nao responderam ainda.`.trim(),
        )
      } else if (arquivosBase.length > 0) {
        Alert.alert(
          'Projeto criado',
          `${participantesValidos.length > 0 ? 'Participantes enviados.' : 'Projeto salvo sem participantes.'} ${enviados} arquivo(s) cartograficos enviados.`.trim() + (possuiMagicLink ? ' Magic link pronto para o cliente principal.' : ''),
        )
      } else {
        Alert.alert(
          'Projeto criado',
          possuiMagicLink
            ? 'Projeto criado e magic link preparado para o cliente principal.'
            : 'Projeto criado com sucesso.',
        )
      }

      router.replace(`/(tabs)/projeto/${projeto.id}` as any)
    } catch (error: any) {
      Alert.alert('Erro', error?.message || 'Nao foi possivel criar o projeto agora.')
    } finally {
      setSalvando(false)
    }
  }

  return (
    <ScrollView style={[s.container, { backgroundColor: C.background }]} contentContainerStyle={s.content}>
      <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}> 
        <Text style={[s.title, { color: C.text }]}>Novo projeto</Text>
        <Text style={[s.subtitle, { color: C.muted }]}>Abra o processo com os participantes certos e, se quiser, já deixe a base cartografica inicial pronta para o topografo.</Text>

        <View style={s.field}>
          <Text style={[s.label, { color: C.muted }]}>Nome do projeto</Text>
          <TextInput style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]} value={form.nome} onChangeText={(v) => atualizar('nome', v)} placeholder="Ex.: Fazenda Boa Vista" placeholderTextColor={C.muted} />
        </View>

        <View style={s.row}>
          <View style={[s.field, s.flex]}>
            <Text style={[s.label, { color: C.muted }]}>Município</Text>
            <TextInput style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]} value={form.municipio} onChangeText={(v) => atualizar('municipio', v)} placeholder="Município" placeholderTextColor={C.muted} />
          </View>
          <View style={[s.field, s.ufField]}>
            <Text style={[s.label, { color: C.muted }]}>UF</Text>
            <TextInput style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]} value={form.estado} onChangeText={(v) => atualizar('estado', v.toUpperCase())} placeholder="UF" placeholderTextColor={C.muted} maxLength={2} />
          </View>
        </View>

        <Text style={[s.section, { color: C.text }]}>Status inicial</Text>
        <View style={s.chipsRow}>
          {STATUS.map((item) => {
            const ativo = form.status === item.value
            return (
              <TouchableOpacity key={item.value} style={[s.chip, chipStyleAtivo(ativo, C)]} onPress={() => atualizar('status', item.value)}>
                <Text style={{ color: ativo ? C.primaryText : C.text, fontWeight: '700', fontSize: 13 }}>{item.label}</Text>
              </TouchableOpacity>
            )
          })}
        </View>

        <View style={s.field}>
          <Text style={[s.label, { color: C.muted }]}>Zona UTM</Text>
          <TextInput style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]} value={form.zona_utm} onChangeText={(v) => atualizar('zona_utm', v.toUpperCase())} placeholder="23S" placeholderTextColor={C.muted} />
        </View>
      </View>

      <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}> 
        <View style={s.sectionHeader}>
          <View style={{ flex: 1 }}>
            <Text style={[s.title, { color: C.text }]}>Participantes do projeto</Text>
            <Text style={[s.subtitle, { color: C.muted }]}>Cliente principal + outros envolvidos. Cada participante pode receber um magic link próprio.</Text>
          </View>
          <TouchableOpacity style={[s.smallButton, { borderColor: C.cardBorder, backgroundColor: C.background }]} onPress={adicionarParticipante}>
            <Text style={[s.smallButtonTxt, { color: C.text }]}>+ Adicionar outro cliente</Text>
          </TouchableOpacity>
        </View>

        {participantes.map((participante, indice) => {
          const principal = indice === 0
          return (
            <View key={participante.id} style={[s.participantCard, { borderColor: C.cardBorder, backgroundColor: C.background }]}> 
              <View style={s.participantHeader}>
                <View>
                  <Text style={[s.participantTitle, { color: C.text }]}>{principal ? 'Cliente principal' : `Participante ${indice + 1}`}</Text>
                  <Text style={[s.participantSubtitle, { color: C.muted }]}>{principal ? 'Responsável principal do processo.' : 'Vincule coproprietários, possuidores, herdeiros ou representantes.'}</Text>
                </View>
                <View style={[s.badge, { borderColor: C.cardBorder }]}>
                  <Text style={[s.badgeTxt, { color: C.text }]}>{principal ? 'Principal' : 'Adicional'}</Text>
                </View>
              </View>

              <View style={s.field}>
                <Text style={[s.label, { color: C.muted }]}>Nome</Text>
                <TextInput
                  style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.card }]}
                  value={participante.nome}
                  onChangeText={(v) => atualizarParticipante(participante.id, 'nome', v)}
                  placeholder="Nome completo"
                  placeholderTextColor={C.muted}
                />
              </View>

              <View style={s.row}>
                <View style={[s.field, s.flex]}>
                  <Text style={[s.label, { color: C.muted }]}>CPF</Text>
                  <TextInput
                    style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.card }]}
                    value={participante.cpf}
                    onChangeText={(v) => atualizarParticipante(participante.id, 'cpf', v)}
                    placeholder="000.000.000-00"
                    placeholderTextColor={C.muted}
                    keyboardType="number-pad"
                  />
                </View>
                <View style={[s.field, s.flex]}>
                  <Text style={[s.label, { color: C.muted }]}>Telefone</Text>
                  <TextInput
                    style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.card }]}
                    value={participante.telefone}
                    onChangeText={(v) => atualizarParticipante(participante.id, 'telefone', v)}
                    placeholder="(00) 00000-0000"
                    placeholderTextColor={C.muted}
                    keyboardType="phone-pad"
                  />
                </View>
              </View>

              {!principal && (
                <View style={s.field}>
                  <Text style={[s.label, { color: C.muted }]}>Papel no projeto</Text>
                  <View style={s.chipsRow}>
                    {PAPEL_OPTIONS.filter((item) => item.value !== 'principal').map((item) => {
                      const ativo = participante.papel === item.value
                      return (
                        <TouchableOpacity
                          key={item.value}
                          style={[s.chip, chipStyleAtivo(ativo, C)]}
                          onPress={() => atualizarParticipante(participante.id, 'papel', item.value)}
                        >
                          <Text style={{ color: ativo ? C.primaryText : C.text, fontWeight: '700', fontSize: 12 }}>{item.label}</Text>
                        </TouchableOpacity>
                      )
                    })}
                  </View>
                </View>
              )}

              {principal && (
                <View style={s.roleInline}>
                  <Text style={[s.roleLabel, { color: C.muted }]}>Papel no projeto</Text>
                  <Text style={[s.roleValue, { color: C.text }]}>Principal</Text>
                </View>
              )}

              <TouchableOpacity
                style={[s.toggleCard, { borderColor: C.cardBorder, backgroundColor: participante.gerar_magic_link ? `${C.primary}22` : C.card }]}
                onPress={() => atualizarParticipante(participante.id, 'gerar_magic_link', !participante.gerar_magic_link)}
              >
                <View style={[s.toggleBullet, { backgroundColor: participante.gerar_magic_link ? C.primary : C.cardBorder }]} />
                <View style={{ flex: 1 }}>
                  <Text style={[s.toggleTitle, { color: C.text }]}>Gerar magic link para este participante</Text>
                  <Text style={[s.toggleSubtitle, { color: C.muted }]}>Se marcado, esse cliente entra no fluxo de acesso e preenchimento.</Text>
                </View>
              </TouchableOpacity>

              {!principal && (
                <TouchableOpacity style={s.removeLink} onPress={() => removerParticipante(participante.id)}>
                  <Text style={[s.removeLinkTxt, { color: C.muted }]}>Remover participante</Text>
                </TouchableOpacity>
              )}
            </View>
          )
        })}
      </View>

      <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}> 
        <View style={s.sectionHeader}>
          <View style={{ flex: 1 }}>
            <Text style={[s.title, { color: C.text }]}>Base cartográfica inicial</Text>
            <Text style={[s.subtitle, { color: C.muted }]}>Importe uma referência simples para o topografo revisar depois. Nada vira base oficial sem confirmação explícita.</Text>
          </View>
          <TouchableOpacity style={[s.smallButton, { borderColor: C.cardBorder, backgroundColor: C.background }]} onPress={adicionarArquivo}>
            <Text style={[s.smallButtonTxt, { color: C.text }]}>+ Adicionar arquivo</Text>
          </TouchableOpacity>
        </View>

        {arquivosBase.length === 0 ? (
          <View style={[s.emptyBox, { borderColor: C.cardBorder, backgroundColor: C.background }]}> 
            <Text style={[s.emptyTitle, { color: C.text }]}>Nenhum arquivo adicionado ainda</Text>
            <Text style={[s.emptySubtitle, { color: C.muted }]}>KML, KMZ, GeoJSON, Shapefile ZIP, CSV, TXT, DXF, imagem ou PDF podem entrar aqui como base inicial.</Text>
          </View>
        ) : (
          arquivosBase.map((arquivo) => (
            <View key={arquivo.id} style={[s.fileCard, { borderColor: C.cardBorder, backgroundColor: C.background }]}> 
              <View style={s.fileHeader}>
                <View style={{ flex: 1 }}>
                  <Text style={[s.fileTitle, { color: C.text }]} numberOfLines={1}>{arquivo.nome}</Text>
                  <Text style={[s.fileSubtitle, { color: C.muted }]}>{arquivo.classificacao === 'documento_croqui' ? 'Documento / croqui' : 'Base cartográfica'} · {arquivo.origem}</Text>
                </View>
                <TouchableOpacity onPress={() => removerArquivo(arquivo.id)}>
                  <Text style={[s.removeLinkTxt, { color: C.muted }]}>Remover</Text>
                </TouchableOpacity>
              </View>

              <View style={s.field}>
                <Text style={[s.label, { color: C.muted }]}>Origem</Text>
                <View style={s.chipsRow}>
                  {ORIGEM_OPTIONS.map((item) => {
                    const ativo = arquivo.origem === item.value
                    return (
                      <TouchableOpacity
                        key={item.value}
                        style={[s.chip, chipStyleAtivo(ativo, C)]}
                        onPress={() => atualizarArquivo(arquivo.id, 'origem', item.value)}
                      >
                        <Text style={{ color: ativo ? C.primaryText : C.text, fontWeight: '700', fontSize: 12 }}>{item.label}</Text>
                      </TouchableOpacity>
                    )
                  })}
                </View>
              </View>

              <View style={s.field}>
                <Text style={[s.label, { color: C.muted }]}>Classificação</Text>
                <View style={s.chipsRow}>
                  {CLASSIFICACAO_OPTIONS.map((item) => {
                    const ativo = arquivo.classificacao === item.value
                    return (
                      <TouchableOpacity
                        key={item.value}
                        style={[s.chip, chipStyleAtivo(ativo, C)]}
                        onPress={() => atualizarArquivo(arquivo.id, 'classificacao', item.value)}
                      >
                        <Text style={{ color: ativo ? C.primaryText : C.text, fontWeight: '700', fontSize: 12 }}>{item.label}</Text>
                      </TouchableOpacity>
                    )
                  })}
                </View>
              </View>
            </View>
          ))
        )}
      </View>

      <TouchableOpacity style={[s.submit, { backgroundColor: C.primary, opacity: salvando ? 0.7 : 1 }]} onPress={salvar} disabled={salvando}>
        <Text style={[s.submitTxt, { color: C.primaryText }]}>{salvando ? 'Criando...' : 'Criar projeto'}</Text>
      </TouchableOpacity>
    </ScrollView>
  )
}

const s = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 16, paddingTop: 26, gap: 14 },
  card: { borderWidth: 1, borderRadius: 18, padding: 16, gap: 14 },
  title: { fontSize: 20, fontWeight: '700' },
  subtitle: { fontSize: 13, lineHeight: 20 },
  section: { fontSize: 15, fontWeight: '700', marginTop: 4 },
  sectionHeader: { flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
  field: { gap: 6 },
  row: { flexDirection: 'row', gap: 10 },
  flex: { flex: 1 },
  ufField: { width: 78 },
  label: { fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.6, fontWeight: '700' },
  input: { borderWidth: 1, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 13, fontSize: 14 },
  chipsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 14, paddingVertical: 10 },
  smallButton: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 12, paddingVertical: 10 },
  smallButtonTxt: { fontSize: 12, fontWeight: '800' },
  participantCard: { borderWidth: 1, borderRadius: 16, padding: 14, gap: 12 },
  participantHeader: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10 },
  participantTitle: { fontSize: 16, fontWeight: '800' },
  participantSubtitle: { fontSize: 12, lineHeight: 18, marginTop: 2 },
  badge: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 6 },
  badgeTxt: { fontSize: 11, fontWeight: '800' },
  roleInline: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  roleLabel: { fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.6, fontWeight: '700' },
  roleValue: { fontSize: 13, fontWeight: '700' },
  toggleCard: { borderWidth: 1, borderRadius: 14, padding: 14, flexDirection: 'row', alignItems: 'center', gap: 12 },
  toggleBullet: { width: 14, height: 14, borderRadius: 999 },
  toggleTitle: { fontSize: 14, fontWeight: '700' },
  toggleSubtitle: { fontSize: 12, lineHeight: 18, marginTop: 2 },
  removeLink: { alignSelf: 'flex-start' },
  removeLinkTxt: { fontSize: 12, fontWeight: '700' },
  emptyBox: { borderWidth: 1, borderRadius: 14, padding: 14, gap: 6 },
  emptyTitle: { fontSize: 14, fontWeight: '700' },
  emptySubtitle: { fontSize: 12, lineHeight: 18 },
  fileCard: { borderWidth: 1, borderRadius: 16, padding: 14, gap: 12 },
  fileHeader: { flexDirection: 'row', alignItems: 'flex-start', gap: 10 },
  fileTitle: { fontSize: 14, fontWeight: '800' },
  fileSubtitle: { fontSize: 12, marginTop: 2 },
  submit: { borderRadius: 14, paddingVertical: 16, alignItems: 'center', marginBottom: 30 },
  submitTxt: { fontSize: 15, fontWeight: '800' },
})


