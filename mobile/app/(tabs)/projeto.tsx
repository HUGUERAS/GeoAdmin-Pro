import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { apiGet, getApiBaseUrl } from '@/lib/api';

type Projeto = {
  id: string;
  nome?: string;
  projeto_nome?: string;
  status?: string;
  zona_utm?: string;
  municipio?: string;
  numero_job?: string;
};

type ProjetosResponse = {
  total: number;
  projetos: Projeto[];
};

export default function ProjetoScreen() {
  const [carregando, setCarregando] = useState(true);
  const [backendOnline, setBackendOnline] = useState(false);
  const [erroProjetos, setErroProjetos] = useState('');
  const [projetos, setProjetos] = useState<Projeto[]>([]);

  async function carregar() {
    setCarregando(true);
    setErroProjetos('');

    try {
      await apiGet<{ status: string }>('/health');
      setBackendOnline(true);
    } catch (error) {
      setBackendOnline(false);
      setErroProjetos(error instanceof Error ? error.message : 'Backend indisponível.');
      setProjetos([]);
      setCarregando(false);
      return;
    }

    try {
      const resposta = await apiGet<ProjetosResponse>('/projetos');
      setProjetos(resposta.projetos);
    } catch (error) {
      setErroProjetos(
        error instanceof Error
          ? error.message
          : 'Não foi possível carregar os projetos.'
      );
      setProjetos([]);
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregar();
  }, []);

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Projetos</Text>
      <Text style={styles.subtitle}>
        Backend atual: <Text style={styles.highlight}>{getApiBaseUrl()}</Text>
      </Text>

      <View style={styles.statusCard}>
        <Text style={styles.statusTitle}>Conexão com o backend</Text>
        <Text style={[styles.statusValue, backendOnline ? styles.online : styles.offline]}>
          {backendOnline ? 'Online' : 'Offline'}
        </Text>
        <Pressable onPress={carregar} style={styles.button}>
          <Text style={styles.buttonText}>Atualizar status</Text>
        </Pressable>
      </View>

      <View style={styles.listCard}>
        <Text style={styles.listTitle}>Projetos do backend</Text>

        {carregando ? (
          <View style={styles.loadingRow}>
            <ActivityIndicator color="#FFFFFF" />
            <Text style={styles.loadingText}>Buscando dados...</Text>
          </View>
        ) : null}

        {!carregando && erroProjetos ? (
          <Text style={styles.warning}>
            {erroProjetos}
            {'\n\n'}
            Se o `/health` respondeu mas os projetos falharam, o backend provavelmente está sem Supabase configurado em `backend/.env`.
          </Text>
        ) : null}

        {!carregando && !erroProjetos && projetos.length === 0 ? (
          <Text style={styles.empty}>Nenhum projeto retornado pelo backend.</Text>
        ) : null}

        {projetos.map((projeto) => (
          <View key={projeto.id} style={styles.projetoCard}>
            <Text style={styles.projetoNome}>
              {projeto.nome || projeto.projeto_nome || 'Projeto sem nome'}
            </Text>
            <Text style={styles.projetoMeta}>Status: {projeto.status || 'não informado'}</Text>
            <Text style={styles.projetoMeta}>Zona UTM: {projeto.zona_utm || 'não informada'}</Text>
            <Text style={styles.projetoMeta}>Município: {projeto.municipio || 'não informado'}</Text>
            <Text style={styles.projetoMeta}>Job: {projeto.numero_job || 'sem job'}</Text>
          </View>
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    backgroundColor: '#0b0b0b',
    paddingHorizontal: 16,
    paddingTop: 32,
    paddingBottom: 32,
    gap: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  subtitle: {
    fontSize: 14,
    color: '#CCCCCC',
    lineHeight: 20,
  },
  highlight: {
    color: '#7BDFF2',
  },
  statusCard: {
    backgroundColor: '#141414',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: '#222222',
    gap: 10,
  },
  statusTitle: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '600',
  },
  statusValue: {
    fontSize: 16,
    fontWeight: '700',
  },
  online: {
    color: '#87E887',
  },
  offline: {
    color: '#FF9F9F',
  },
  button: {
    alignSelf: 'flex-start',
    backgroundColor: '#1E5EFF',
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  buttonText: {
    color: '#FFFFFF',
    fontWeight: '700',
  },
  listCard: {
    backgroundColor: '#141414',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: '#222222',
    gap: 12,
  },
  listTitle: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '600',
  },
  loadingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  loadingText: {
    color: '#D9D9D9',
  },
  warning: {
    color: '#FFB86C',
    lineHeight: 20,
  },
  empty: {
    color: '#B8B8B8',
  },
  projetoCard: {
    backgroundColor: '#0f0f0f',
    borderRadius: 12,
    padding: 14,
    gap: 6,
  },
  projetoNome: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
  projetoMeta: {
    color: '#BBBBBB',
    fontSize: 13,
  },
});

