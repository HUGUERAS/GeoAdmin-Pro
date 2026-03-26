import { useState, useEffect, useCallback } from 'react'
import { View, Text, ScrollView, StyleSheet, ActivityIndicator, TouchableOpacity, Alert, Clipboard } from 'react-native'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { Colors } from '../../../constants/Colors'
import { API_URL } from '../../../constants/Api'
import { StatusBadge } from '../../../components/StatusBadge'
import { SyncBadge } from '../../../components/SyncBadge'
import { contarPendentes, initDB, cacheProjetoDetalhe, getCachedProjetoDetalhe } from '../../../lib/db'
import { sincronizar } from '../../../lib/sync'

export default function DetalheProjetoScreen() {
  const C = Colors.dark
  const { id } = useLocalSearchParams<{ id: string }>()
  const router  = useRouter()
  const [projeto, setProjeto]       = useState<any>(null)
  const [loading, setLoading]       = useState(true)
  const [gerando, setGerando]       = useState(false)
  const [pendentes, setPendentes]   = useState(0)
  const [sincronizando, setSinc]    = useState(false)
  const [offline, setOffline]       = useState(false)
  const [semCache, setSemCache]     = useState(false)

  const atualizarPendentes = useCallback(async () => {
    const n = await contarPendentes(id)
    setPendentes(n)
  }, [id])

  const handleSync = async () => {
    setSinc(true)
    const r = await sincronizar(id)
    await atualizarPendentes()
    setSinc(false)
    if (r.sincronizados > 0)
      Alert.alert('Sincronizado', `${r.sincronizados} ponto(s) enviado(s).`)
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
  }, [id])

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
          <SyncBadge pendentes={pendentes} onPress={handleSync} sincronizando={sincronizando} />
        </View>
        <View style={{ marginTop: 8 }}><StatusBadge status={projeto.status} /></View>
      </View>

      <View style={s.body}>
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
            <Text style={[s.btnTxt, { color: C.success }]}>👤 Cliente & Documentacao</Text>
          </TouchableOpacity>
        ) : null}

        <TouchableOpacity
          style={[s.btn, { backgroundColor: C.card, borderColor: C.info }]}
          onPress={() => router.push(`/(tabs)/mapa/${id}` as any)}
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
  campo:         { paddingVertical: 12, borderBottomWidth: 0.5 },
  campoLabel:    { fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 2 },
  campoValor:    { fontSize: 15, fontWeight: '500' },
  btn:           { borderRadius: 10, padding: 16, alignItems: 'center', marginTop: 12, borderWidth: 1 },
  btnTxt:        { fontSize: 15, fontWeight: '700' },
  bannerOffline: { backgroundColor: '#B8860B', paddingVertical: 6, paddingHorizontal: 14 },
  bannerTxt:     { color: '#FFF8DC', fontSize: 12, fontWeight: '500', textAlign: 'center' },
  semCacheTxt:   { fontSize: 14, textAlign: 'center', paddingHorizontal: 24 },
})
