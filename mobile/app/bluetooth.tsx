/**
 * mobile/app/bluetooth.tsx
 * Tela de coleta GNSS via Bluetooth SPP (CHC i73+).
 * Stack screen — sem tab bar, tela cheia para uso em campo com luvas.
 *
 * ATENÇÃO: Requer EAS build (react-native-bluetooth-classic é módulo nativo).
 * Não funciona no Expo Go.
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import {
  View, Text, FlatList, TouchableOpacity, TextInput,
  StyleSheet, ActivityIndicator, Modal, ScrollView, Alert,
} from 'react-native'
import { Feather } from '@expo/vector-icons'
import { BluetoothDevice } from 'react-native-bluetooth-classic'
import { Colors } from '../constants/Colors'
import {
  listarDispositivosPareados, conectar, desconectar,
  isConectado, iniciarLeitura, pararLeitura,
} from '../lib/bluetooth'
import { NmeaFix, labelQualidade, corQualidade } from '../lib/nmea'
import { GpsIndicador } from '../components/GpsIndicador'
import { salvarPonto, ultimoNomePonto } from '../lib/db'
import { sincronizar } from '../lib/sync'
import {
  somConectado, somDesconectado, somPontoSalvo,
  somRtkFixo, somRtkFloat, somPdopAlto, somPrecisaoBaixa,
  somSatelitesInsuf, descarregarSons,
} from '../lib/audio'

// ID do projeto atual — em produção viria via params ou contexto
// Por ora exibe lista de dispositivos sem vínculo fixo de projeto
const PROJETO_PLACEHOLDER = ''

export default function BluetoothScreen() {
  const C = Colors.dark
  const insets = useSafeAreaInsets()
  const [dispositivos, setDispositivos]   = useState<BluetoothDevice[]>([])
  const [conectando, setConectando]       = useState(false)
  const [conectado, setConectado]         = useState(false)
  const [enderecoAtivo, setEnderecoAtivo] = useState<string | null>(null)
  const [fix, setFix]                     = useState<NmeaFix | null>(null)
  const [historico, setHistorico]         = useState<{ nome: string; q: number }[]>([])
  const [modalVisivel, setModalVisivel]   = useState(false)
  const [nomePonto, setNomePonto]         = useState('PT0001')
  const [salvando, setSalvando]           = useState(false)

  const fixRef        = useRef<NmeaFix | null>(null)
  const qualidadeRef  = useRef<number>(0)   // rastreia mudanças de qualidade para alertas sonoros
  fixRef.current = fix

  // ── Alertas sonoros quando a qualidade do fix muda ─────────────────────────
  useEffect(() => {
    if (!fix) return
    const qAnterior = qualidadeRef.current
    const qAtual    = fix.qualidade
    if (qAtual === qAnterior) return
    qualidadeRef.current = qAtual

    if (qAtual === 4)                        somRtkFixo()
    else if (qAtual === 5)                   somRtkFloat()
    else if (qAtual > 0 && fix.hdop > 4)     somPdopAlto()
    else if (qAtual > 0 && fix.satelites < 4) somSatelitesInsuf()
    else if (qAtual === 0 && qAnterior > 0)  somDesconectado()
  }, [fix?.qualidade])

  const carregarDispositivos = useCallback(async () => {
    const lista = await listarDispositivosPareados()
    setDispositivos(lista)
  }, [])

  useEffect(() => {
    carregarDispositivos()
    return () => { pararLeitura(); desconectar(); descarregarSons() }
  }, [])

  const handleConectar = async (address: string) => {
    setConectando(true)
    const ok = await conectar(address)
    setConectando(false)
    if (ok) {
      setConectado(true)
      setEnderecoAtivo(address)
      iniciarLeitura((novoFix) => setFix(novoFix))
      somConectado()
    } else {
      Alert.alert('Falha', 'Não foi possível conectar. Verifique se o CHC i73+ está ligado e pareado.')
    }
  }

  const handleDesconectar = async () => {
    await desconectar()
    setConectado(false)
    setEnderecoAtivo(null)
    setFix(null)
    somDesconectado()
  }

  const abrirModalColetar = async () => {
    const nome = await ultimoNomePonto(PROJETO_PLACEHOLDER || 'sem_projeto')
    setNomePonto(nome)
    setModalVisivel(true)
  }

  const salvarLocal = async (sincronizarDepois = false) => {
    const f = fixRef.current
    if (!f || f.qualidade === 0) return

    const doSave = async () => {
      setSalvando(true)
      try {
        const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`
        await salvarPonto({
          id,
          projeto_id:  PROJETO_PLACEHOLDER || 'sem_projeto',
          nome:        nomePonto,
          lat:         f.lat,
          lon:         f.lon,
          norte:       0,            // conversão UTM feita no backend
          este:        0,
          cota:        f.altElipsoidal, // altitude elipsoidal → backend aplica IBGE HNOR 2020
          codigo:      'TP',
          status_gnss: labelQualidade(f.qualidade),
          satelites:   f.satelites,
          pdop:        f.hdop,
          sigma_e:     0,
          sigma_n:     0,
          sigma_u:     0,
          origem:      'bluetooth',
          coletado_em: new Date().toISOString(),
          sync_em:     undefined,
        })
        somPontoSalvo()
        setHistorico(h => [{ nome: nomePonto, q: f.qualidade }, ...h].slice(0, 5))
        setModalVisivel(false)
        if (sincronizarDepois) {
          await sincronizar(PROJETO_PLACEHOLDER || undefined)
        }
      } finally {
        setSalvando(false)
      }
    }

    if (f.qualidade < 4 || f.hdop > 2) {
      somPrecisaoBaixa()
      Alert.alert(
        'Qualidade insuficiente',
        `Fix: ${labelQualidade(f.qualidade)}  HDOP: ${f.hdop.toFixed(1)}\n\nPara georreferenciamento INCRA é exigido RTK Fixo com HDOP ≤ 2. Salvar assim mesmo?`,
        [
          { text: 'Cancelar', style: 'cancel' },
          { text: 'Salvar mesmo assim', style: 'destructive', onPress: doSave },
        ]
      )
      return
    }

    await doSave()
  }

  const podeColetarFix = fix && fix.qualidade > 0 && fix.valida

  return (
    <View style={[s.container, { backgroundColor: C.background }]}>
      {/* Header */}
      <View style={[s.header, { backgroundColor: C.card, borderBottomColor: C.cardBorder, paddingTop: Math.max(insets.top + 12, 20) }]}>
        <Text style={[s.titulo, { color: C.text }]}>GNSS Bluetooth</Text>
        <Text style={[s.sub, { color: C.muted }]}>CHC i73+  •  SPP Clássico</Text>
      </View>

      <ScrollView contentContainerStyle={{ paddingBottom: 32 }}>
        {/* Lista de dispositivos pareados */}
        <View style={s.secao}>
          <View style={s.secaoHeader}>
            <Text style={[s.secaoTitulo, { color: C.muted }]}>DISPOSITIVOS PAREADOS</Text>
            <TouchableOpacity onPress={carregarDispositivos}>
              <Feather name="refresh-cw" size={16} color={C.muted} />
            </TouchableOpacity>
          </View>

          {dispositivos.length === 0 ? (
            <View style={[s.emptyBox, { backgroundColor: C.card }]}>
              <Feather name="bluetooth" size={28} color={C.muted} />
              <Text style={[s.emptyTxt, { color: C.muted }]}>
                Nenhum dispositivo pareado.{'\n'}Pareie o CHC i73+ nas configurações de Bluetooth do Android.
              </Text>
            </View>
          ) : (
            dispositivos.map(dev => (
              <View key={dev.address} style={[s.devRow, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
                <View style={s.devInfo}>
                  <Text style={[s.devNome, { color: C.text }]}>{dev.name ?? 'Dispositivo'}</Text>
                  <Text style={[s.devAddr, { color: C.muted }]}>{dev.address}</Text>
                </View>
                {enderecoAtivo === dev.address ? (
                  <TouchableOpacity
                    style={[s.devBtn, { backgroundColor: '#c0392b' }]}
                    onPress={handleDesconectar}
                    accessibilityRole="button"
                    accessibilityLabel={`Desconectar ${dev.name ?? 'dispositivo'}`}
                  >
                    <Text style={s.devBtnTxt}>Desconectar</Text>
                  </TouchableOpacity>
                ) : (
                  <TouchableOpacity
                    style={[s.devBtn, { backgroundColor: C.primary }]}
                    onPress={() => handleConectar(dev.address)}
                    disabled={conectando}
                    accessibilityRole="button"
                    accessibilityLabel={`Conectar ${dev.name ?? 'dispositivo'}`}
                    accessibilityState={{ disabled: conectando }}
                  >
                    {conectando ? <ActivityIndicator color="#fff" size="small" /> : <Text style={s.devBtnTxt}>Conectar</Text>}
                  </TouchableOpacity>
                )}
              </View>
            ))
          )}
        </View>

        {/* Status do fix — visível apenas quando conectado */}
        {conectado && (
          <View style={s.fixIndicadorWrapper}>
            <GpsIndicador fix={fix} />
          </View>
        )}

        {/* Coordenadas ao vivo */}
        {conectado && fix && fix.qualidade > 0 && (
          <View style={[s.coordBox, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
            <Text style={[s.coordLabel, { color: C.muted }]}>LAT</Text>
            <Text style={[s.coord, { color: C.primary }]}>{fix.lat.toFixed(8)}°</Text>
            <Text style={[s.coordLabel, { color: C.muted }]}>LON</Text>
            <Text style={[s.coord, { color: C.primary }]}>{fix.lon.toFixed(8)}°</Text>
            <Text style={[s.coordLabel, { color: C.muted }]}>ALT MSL (aprox. ortométrica)</Text>
            <Text style={[s.coord, { color: C.primary }]}>{fix.alt.toFixed(3)} m</Text>
            <Text style={[s.coordLabel, { color: C.muted }]}>ALT ELIPSOIDAL (WGS84)</Text>
            <Text style={[s.coord, { color: C.text }]}>{fix.altElipsoidal.toFixed(3)} m</Text>
          </View>
        )}

        {/* Botão COLETAR PONTO */}
        {conectado && (
          <TouchableOpacity
            style={[s.btnColetar, { backgroundColor: podeColetarFix ? C.primary : C.card }]}
            onPress={abrirModalColetar}
            disabled={!podeColetarFix}
            activeOpacity={0.8}
            accessibilityRole="button"
            accessibilityLabel="Coletar ponto"
            accessibilityState={{ disabled: !podeColetarFix }}
          >
            <Feather name="map-pin" size={22} color={podeColetarFix ? C.primaryText : C.muted} />
            <Text style={[s.btnColetarTxt, { color: podeColetarFix ? C.primaryText : C.muted }]}>
              COLETAR PONTO
            </Text>
          </TouchableOpacity>
        )}

        {/* Histórico dos últimos 5 pontos */}
        {historico.length > 0 && (
          <View style={s.secao}>
            <Text style={[s.secaoTitulo, { color: C.muted }]}>ÚLTIMOS COLETADOS</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
              {historico.map((h, i) => (
                <View key={i} style={[s.chip, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
                  <View style={[s.chipDot, { backgroundColor: corQualidade(h.q) }]} />
                  <Text style={[s.chipTxt, { color: C.text }]}>{h.nome}</Text>
                </View>
              ))}
            </ScrollView>
          </View>
        )}
      </ScrollView>

      {/* Modal de coleta */}
      <Modal visible={modalVisivel} transparent animationType="slide">
        <View style={s.modalOverlay}>
          <View style={[s.modalBox, { backgroundColor: C.card }]}>
            <Text style={[s.modalTitulo, { color: C.text }]}>Nome do Ponto</Text>
            <TextInput
              style={[s.modalInput, { backgroundColor: C.background, color: C.text, borderColor: C.cardBorder }]}
              value={nomePonto}
              onChangeText={setNomePonto}
              autoFocus
              selectTextOnFocus
              autoCapitalize="characters"
            />
            <TouchableOpacity
              style={[s.modalBtn, { backgroundColor: '#27ae60' }]}
              onPress={() => salvarLocal(false)}
              disabled={salvando}
              accessibilityRole="button"
              accessibilityLabel="Salvar ponto local"
              accessibilityState={{ disabled: salvando }}
            >
              {salvando ? <ActivityIndicator color="#fff" /> : <Text style={s.modalBtnTxt}>Salvar Local</Text>}
            </TouchableOpacity>
            <TouchableOpacity
              style={[s.modalBtn, { backgroundColor: C.primary }]}
              onPress={() => salvarLocal(true)}
              disabled={salvando}
              accessibilityRole="button"
              accessibilityLabel="Salvar ponto e sincronizar"
              accessibilityState={{ disabled: salvando }}
            >
              {salvando ? <ActivityIndicator color="#fff" /> : <Text style={s.modalBtnTxt}>Salvar + Sincronizar</Text>}
            </TouchableOpacity>
            <TouchableOpacity
              onPress={() => setModalVisivel(false)}
              style={s.modalCancelar}
              accessibilityRole="button"
              accessibilityLabel="Cancelar coleta"
            >
              <Text style={[s.modalCancelarTxt, { color: C.muted }]}>Cancelar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  )
}

const s = StyleSheet.create({
  container:      { flex: 1 },
  header:         { padding: 20, borderBottomWidth: 0.5 },
  titulo:         { fontSize: 24, fontWeight: '700' },
  sub:            { fontSize: 12, marginTop: 4 },
  secao:          { padding: 16 },
  secaoHeader:    { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 10 },
  secaoTitulo:    { fontSize: 11, textTransform: 'uppercase', letterSpacing: 1 },
  emptyBox:       { borderRadius: 12, padding: 24, alignItems: 'center', gap: 12 },
  emptyTxt:       { fontSize: 13, textAlign: 'center', lineHeight: 20 },
  devRow:         { flexDirection: 'row', alignItems: 'center', borderRadius: 10, borderWidth: 0.5, padding: 14, marginBottom: 8 },
  devInfo:        { flex: 1 },
  devNome:        { fontSize: 15, fontWeight: '600' },
  devAddr:        { fontSize: 11, fontFamily: 'monospace', marginTop: 2 },
  devBtn:         { borderRadius: 8, paddingHorizontal: 16, paddingVertical: 13, minWidth: 110, alignItems: 'center' },
  devBtnTxt:      { color: '#fff', fontWeight: '700', fontSize: 13 },
  fixIndicadorWrapper: { marginHorizontal: 16, marginBottom: 4 },
  coordBox:       { margin: 16, borderRadius: 12, borderWidth: 1, padding: 16 },
  coordLabel:     { fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, marginTop: 8 },
  coord:          { fontSize: 28, fontFamily: 'monospace', fontWeight: '700' },

  btnColetar:     { marginHorizontal: 16, marginTop: 8, borderRadius: 12, height: 72, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10 },
  btnColetarTxt:  { fontSize: 20, fontWeight: '800', letterSpacing: 1 },
  chip:           { flexDirection: 'row', alignItems: 'center', borderRadius: 20, borderWidth: 0.5, paddingHorizontal: 12, paddingVertical: 6, marginRight: 8, gap: 6 },
  chipDot:        { width: 8, height: 8, borderRadius: 4 },
  chipTxt:        { fontSize: 13, fontWeight: '500' },
  modalOverlay:   { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  modalBox:       { borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 24, gap: 12 },
  modalTitulo:    { fontSize: 18, fontWeight: '700', marginBottom: 4 },
  modalInput:     { borderRadius: 10, borderWidth: 1, padding: 16, fontSize: 20, fontFamily: 'monospace', fontWeight: '700', height: 60 },
  modalBtn:       { borderRadius: 10, padding: 16, alignItems: 'center' },
  modalBtnTxt:    { color: '#fff', fontSize: 16, fontWeight: '700' },
  modalCancelar:  { alignItems: 'center', padding: 14 },
  modalCancelarTxt: { fontSize: 14 },
})
