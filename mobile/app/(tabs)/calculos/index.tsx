import { useEffect, useMemo, useState } from 'react'
import { View, Text, ScrollView, StyleSheet, TouchableOpacity, ActivityIndicator } from 'react-native'
import { useRouter } from 'expo-router'
import { Feather } from '@expo/vector-icons'
import { Colors } from '../../../constants/Colors'
import { FerramentaBtn } from '../../../components/FerramentaBtn'
import { ScreenHeader } from '../../../components/ScreenHeader'
import { apiGet } from '../../../lib/api'
import { getCachedProjetoDetalhe, initDB, obterUltimoProjetoMapa } from '../../../lib/db'

type FerramentaDef = {
  id: string
  label: string
  icone: string
  rota: string
  toolMapa?: string
}

type SecaoDef = {
  id: string
  titulo: string
  descricao: string
  ferramentas: FerramentaDef[]
}

const SECOES: SecaoDef[] = [
  {
    id: 'peca-tecnica',
    titulo: 'Peça técnica',
    descricao: 'Ferramentas para conferir área, gerar coordenadas auxiliares e fechar o raciocínio topográfico.',
    ferramentas: [
      { id: 'inverso', label: 'Inverso', icone: 'arrow-up-right', rota: '/calculos/inverso', toolMapa: 'inverso' },
      { id: 'area', label: 'Área', icone: 'square', rota: '/calculos/area', toolMapa: 'area' },
      { id: 'intersecao', label: 'Interseção', icone: 'git-merge', rota: '/calculos/intersecao', toolMapa: 'intersecao' },
      { id: 'distancia', label: 'Dist. P-L', icone: 'move', rota: '/calculos/distancia', toolMapa: 'distpl' },
      { id: 'subdivisao', label: 'Subdivisão', icone: 'scissors', rota: '/calculos/subdivisao', toolMapa: 'subdivisao' },
      { id: 'rotacao', label: 'Rotação', icone: 'rotate-cw', rota: '/calculos/rotacao', toolMapa: 'rotacao' },
    ],
  },
  {
    id: 'apoio-cad',
    titulo: 'Apoio ao CAD',
    descricao: 'Use para montar, conferir e ajustar vértices antes de voltar ao mapa/CAD do projeto.',
    ferramentas: [
      { id: 'conversao', label: 'Conversão', icone: 'refresh-cw', rota: '/calculos/conversao', toolMapa: 'conversao' },
      { id: 'deflexao', label: 'Deflexão', icone: 'corner-down-right', rota: '/calculos/deflexao', toolMapa: 'deflexao' },
      { id: 'media', label: 'Média Pts', icone: 'target', rota: '/calculos/media', toolMapa: 'mediaPts' },
      { id: 'irradiacao', label: 'Irradiação', icone: 'navigation', rota: '/calculos/irradiacao', toolMapa: 'irradiacao' },
    ],
  },
  {
    id: 'pontos-linhas',
    titulo: 'Pontos e Linhas',
    descricao: 'Bloco de notas de campo, travessia de segmentos e nomenclatura de vértices.',
    ferramentas: [
      { id: 'pontos', label: 'Pontos', icone: 'grid', rota: '/calculos/pontos' },
      { id: 'linha', label: 'Linha', icone: 'arrow-up-right', rota: '/calculos/linha' },
      { id: 'polilinha', label: 'Polilinha', icone: 'trending-up', rota: '/calculos/polilinha' },
      { id: 'nomenclatura', label: 'Nomenclatura', icone: 'tag', rota: '/calculos/nomenclatura' },
    ],
  },
]

type ProjetoContexto = {
  id: string
  projeto_nome?: string | null
  cliente_nome?: string | null
  total_pontos?: number | null
}

export default function CalculosScreen() {
  const C = Colors.dark
  const router = useRouter()
  const [carregandoContexto, setCarregandoContexto] = useState(true)
  const [projetoAtivo, setProjetoAtivo] = useState<ProjetoContexto | null>(null)

  useEffect(() => {
    let ativo = true
      ; (async () => {
        try {
          await initDB()
          const projetoId = await obterUltimoProjetoMapa()
          if (!ativo || !projetoId) {
            setProjetoAtivo(null)
            return
          }

          const cached = await getCachedProjetoDetalhe(projetoId)
          if (cached && ativo) {
            setProjetoAtivo({
              id: projetoId,
              projeto_nome: cached.projeto_nome,
              cliente_nome: cached.cliente_nome,
              total_pontos: cached.total_pontos,
            })
          }

          try {
            const remoto = await apiGet<any>(`/projetos/${projetoId}`)
            if (!ativo) return
            setProjetoAtivo({
              id: projetoId,
              projeto_nome: remoto.projeto_nome,
              cliente_nome: remoto.cliente_nome,
              total_pontos: remoto.total_pontos,
            })
          } catch {
            // Mantém o cache se a API falhar.
          }
        } finally {
          if (ativo) setCarregandoContexto(false)
        }
      })()

    return () => { ativo = false }
  }, [])

  const mensagemContexto = useMemo(() => {
    if (carregandoContexto) return 'Recuperando o projeto ativo do mapa...'
    if (!projetoAtivo) return 'Sem projeto ativo no CAD. Abra um projeto e toque em "Ver no mapa" para transformar esta aba em apoio real ao trabalho.'
    return `Projeto ativo: ${projetoAtivo.projeto_nome || 'Projeto sem nome'}${projetoAtivo.cliente_nome ? ` · Cliente ${projetoAtivo.cliente_nome}` : ''}${projetoAtivo.total_pontos ? ` · ${projetoAtivo.total_pontos} ponto(s)` : ''}`
  }, [carregandoContexto, projetoAtivo])

  const abrirFerramenta = (ferramenta: { rota?: string; toolMapa?: string }) => {
    if (projetoAtivo?.id && ferramenta.toolMapa) {
      router.push(`/(tabs)/mapa/${projetoAtivo.id}?tool=${ferramenta.toolMapa}` as any)
      return
    }
    if (ferramenta.rota) {
      router.push(ferramenta.rota as any)
    }
  }

  return (
    <View style={[s.container, { backgroundColor: C.background }]}>
      <ScreenHeader
        titulo="Cálculos técnicos"
        subtitulo="Essas ferramentas existem para alimentar o CAD e a peça técnica, não para virar um fluxo paralelo."
      />
      <ScrollView contentContainerStyle={s.grid}>
        <View style={[s.contextoCard, { backgroundColor: C.card, borderColor: projetoAtivo ? C.primary : C.cardBorder }]}>
          <Text style={[s.contextoLabel, { color: projetoAtivo ? C.primary : C.muted }]}>Contexto do cálculo</Text>
          <Text style={[s.contextoTexto, { color: C.text }]}>{mensagemContexto}</Text>
          {carregandoContexto ? (
            <ActivityIndicator color={C.primary} style={{ marginTop: 8 }} />
          ) : (
            <View style={s.contextoAcoes}>
              {projetoAtivo ? (
                <>
                  <TouchableOpacity style={[s.contextoBtn, { borderColor: C.primary }]} onPress={() => router.push(`/(tabs)/mapa/${projetoAtivo.id}` as any)}>
                    <Text style={[s.contextoBtnTxt, { color: C.primary }]}>Abrir CAD</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={[s.contextoBtn, { borderColor: C.info }]} onPress={() => router.push(`/(tabs)/projeto/${projetoAtivo.id}` as any)}>
                    <Text style={[s.contextoBtnTxt, { color: C.info }]}>Abrir projeto</Text>
                  </TouchableOpacity>
                </>
              ) : (
                <TouchableOpacity style={[s.contextoBtn, { borderColor: C.primary }]} onPress={() => router.push('/(tabs)/projeto' as any)}>
                  <Text style={[s.contextoBtnTxt, { color: C.primary }]}>Escolher projeto</Text>
                </TouchableOpacity>
              )}
            </View>
          )}
        </View>

        {SECOES.map((secao) => {
          const rows = []
          for (let i = 0; i < secao.ferramentas.length; i += 3) rows.push(secao.ferramentas.slice(i, i + 3))
          return (
            <View key={secao.id} style={[s.secao, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
              <Text style={[s.secaoTitulo, { color: C.text }]}>{secao.titulo}</Text>
              <Text style={[s.secaoSub, { color: C.muted }]}>
                {projetoAtivo
                  ? `${secao.descricao} Com projeto ativo, o toque abre direto no CAD deste projeto.`
                  : secao.descricao}
              </Text>
              {rows.map((row, ri) => (
                <View key={`${secao.id}-${ri}`} style={s.row}>
                  {row.map((f) => (
                    <FerramentaBtn
                      key={f.id}
                      label={f.label}
                      icone={<Feather name={f.icone as any} size={22} color={(f.rota || (projetoAtivo && f.toolMapa)) ? C.primary : C.muted} />}
                      ativo={!!f.rota || !!(projetoAtivo && f.toolMapa)}
                      onPress={() => abrirFerramenta(f)}
                    />
                  ))}
                </View>
              ))}
            </View>
          )
        })}
        <Text style={[s.rodape, { color: C.muted }]}>Fluxo ideal: abrir o projeto, entrar no CAD, calcular em contexto e só usar o modo livre quando estiver fazendo rascunho ou conferência isolada.</Text>
      </ScrollView>
    </View>
  )
}

const s = StyleSheet.create({
  container: { flex: 1 },
  header: { padding: 20, borderBottomWidth: 0.5 },
  titulo: { fontSize: 24, fontWeight: '700' },
  sub: { fontSize: 12, marginTop: 4, lineHeight: 18 },
  grid: { padding: 10 },
  contextoCard: { borderWidth: 1, borderRadius: 14, padding: 14, marginBottom: 12, gap: 10 },
  contextoLabel: { fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.7, fontWeight: '700' },
  contextoTexto: { fontSize: 14, lineHeight: 20, fontWeight: '600' },
  contextoAcoes: { flexDirection: 'row', gap: 10, flexWrap: 'wrap' },
  contextoBtn: { minHeight: 42, borderRadius: 10, borderWidth: 1, paddingHorizontal: 14, alignItems: 'center', justifyContent: 'center' },
  contextoBtnTxt: { fontSize: 13, fontWeight: '700' },
  secao: { borderWidth: 0.5, borderRadius: 14, padding: 12, marginBottom: 12, gap: 10 },
  secaoTitulo: { fontSize: 16, fontWeight: '700' },
  secaoSub: { fontSize: 12, lineHeight: 18 },
  row: { flexDirection: 'row' },
  rodape: { fontSize: 12, lineHeight: 18, textAlign: 'center', paddingHorizontal: 10, paddingBottom: 24 },
})
