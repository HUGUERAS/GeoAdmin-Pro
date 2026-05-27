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
  rota?: string
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
    id: 'campo-simples',
    titulo: 'Campo simples',
    descricao: 'Linha, polilinha e nomes. Só o que precisa ficar pronto antes de abrir no FreeCAD.',
    ferramentas: [
      { id: 'linha', label: 'Linha', icone: 'slash', rota: '/calculos/linha' },
      { id: 'polilinha', label: 'Polilinha', icone: 'trending-up', rota: '/calculos/polilinha' },
      { id: 'nomenclatura', label: 'Nomes', icone: 'tag', rota: '/calculos/nomenclatura' },
    ],
  },
  {
    id: 'cad-freecad',
    titulo: 'No CAD do projeto',
    descricao: 'Com projeto ativo, trabalha no perímetro real e deixa mastigado para o FreeCAD.',
    ferramentas: [
      { id: 'cad-linha', label: 'Linha CAD', icone: 'slash', toolMapa: 'inverso' },
      { id: 'cad-polilinha', label: 'Polilinha CAD', icone: 'trending-up', toolMapa: 'area' },
      { id: 'cad-nomes', label: 'Nomear vértices', icone: 'tag', toolMapa: 'nomenclatura' },
      { id: 'cad-freecad', label: 'Pacote FreeCAD', icone: 'box', toolMapa: 'pacote' },
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
    if (!projetoAtivo) return 'Sem projeto ativo. Use as ferramentas livres ou abra um projeto para preparar o perímetro real.'
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
        titulo="Linha, polilinha e nomes"
        subtitulo="Ferramentas simples para organizar o perímetro antes do FreeCAD."
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
          for (let i = 0; i < secao.ferramentas.length; i += 2) rows.push(secao.ferramentas.slice(i, i + 2))
          return (
            <View key={secao.id} style={[s.secao, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
              <Text style={[s.secaoTitulo, { color: C.text }]}>{secao.titulo}</Text>
              <Text style={[s.secaoSub, { color: C.muted }]}>
                {projetoAtivo
                  ? `${secao.descricao} Toque para abrir no CAD deste projeto.`
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
        <Text style={[s.rodape, { color: C.muted }]}>FreeCAD entra depois: o app prepara linha, polilinha, nomes e pacote do projeto.</Text>
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
