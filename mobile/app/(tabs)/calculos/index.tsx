import { View, Text, ScrollView, StyleSheet } from 'react-native'
import { useRouter } from 'expo-router'
import { Feather } from '@expo/vector-icons'
import { Colors } from '../../../constants/Colors'
import { FerramentaBtn } from '../../../components/FerramentaBtn'

const SECOES = [
  {
    id: 'peca-tecnica',
    titulo: 'Peça técnica',
    descricao: 'Ferramentas para conferir área, gerar coordenadas auxiliares e fechar o raciocínio topográfico.',
    ferramentas: [
      { id: 'area',       label: 'Área',          icone: 'square',            rota: '/calculos/area' },
      { id: 'intersecao', label: 'Interseção',    icone: 'git-merge',         rota: '/calculos/intersecao' },
      { id: 'distancia',  label: 'Dist. P-L',     icone: 'move',              rota: '/calculos/distancia' },
      { id: 'subdivisao', label: 'Subdivisão',    icone: 'scissors',          rota: '/calculos/subdivisao' },
      { id: 'rotacao',    label: 'Rotação',       icone: 'rotate-cw',         rota: '/calculos/rotacao' },
    ],
  },
  {
    id: 'apoio-cad',
    titulo: 'Apoio ao CAD',
    descricao: 'Use para montar, conferir e ajustar vértices antes de voltar ao mapa/CAD do projeto.',
    ferramentas: [
      { id: 'conversao',  label: 'Conversão',     icone: 'refresh-cw',        rota: '/calculos/conversao' },
      { id: 'deflexao',   label: 'Deflexão',      icone: 'corner-down-right', rota: '/calculos/deflexao' },
      { id: 'media',      label: 'Média Pts',     icone: 'target',            rota: '/calculos/media' },
      { id: 'irradiacao', label: 'Irradiação',    icone: 'navigation',        rota: '/calculos/irradiacao' },
    ],
  },
  {
    id: 'pontos-linhas',
    titulo: 'Pontos e Linhas',
    descricao: 'Bloco de notas de campo, travessia de segmentos e nomenclatura de vértices.',
    ferramentas: [
      { id: 'pontos',       label: 'Pontos',       icone: 'grid',          rota: '/calculos/pontos' },
      { id: 'linha',        label: 'Linha',        icone: 'arrow-up-right',rota: '/calculos/linha' },
      { id: 'polilinha',    label: 'Polilinha',    icone: 'trending-up',   rota: '/calculos/polilinha' },
      { id: 'nomenclatura', label: 'Nomenclatura', icone: 'tag',           rota: '/calculos/nomenclatura' },
    ],
  },
]

export default function CalculosScreen() {
  const C = Colors.dark
  const router = useRouter()

  return (
    <View style={[s.container, { backgroundColor: C.background }]}>
      <View style={[s.header, { backgroundColor: C.card, borderBottomColor: C.cardBorder }]}>
        <Text style={[s.titulo, { color: C.text }]}>Cálculos técnicos</Text>
        <Text style={[s.sub, { color: C.muted }]}>Essas ferramentas existem para alimentar o CAD e a peça técnica, não para virar um fluxo paralelo.</Text>
      </View>
      <ScrollView contentContainerStyle={s.grid}>
        {SECOES.map((secao) => {
          const rows = []
          for (let i = 0; i < secao.ferramentas.length; i += 3) rows.push(secao.ferramentas.slice(i, i + 3))
          return (
            <View key={secao.id} style={[s.secao, { backgroundColor: C.card, borderColor: C.cardBorder }]}> 
              <Text style={[s.secaoTitulo, { color: C.text }]}>{secao.titulo}</Text>
              <Text style={[s.secaoSub, { color: C.muted }]}>{secao.descricao}</Text>
              {rows.map((row, ri) => (
                <View key={`${secao.id}-${ri}`} style={s.row}>
                  {row.map((f) => (
                    <FerramentaBtn
                      key={f.id}
                      label={f.label}
                      icone={<Feather name={f.icone as any} size={22} color={f.rota ? C.primary : C.muted} />}
                      ativo={!!f.rota}
                      onPress={() => { if (f.rota) router.push(f.rota as any) }}
                    />
                  ))}
                </View>
              ))}
            </View>
          )
        })}
        <Text style={[s.rodape, { color: C.muted }]}>Fluxo ideal: calcular, conferir e voltar para o mapa/CAD do projeto.</Text>
      </ScrollView>
    </View>
  )
}

const s = StyleSheet.create({
  container: { flex: 1 },
  header:    { padding: 20, paddingTop: 56, borderBottomWidth: 0.5 },
  titulo:    { fontSize: 24, fontWeight: '700' },
  sub:       { fontSize: 12, marginTop: 4, lineHeight: 18 },
  grid:      { padding: 10 },
  secao:     { borderWidth: 0.5, borderRadius: 14, padding: 12, marginBottom: 12, gap: 10 },
  secaoTitulo:{ fontSize: 16, fontWeight: '700' },
  secaoSub:  { fontSize: 12, lineHeight: 18 },
  row:       { flexDirection: 'row' },
  rodape:    { fontSize: 12, lineHeight: 18, textAlign: 'center', paddingHorizontal: 10, paddingBottom: 24 },
})
