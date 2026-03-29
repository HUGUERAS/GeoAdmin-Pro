import { useState } from 'react'
import {
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native'
import { useRouter } from 'expo-router'
import { Colors } from '../../../constants/Colors'
import { apiPost } from '../../../lib/api'

type FormProjeto = {
  nome: string
  municipio: string
  estado: string
  status: string
  zona_utm: string
  cliente_nome: string
  cliente_cpf: string
  cliente_telefone: string
  gerar_magic_link: boolean
}

const STATUS = [
  { label: 'Medição', value: 'medicao' },
  { label: 'Montagem', value: 'montagem' },
  { label: 'Protocolado', value: 'protocolado' },
]

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
    cliente_nome: '',
    cliente_cpf: '',
    cliente_telefone: '',
    gerar_magic_link: true,
  })

  const atualizar = (campo: keyof FormProjeto, valor: string | boolean) => {
    setForm((atual) => ({ ...atual, [campo]: valor }))
  }

  const salvar = async () => {
    if (!form.nome.trim()) {
      Alert.alert('Projeto sem nome', 'Informe o nome do projeto antes de continuar.')
      return
    }
    setSalvando(true)
    try {
      const projeto = await apiPost<any>('/projetos', {
        nome: form.nome,
        municipio: form.municipio || null,
        estado: form.estado || null,
        status: form.status,
        zona_utm: form.zona_utm,
        cliente_nome: form.cliente_nome || null,
        cliente_cpf: form.cliente_cpf || null,
        cliente_telefone: form.cliente_telefone || null,
        gerar_magic_link: form.gerar_magic_link,
      })
      Alert.alert(
        'Projeto criado',
        projeto.magic_link?.link
          ? 'Projeto criado e magic link preparado para o cliente principal.'
          : 'Projeto criado com sucesso.',
      )
      router.replace(`/(tabs)/projeto/${projeto.id}` as any)
    } catch (error: any) {
      Alert.alert('Erro', error?.message || 'Não foi possível criar o projeto agora.')
    } finally {
      setSalvando(false)
    }
  }

  return (
    <ScrollView style={[s.container, { backgroundColor: C.background }]} contentContainerStyle={s.content}>
      <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}> 
        <Text style={[s.title, { color: C.text }]}>Novo projeto</Text>
        <Text style={[s.subtitle, { color: C.muted }]}>Abra o processo já com o cliente principal e deixe o magic link pronto para destravar o formulário.</Text>

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
              <TouchableOpacity key={item.value} style={[s.chip, ativo ? { backgroundColor: C.primary, borderColor: C.primary } : { backgroundColor: C.background, borderColor: C.cardBorder }]} onPress={() => atualizar('status', item.value)}>
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
        <Text style={[s.title, { color: C.text }]}>Cliente principal</Text>
        <Text style={[s.subtitle, { color: C.muted }]}>Se você informar o cliente agora, o app já pode criar o projeto e deixar o magic link pronto.</Text>

        <View style={s.field}>
          <Text style={[s.label, { color: C.muted }]}>Nome do cliente</Text>
          <TextInput style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]} value={form.cliente_nome} onChangeText={(v) => atualizar('cliente_nome', v)} placeholder="Nome completo" placeholderTextColor={C.muted} />
        </View>
        <View style={s.row}>
          <View style={[s.field, s.flex]}>
            <Text style={[s.label, { color: C.muted }]}>CPF</Text>
            <TextInput style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]} value={form.cliente_cpf} onChangeText={(v) => atualizar('cliente_cpf', v)} placeholder="000.000.000-00" placeholderTextColor={C.muted} />
          </View>
          <View style={[s.field, s.flex]}>
            <Text style={[s.label, { color: C.muted }]}>Telefone</Text>
            <TextInput style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]} value={form.cliente_telefone} onChangeText={(v) => atualizar('cliente_telefone', v)} placeholder="(00) 00000-0000" placeholderTextColor={C.muted} />
          </View>
        </View>

        <TouchableOpacity style={[s.toggleCard, { borderColor: C.cardBorder, backgroundColor: form.gerar_magic_link ? `${C.primary}22` : C.background }]} onPress={() => atualizar('gerar_magic_link', !form.gerar_magic_link)}>
          <View style={[s.toggleBullet, { backgroundColor: form.gerar_magic_link ? C.primary : C.cardBorder }]} />
          <View style={{ flex: 1 }}>
            <Text style={[s.toggleTitle, { color: C.text }]}>Gerar magic link automaticamente</Text>
            <Text style={[s.toggleSubtitle, { color: C.muted }]}>Se existir cliente principal, o link já sai pronto para WhatsApp.</Text>
          </View>
        </TouchableOpacity>
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
  field: { gap: 6 },
  row: { flexDirection: 'row', gap: 10 },
  flex: { flex: 1 },
  ufField: { width: 78 },
  label: { fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.6, fontWeight: '700' },
  input: { borderWidth: 1, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 13, fontSize: 14 },
  chipsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 14, paddingVertical: 10 },
  toggleCard: { borderWidth: 1, borderRadius: 14, padding: 14, flexDirection: 'row', alignItems: 'center', gap: 12 },
  toggleBullet: { width: 14, height: 14, borderRadius: 999 },
  toggleTitle: { fontSize: 14, fontWeight: '700' },
  toggleSubtitle: { fontSize: 12, lineHeight: 18, marginTop: 2 },
  submit: { borderRadius: 14, paddingVertical: 16, alignItems: 'center', marginBottom: 30 },
  submitTxt: { fontSize: 15, fontWeight: '800' },
})
