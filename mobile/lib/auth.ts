/**
 * Gerenciamento de autenticação — armazenamento do token JWT.
 */
import AsyncStorage from '@react-native-async-storage/async-storage'
import { definirToken } from './api'

const CHAVE_TOKEN = '@geoadmin:access_token'
const CHAVE_REFRESH = '@geoadmin:refresh_token'
const CHAVE_USUARIO = '@geoadmin:usuario'

export interface SessaoUsuario {
  access_token: string
  refresh_token: string
  user_id: string
  email: string
}

export async function salvarSessao(sessao: SessaoUsuario): Promise<void> {
  await Promise.all([
    AsyncStorage.setItem(CHAVE_TOKEN, sessao.access_token),
    AsyncStorage.setItem(CHAVE_REFRESH, sessao.refresh_token),
    AsyncStorage.setItem(CHAVE_USUARIO, JSON.stringify({ user_id: sessao.user_id, email: sessao.email })),
  ])
  definirToken(sessao.access_token)
}

export async function carregarSessao(): Promise<SessaoUsuario | null> {
  const [token, refresh, usuarioRaw] = await Promise.all([
    AsyncStorage.getItem(CHAVE_TOKEN),
    AsyncStorage.getItem(CHAVE_REFRESH),
    AsyncStorage.getItem(CHAVE_USUARIO),
  ])

  if (!token || !refresh || !usuarioRaw) return null

  try {
    const usuario = JSON.parse(usuarioRaw)
    definirToken(token)
    return { access_token: token, refresh_token: refresh, ...usuario }
  } catch {
    return null
  }
}

export async function limparSessao(): Promise<void> {
  await Promise.all([
    AsyncStorage.removeItem(CHAVE_TOKEN),
    AsyncStorage.removeItem(CHAVE_REFRESH),
    AsyncStorage.removeItem(CHAVE_USUARIO),
  ])
  definirToken(null)
}
