import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, StyleSheet, ScrollView, RefreshControl, TouchableOpacity, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { Feather } from '@expo/vector-icons';
import { Colors } from '../../../constants/Colors';
import { apiGet } from '../../../lib/api';

export default function AdminMasterScreen() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [resumo, setResumo] = useState<any>(null);
  const [projetos, setProjetos] = useState<any[]>([]);
  const [alertas, setAlertas] = useState<any[]>([]);

  const loadData = async () => {
    try {
      setError(null);
      const [resumoData, projetosData, alertasData] = await Promise.all([
        apiGet<any>('/admin/master/resumo'),
        apiGet<any>('/admin/master/projetos'),
        apiGet<any>('/admin/master/alertas')
      ]);
      setResumo(resumoData);
      setProjetos(projetosData);
      setAlertas(alertasData);
    } catch (err: any) {
      if (err.message?.includes('401') || err.message?.includes('403')) {
        setError('Acesso negado. Apenas administradores podem ver este painel.');
      } else {
        setError(err.message || 'Falha ao carregar dados do painel master.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // Refresh a cada 15 segundos (polling operacional)
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, []);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  }, []);

  const C = Colors.dark;

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: C.background, justifyContent: 'center', alignItems: 'center' }]}>
        <ActivityIndicator size="large" color={C.primary} />
        <Text style={{ color: C.muted, marginTop: 16 }}>Carregando Painel Master...</Text>
      </View>
    );
  }

  return (
    <ScrollView 
      style={[styles.container, { backgroundColor: C.background }]}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={C.primary} />}
    >
      <View style={styles.header}>
        <Text style={[styles.title, { color: C.text }]}>Visão Executiva (Master)</Text>
        <Text style={[styles.subtitle, { color: C.muted }]}>Monitoramento da Operação REURB</Text>
      </View>

      {error ? (
        <View style={[styles.alertCard, { backgroundColor: 'rgba(239, 68, 68, 0.1)', borderColor: 'rgba(239, 68, 68, 0.3)' }]}>
          <Feather name="alert-triangle" size={24} color="#ef4444" />
          <Text style={[styles.alertText, { color: '#ef4444' }]}>{error}</Text>
        </View>
      ) : (
        <>
          {/* Métricas Principais */}
          {resumo && (
            <View style={styles.metricsGrid}>
              <View style={[styles.metricCard, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
                <Feather name="map" size={20} color={C.primary} />
                <Text style={[styles.metricValue, { color: C.text }]}>{resumo.total_projetos}</Text>
                <Text style={[styles.metricLabel, { color: C.muted }]}>Projetos Ativos</Text>
              </View>

              <View style={[styles.metricCard, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
                <Feather name="layers" size={20} color={C.primary} />
                <Text style={[styles.metricValue, { color: C.text }]}>{resumo.total_lotes}</Text>
                <Text style={[styles.metricLabel, { color: C.muted }]}>Total de Lotes</Text>
                {resumo.lotes_sem_participante > 0 && (
                  <Text style={[styles.metricWarning, { color: '#f59e0b' }]}>{resumo.lotes_sem_participante} sem participante</Text>
                )}
              </View>

              <View style={[styles.metricCard, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
                <Feather name="file-text" size={20} color={C.primary} />
                <Text style={[styles.metricValue, { color: C.text }]}>{resumo.documentos_pendentes}</Text>
                <Text style={[styles.metricLabel, { color: C.muted }]}>Docs Pendentes</Text>
                <Text style={[styles.metricSuccess, { color: '#10b981' }]}>{resumo.documentos_aprovados} aprovados</Text>
              </View>

              <View style={[styles.metricCard, { backgroundColor: C.card, borderColor: C.cardBorder }]}>
                <Feather name="message-square" size={20} color={C.primary} />
                <Text style={[styles.metricValue, { color: C.text }]}>{resumo.mensagens_pendentes_aprovacao}</Text>
                <Text style={[styles.metricLabel, { color: C.muted }]}>Msg Pendentes</Text>
                {resumo.inbounds_nao_vinculados > 0 && (
                  <Text style={[styles.metricWarning, { color: '#f59e0b' }]}>{resumo.inbounds_nao_vinculados} órfãs</Text>
                )}
              </View>
            </View>
          )}

          {/* Alertas Críticos */}
          {alertas && alertas.length > 0 && (
            <View style={styles.section}>
              <Text style={[styles.sectionTitle, { color: C.text }]}>Alertas da Operação</Text>
              {alertas.map((alerta, index) => (
                <View key={index} style={[styles.alertaItem, { backgroundColor: C.card, borderColor: 'rgba(245, 158, 11, 0.3)' }]}>
                  <Feather name="alert-circle" size={20} color="#f59e0b" style={{ marginRight: 12 }} />
                  <View style={{ flex: 1 }}>
                    <Text style={{ color: C.text, fontWeight: '600', fontSize: 14 }}>{alerta.tipo.replace('_', ' ').toUpperCase()}</Text>
                    <Text style={{ color: C.muted, fontSize: 13, marginTop: 4 }}>
                      {alerta.projeto_nome ? `${alerta.projeto_nome}: ` : ''}{alerta.mensagem}
                    </Text>
                  </View>
                </View>
              ))}
            </View>
          )}

          {/* Lista de Projetos */}
          <View style={styles.section}>
            <Text style={[styles.sectionTitle, { color: C.text }]}>Projetos em Andamento</Text>
            {projetos && projetos.map(p => (
              <TouchableOpacity 
                key={p.id} 
                style={[styles.projetoCard, { backgroundColor: C.card, borderColor: C.cardBorder }]}
                onPress={() => router.push(`/projeto/${p.id}`)}
              >
                <View style={styles.projetoHeader}>
                  <View>
                    <Text style={[styles.projetoTitle, { color: C.text }]}>{p.nome}</Text>
                    <Text style={[styles.projetoSubtitle, { color: C.muted }]}>{p.lotes} lotes</Text>
                  </View>
                  <View style={styles.badgeContainer}>
                    <Text style={[
                      styles.badge, 
                      p.status === 'em_andamento' ? { backgroundColor: 'rgba(245, 158, 11, 0.2)', color: '#f59e0b' } : { backgroundColor: 'rgba(16, 185, 129, 0.2)', color: '#10b981' }
                    ]}>
                      {p.percentual_conclusao}%
                    </Text>
                    <Feather name="chevron-right" size={20} color={C.muted} />
                  </View>
                </View>
              </TouchableOpacity>
            ))}
            {(!projetos || projetos.length === 0) && (
              <Text style={{ color: C.muted, textAlign: 'center', marginVertical: 20 }}>Nenhum projeto encontrado.</Text>
            )}
          </View>
        </>
      )}
      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
  },
  header: {
    marginBottom: 24,
    marginTop: 8,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
  },
  alertCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderRadius: 8,
    borderWidth: 1,
    marginBottom: 24,
  },
  alertText: {
    marginLeft: 12,
    flex: 1,
    fontSize: 14,
    fontWeight: '500',
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: 24,
  },
  metricCard: {
    width: '48%',
    borderRadius: 12,
    borderWidth: 1,
    padding: 16,
    marginBottom: 16,
    alignItems: 'flex-start',
  },
  metricValue: {
    fontSize: 28,
    fontWeight: '700',
    marginVertical: 8,
  },
  metricLabel: {
    fontSize: 13,
    fontWeight: '500',
  },
  metricWarning: {
    fontSize: 11,
    fontWeight: '600',
    marginTop: 4,
  },
  metricSuccess: {
    fontSize: 11,
    fontWeight: '600',
    marginTop: 4,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 16,
  },
  alertaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderRadius: 8,
    borderWidth: 1,
    marginBottom: 12,
  },
  projetoCard: {
    borderRadius: 12,
    borderWidth: 1,
    padding: 16,
    marginBottom: 12,
  },
  projetoHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  projetoTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  projetoSubtitle: {
    fontSize: 13,
  },
  badgeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    fontSize: 12,
    fontWeight: '700',
    overflow: 'hidden',
    marginRight: 8,
  }
});
