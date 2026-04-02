import { useState } from 'react'
import { View, Text, TouchableOpacity, ScrollView, StyleSheet, Alert, ActivityIndicator } from 'react-native'
import { Colors } from '../../../constants/Colors'
import { apiPost } from '../../../lib/api'
import { ScreenHeader } from '../../../components/ScreenHeader'
import { ss } from '@/styles/ss'
import { CampoInput } from '../../../components/CampoInput'

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
        setResultadoUtmGeo(await apiPost<ResultadoUtmGeo>('/geo/converter/utm-geo', { norte: n, este: e, fuso: f, hemisferio }))
      } else {
        const la = parseFloat(lat), lo = parseFloat(lon)
        if (isNaN(la) || isNaN(lo)) {
          Alert.alert('Dados incompletos', 'Preencha Latitude e Longitude.')
          return
        }
        const body: Record<string, unknown> = { lat: la, lon: lo }
        if (fusoOpcional) body.fuso = parseInt(fusoOpcional)
        setResultadoGeoUtm(await apiPost<ResultadoGeoUtm>('/geo/converter/geo-utm', body))
      }
    } catch (e: any) {
      Alert.alert('Erro', e.message || 'Não foi possível converter.\nVerifique a conexão com o backend.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <ScrollView style={[ss.container, { backgroundColor: C.background }]} keyboardShouldPersistTaps="handled">
      <ScreenHeader titulo="Conversão" subtitulo="UTM ↔ Geográfico (SIRGAS 2000)" />

      <View style={ss.body}>
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
            <View style={[ss.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
              <CampoInput label="NORTE (m)" value={norte} onChangeText={setNorte} placeholder="7395000.000" />
              <CampoInput label="ESTE (m)" value={este} onChangeText={setEste} placeholder="313500.000" />
              <View style={ss.campoRow}>
                <View style={ss.campoHalf}>
                  <CampoInput label="FUSO" value={fuso} onChangeText={setFuso} placeholder="23" />
                </View>
                <View style={ss.campoHalf}>
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
            <View style={[ss.card, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
              <CampoInput label="LATITUDE (decimal)" value={lat} onChangeText={setLat} placeholder="-23.55050000" />
              <CampoInput label="LONGITUDE (decimal)" value={lon} onChangeText={setLon} placeholder="-46.63330000" />
              <CampoInput label="FUSO (opcional)" value={fusoOpcional} onChangeText={setFusoOpcional} placeholder="auto" />
            </View>
          </>
        )}

        <View style={ss.btns}>
          <TouchableOpacity style={[ss.btnSec, { borderColor: C.cardBorder }]} onPress={limpar}>
            <Text style={[ss.btnSecTxt, { color: C.muted }]}>Limpar</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[ss.btnPri, { backgroundColor: C.primary }]} onPress={calcular} disabled={loading}>
            {loading ? <ActivityIndicator color={C.primaryText} /> : <Text style={[ss.btnPriTxt, { color: C.primaryText }]}>Converter</Text>}
          </TouchableOpacity>
        </View>

        {resultadoUtmGeo && (
          <View style={[ss.resultado, { backgroundColor: C.card, borderColor: C.primary }]}>
            <Text style={[ss.resLabel, { color: C.muted }]}>Resultado — Geográfico (SIRGAS 2000)</Text>
            <View style={s.resRow}>
              <View style={s.resItem}>
                <Text style={[ss.resValor, { color: C.primary }]}>{resultadoUtmGeo.lat.toFixed(8)}</Text>
                <Text style={[s.resSub, { color: C.muted }]}>Latitude</Text>
              </View>
              <View style={[s.resDividerV, { backgroundColor: C.cardBorder }]} />
              <View style={s.resItem}>
                <Text style={[ss.resValor, { color: C.primary }]}>{resultadoUtmGeo.lon.toFixed(8)}</Text>
                <Text style={[s.resSub, { color: C.muted }]}>Longitude</Text>
              </View>
            </View>
            <Text style={[s.fusoInfo, { color: C.muted }]}>Fuso {resultadoUtmGeo.fuso}</Text>
          </View>
        )}

        {resultadoGeoUtm && (
          <View style={[ss.resultado, { backgroundColor: C.card, borderColor: C.primary }]}>
            <Text style={[ss.resLabel, { color: C.muted }]}>Resultado — UTM (SIRGAS 2000)</Text>
            <View style={s.resRow}>
              <View style={s.resItem}>
                <Text style={[ss.resValor, { color: C.primary }]}>{resultadoGeoUtm.norte.toFixed(3)}</Text>
                <Text style={[s.resSub, { color: C.muted }]}>Norte (m)</Text>
              </View>
              <View style={[s.resDividerV, { backgroundColor: C.cardBorder }]} />
              <View style={s.resItem}>
                <Text style={[ss.resValor, { color: C.primary }]}>{resultadoGeoUtm.este.toFixed(3)}</Text>
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
  secao: { fontSize: 12, fontWeight: '700', marginBottom: 8, marginTop: 16, textTransform: 'uppercase', letterSpacing: 0.5 },
  toggle: { flexDirection: 'row', borderRadius: 10, borderWidth: 0.5, overflow: 'hidden', marginTop: 16 },
  toggleBtn: { flex: 1, padding: 12, alignItems: 'center' },
  toggleTxt: { fontSize: 14, fontWeight: '600' },
  toggleSm: { flexDirection: 'row', borderRadius: 8, borderWidth: 0.5, overflow: 'hidden', height: 46 },
  toggleSmBtn: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  toggleSmTxt: { fontSize: 14, fontWeight: '700' },
  label: { fontSize: 10, fontWeight: '600', marginBottom: 5, textTransform: 'uppercase', letterSpacing: 0.3 },
  resRow: { flexDirection: 'row', alignItems: 'center' },
  resItem: { flex: 1, alignItems: 'center' },
  resSub: { fontSize: 12, marginTop: 4 },
  resDividerV: { width: 0.5, height: 40, marginHorizontal: 10 },
  fusoInfo: { fontSize: 11, textAlign: 'center', marginTop: 12 },
  gabarito: { marginTop: 16, borderWidth: 0.5, borderRadius: 8, padding: 12, borderStyle: 'dashed' },
  gabaritoTxt: { fontSize: 12, textAlign: 'center' },
})
