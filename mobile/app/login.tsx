import { useState } from 'react'
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native'
import { useRouter } from 'expo-router'
import { Colors } from '../constants/Colors'
import { apiPost } from '../lib/api'
import { salvarSessao } from '../lib/auth'

const C = Colors.dark

export default function LoginScreen() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [carregando, setCarregando] = useState(false)

  async function entrar() {
    const emailTrim = email.trim().toLowerCase()
    if (!emailTrim || !senha) {
      Alert.alert('Campos obrigatórios', 'Preencha email e senha.')
      return
    }

    setCarregando(true)
    try {
      const resposta = await apiPost<{
        access_token: string
        refresh_token: string
        user_id: string
        email: string
      }>('/auth/login', { email: emailTrim, senha })

      await salvarSessao(resposta)
      router.replace('/(tabs)/projeto')
    } catch (erro: any) {
      Alert.alert('Falha no login', erro?.message || 'Email ou senha inválidos.')
    } finally {
      setCarregando(false)
    }
  }

  return (
    <KeyboardAvoidingView
      style={s.flex}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView contentContainerStyle={s.container} keyboardShouldPersistTaps="handled">
        {/* Logo / título */}
        <View style={s.logoArea}>
          <Text style={s.logoEmoji}>📐</Text>
          <Text style={s.logoTitulo}>GeoAdmin Pro</Text>
          <Text style={s.logoSub}>Sistema de gestão topográfica</Text>
        </View>

        {/* Formulário */}
        <View style={s.card}>
          <Text style={s.label}>Email</Text>
          <TextInput
            style={s.input}
            placeholder="topografo@empresa.com"
            placeholderTextColor={C.muted}
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
            value={email}
            onChangeText={setEmail}
            editable={!carregando}
          />

          <Text style={[s.label, { marginTop: 16 }]}>Senha</Text>
          <TextInput
            style={s.input}
            placeholder="••••••••"
            placeholderTextColor={C.muted}
            secureTextEntry
            value={senha}
            onChangeText={setSenha}
            editable={!carregando}
            onSubmitEditing={entrar}
            returnKeyType="done"
          />

          <TouchableOpacity
            style={[s.btnEntrar, carregando && { opacity: 0.7 }]}
            onPress={entrar}
            disabled={carregando}
          >
            {carregando
              ? <ActivityIndicator color={C.primaryText} />
              : <Text style={s.btnEntrarTxt}>Entrar</Text>}
          </TouchableOpacity>
        </View>

        <Text style={s.rodape}>
          Acesso restrito a topógrafos autorizados.
        </Text>
      </ScrollView>
    </KeyboardAvoidingView>
  )
}

const s = StyleSheet.create({
  flex: { flex: 1, backgroundColor: C.background },
  container: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: 24,
    paddingVertical: 48,
  },
  logoArea: {
    alignItems: 'center',
    marginBottom: 40,
  },
  logoEmoji: {
    fontSize: 56,
    marginBottom: 12,
  },
  logoTitulo: {
    fontSize: 28,
    fontWeight: '700',
    color: C.text,
    letterSpacing: 0.5,
  },
  logoSub: {
    fontSize: 14,
    color: C.muted,
    marginTop: 4,
  },
  card: {
    backgroundColor: C.card,
    borderRadius: 16,
    padding: 24,
    borderWidth: 1,
    borderColor: C.cardBorder,
  },
  label: {
    fontSize: 13,
    fontWeight: '600',
    color: C.muted,
    marginBottom: 6,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  input: {
    backgroundColor: C.background,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: C.cardBorder,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 15,
    color: C.text,
  },
  btnEntrar: {
    backgroundColor: C.primary,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 24,
  },
  btnEntrarTxt: {
    color: C.primaryText,
    fontSize: 16,
    fontWeight: '700',
  },
  rodape: {
    textAlign: 'center',
    color: C.muted,
    fontSize: 12,
    marginTop: 32,
  },
})
