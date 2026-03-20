import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, ScrollView, StyleSheet, Alert, ActivityIndicator, Platform } from 'react-native'
import { Colors } from '../../../constants/Colors'
import { API_URL } from '../../../constants/Api'

type Modo = 'utm-geo' | 'geo-utm'
type ResultadoUtmGeo = { lat: number; lon: number; fuso: number }
type ResultadoGeoUtm = { norte: number; este: number; fuso: number }

export default function ConversaoScreen() {
  const C = Colors.dark
  const [modo, setModo] = useState<Modo>('utm-geo')

  // UTM → Geo
  const [norte, setNorte] = useState('')
  const [este, setEste] = useState('')
  const [fuso, setFuso] = useState('23')
  const [hemisferio, setHemisferio] = useState<'N' | 'S'>('S')

  // Geo → UTM
  const [lat, setLat] = useState('')
  const [lon, setLon] = useState('')
  const [fusoOpcional, setFusoOpcional] = useState('')

  const [resultadoUtmGeo, setResultadoUtmGeo] = useState<ResultadoUtmGeo | null>(null)
  const [resultadoGeoUtm, setResultadoGeoUtm] = useState<ResultadoGeoUtm | null>(null)
  const [loading, setLoading] = useState(false)

  const trocarModo = (novoModo: Modo) => {
    setModo(novoModo)
    setResultadoUtmGeo(null)
    setResultadoGeoUtm(null)
  }

  const limpar = () => {
    setNorte(''); setEste(''); setFuso('23'); setHemisferio('S')
    setLat(''); setLon(''); setFusoOpcional('')
    setResultadoUtmGeo(null); setResultadoGeoUtm(null)
  }

  const calcular = async () => {
    setLoading(true)
    setResultadoUtmGeo(null)
    setResultadoGeoUtm(null)
    try {
      if (modo === 'utm-geo') {
        const n = parseFloat(norte), e = parseFloat(este), f = parseInt(fuso)
        if (isNaN(n) || isNaN(e) || isNaN(f)) {
          Alert.alert('Dados incompletos', 'Preencha Norte, Este e Fuso.')
          return
        }
        const res = await fetch(`${API_URL}/geo/converter/utm-geo`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ norte: n, este: e, fuso: f, hemisferio }),
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        setResultadoUtmGeo(await res.json())
      } else {
        const la = parseFloat(lat), lo = parseFloat(lon)
        if (isNaN(la) || isNaN(lo)) {
          Alert.alert('Dados incompletos', 'Preencha Latitude e Longitude.')
          return
        }
        const body: any = { lat: la, lon: lo }
        if (fusoOpcional) body.fuso = parseInt(fusoOpcional)
        const res = await fetch(`${API_URL}/geo/converter/geo-utm`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        setResultadoGeoUtm(await res.json())
      }
    } catch {
      Alert.alert('Erro', 'Não foi possível converter.\nVerifique a conexão com o backend.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <ScrollView style={[s.container, { backgroundColor: C.background }]} keyboardShouldPersistTaps="handled">
      <View style={[s.header, { backgroundColor: C.card, borderBottomColor: C.cardBorder }]}>
        <Text style={[s.titulo, { color: C.text }]}>Conversão</Text>
        <Text style={[s.sub, { color: C.muted }]}>UTM ↔ Geográfico (SIRGAS 2000)</Text>
      </View>

      <View style={s.body}>
        {/* Toggle de modo */}
        <View style={[s.toggle, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
          <TouchableOpacity
            style={[s.toggleBtn, modo === 'utm-geo' && { backgroundColor: C.primary }]}
            onPress={() => trocarModo('utm-geo')}
          >
            <Text style={[s.toggleTxt, { color: modo === 'utm-geo' ? C.primaryText : C.muted }]}>UTM → Geo</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[s.toggleBtn, modo === 'geo-utm' && { backgroundColor: C.primary }]}
            onPress={() => trocarModo('geo-utm')}
          >
            <Text style={[s.toggleTxt, { color: modo === 'geo-utm' ? C.primaryText : C.muted }]}>Geo → UTM</Text>
          </TouchableOpacity>
        </View>

        {modo === 'utm-geo' ? (
          <>
            <Text style={[s.secao, { color: C.primary }]}>Coordenadas UTM</Text>
            <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
              <View style={s.campo}>
                <Text style={[s.label, { color: C.muted }]}>NORTE (m)</Text>
                <TextInput
                  style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
                  value={norte} onChangeText={setNorte} placeholder="7395000.000"
                  placeholderTextColor={C.muted} keyboardType="numeric" returnKeyType="next"
                />
              </View>
              <View style={s.campo}>
                <Text style={[s.label, { color: C.muted }]}>ESTE (m)</Text>
                <TextInput
                  style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
                  value={este} onChangeText={setEste} placeholder="313500.000"
                  placeholderTextColor={C.muted} keyboardType="numeric" returnKeyType="next"
                />
              </View>
              <View style={s.campoRow}>
                <View style={s.campoHalf}>
                  <Text style={[s.label, { color: C.muted }]}>FUSO</Text>
                  <TextInput
                    style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
                    value={fuso} onChangeText={setFuso} placeholder="23"
                    placeholderTextColor={C.muted} keyboardType="numeric" returnKeyType="next"
                  />
                </View>
                <View style={s.campoHalf}>
                  <Text style={[s.label, { color: C.muted }]}>HEMISFÉRIO</Text>
                  <View style={[s.toggleSm, { borderColor: C.cardBorder }]}>
                    <TouchableOpacity
                      style={[s.toggleSmBtn, hemisferio === 'N' && { backgroundColor: C.primary }]}
                      onPress={() => setHemisferio('N')}
                    >
                      <Text style={[s.toggleSmTxt, { color: hemisferio === 'N' ? C.primaryText : C.muted }]}>N</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={[s.toggleSmBtn, hemisferio === 'S' && { backgroundColor: C.primary }]}
                      onPress={() => setHemisferio('S')}
                    >
                      <Text style={[s.toggleSmTxt, { color: hemisferio === 'S' ? C.primaryText : C.muted }]}>S</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              </View>
            </View>
          </>
        ) : (
          <>
            <Text style={[s.secao, { color: C.primary }]}>Coordenadas Geográficas</Text>
            <View style={[s.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
              <View style={s.campo}>
                <Text style={[s.label, { color: C.muted }]}>LATITUDE (decimal)</Text>
                <TextInput
                  style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
                  value={lat} onChangeText={setLat} placeholder="-23.55050000"
                  placeholderTextColor={C.muted} keyboardType="numeric" returnKeyType="next"
                />
              </View>
              <View style={s.campo}>
                <Text style={[s.label, { color: C.muted }]}>LONGITUDE (decimal)</Text>
                <TextInput
                  style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
                  value={lon} onChangeText={setLon} placeholder="-46.63330000"
                  placeholderTextColor={C.muted} keyboardType="numeric" returnKeyType="next"
                />
              </View>
              <View style={s.campo}>
                <Text style={[s.label, { color: C.muted }]}>FUSO (opcional)</Text>
                <TextInput
                  style={[s.input, { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background }]}
                  value={fusoOpcional} onChangeText={setFusoOpcional} placeholder="auto"
                  placeholderTextColor={C.muted} keyboardType="numeric" returnKeyType="next"
                />
              </View>
            </View>
          </>
        )}

        <View style={s.btns}>
          <TouchableOpacity style={[s.btnSec, { borderColor: C.cardBorder }]} onPress={limpar}>
            <Text style={[s.btnSecTxt, { color: C.muted }]}>Limpar</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[s.btnPri, { backgroundColor: C.primary }]} onPress={calcular} disabled={loading}>
            {loading ? <ActivityIndicator color={C.primaryText} /> : <Text style={[s.btnPriTxt, { color: C.primaryText }]}>Converter</Text>}
          </TouchableOpacity>
        </View>

        {resultadoUtmGeo && (
          <View style={[s.resultado, { backgroundColor: C.card, borderColor: C.primary }]}>
            <Text style={[s.resLabel, { color: C.muted }]}>Resultado — Geográfico (SIRGAS 2000)</Text>
            <View style={s.resRow}>
              <View style={s.resItem}>
                <Text style={[s.resValor, { color: C.primary }]}>{resultadoUtmGeo.lat.toFixed(8)}</Text>
                <Text style={[s.resSub, { color: C.muted }]}>Latitude</Text>
              </View>
              <View style={[s.resDividerV, { backgroundColor: C.cardBorder }]} />
              <View style={s.resItem}>
                <Text style={[s.resValor, { color: C.primary }]}>{resultadoUtmGeo.lon.toFixed(8)}</Text>
                <Text style={[s.resSub, { color: C.muted }]}>Longitude</Text>
              </View>
            </View>
            <Text style={[s.fusoInfo, { color: C.muted }]}>Fuso {resultadoUtmGeo.fuso}</Text>
          </View>
        )}

        {resultadoGeoUtm && (
          <View style={[s.resultado, { backgroundColor: C.card, borderColor: C.primary }]}>
            <Text style={[s.resLabel, { color: C.muted }]}>Resultado — UTM (SIRGAS 2000)</Text>
            <View style={s.resRow}>
              <View style={s.resItem}>
                <Text style={[s.resValor, { color: C.primary }]}>{resultadoGeoUtm.norte.toFixed(3)}</Text>
                <Text style={[s.resSub, { color: C.muted }]}>Norte (m)</Text>
              </View>
              <View style={[s.resDividerV, { backgroundColor: C.cardBorder }]} />
              <View style={s.resItem}>
                <Text style={[s.resValor, { color: C.primary }]}>{resultadoGeoUtm.este.toFixed(3)}</Text>
                <Text style={[s.resSub, { color: C.muted }]}>Este (m)</Text>
              </View>
            </View>
            <Text style={[s.fusoInfo, { color: C.muted }]}>Fuso {resultadoGeoUtm.fuso}</Text>
          </View>
        )}

        <TouchableOpacity
          style={[s.gabarito, { borderColor: C.cardBorder }]}
          onPress={() => {
            if (modo === 'utm-geo') {
              setNorte('7395000'); setEste('313500'); setFuso('23'); setHemisferio('S')
            } else {
              setLat('-23.55050000'); setLon('-46.63330000'); setFusoOpcional('')
            }
            setResultadoUtmGeo(null); setResultadoGeoUtm(null)
          }}
        >
          <Text style={[s.gabaritoTxt, { color: C.muted }]}>
            {modo === 'utm-geo'
              ? 'Gabarito: N=7395000, E=313500, Fuso=23, Hem=S'
              : 'Gabarito: Lat=-23.5505, Lon=-46.6333 (São Paulo)'}
          </Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  )
}

const s = StyleSheet.create({
  container:    { flex: 1 },
  header:       { padding: 20, paddingTop: 56, borderBottomWidth: 0.5 },
  titulo:       { fontSize: 24, fontWeight: '700' },
  sub:          { fontSize: 13, marginTop: 2 },
  body:         { padding: 16 },
  secao:        { fontSize: 12, fontWeight: '700', marginBottom: 8, marginTop: 16, textTransform: 'uppercase', letterSpacing: 0.5 },
  toggle:       { flexDirection: 'row', borderRadius: 10, borderWidth: 0.5, overflow: 'hidden', marginTop: 16 },
  toggleBtn:    { flex: 1, padding: 12, alignItems: 'center' },
  toggleTxt:    { fontSize: 14, fontWeight: '600' },
  toggleSm:     { flexDirection: 'row', borderRadius: 8, borderWidth: 0.5, overflow: 'hidden', height: 46 },
  toggleSmBtn:  { flex: 1, alignItems: 'center', justifyContent: 'center' },
  toggleSmTxt:  { fontSize: 14, fontWeight: '700' },
  card:         { borderRadius: 10, borderWidth: 0.5, padding: 14, marginBottom: 4 },
  campo:        { marginBottom: 12 },
  campoRow:     { flexDirection: 'row', gap: 10 },
  campoHalf:    { flex: 1, marginBottom: 12 },
  label:        { fontSize: 10, fontWeight: '600', marginBottom: 5, textTransform: 'uppercase', letterSpacing: 0.3 },
  input:        { borderWidth: 0.5, borderRadius: 8, padding: 12, fontSize: 15, fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  btns:         { flexDirection: 'row', gap: 10, marginTop: 20 },
  btnPri:       { flex: 2, padding: 16, borderRadius: 10, alignItems: 'center', justifyContent: 'center', minHeight: 52 },
  btnPriTxt:    { fontSize: 16, fontWeight: '700' },
  btnSec:       { flex: 1, padding: 16, borderRadius: 10, alignItems: 'center', borderWidth: 0.5, minHeight: 52 },
  btnSecTxt:    { fontSize: 16, fontWeight: '500' },
  resultado:    { marginTop: 20, borderRadius: 12, borderWidth: 1, padding: 20 },
  resLabel:     { fontSize: 10, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 14 },
  resRow:       { flexDirection: 'row', alignItems: 'center' },
  resItem:      { flex: 1, alignItems: 'center' },
  resValor:     { fontSize: 18, fontWeight: '700', fontFamily: Platform.OS === 'android' ? 'monospace' : 'Courier' },
  resSub:       { fontSize: 12, marginTop: 4 },
  resDividerV:  { width: 0.5, height: 40, marginHorizontal: 10 },
  fusoInfo:     { fontSize: 11, textAlign: 'center', marginTop: 12 },
  gabarito:     { marginTop: 16, borderWidth: 0.5, borderRadius: 8, padding: 12, borderStyle: 'dashed' },
  gabaritoTxt:  { fontSize: 12, textAlign: 'center' },
})
