import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, ActivityIndicator, TouchableOpacity, Alert } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { apiGet, apiPost } from '../../../../lib/api';
import { useProjetoRealtime } from '../../../../hooks/useProjetoRealtime';

interface PendenciasResumo {
  total_lotes: number;
  lotes_com_participante: number;
  lotes_sem_participante: number;
  magic_links_enviados: number;
  magic_links_pendentes: number;
  confrontacoes_pendentes: number;
}

interface MensagemExterna {
  id: string;
  canal: string;
  conteudo: string;
  status: string;
  telefone?: string;
}

export default function PainelOperacionalScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [projeto, setProjeto] = useState<any>(null);
  const [resumo, setResumo] = useState<PendenciasResumo | null>(null);
  const [mensagens, setMensagens] = useState<MensagemExterna[]>([]);
  const [resumoDocumental, setResumoDocumental] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // MOCK TOKEN (Na prática viria de um AuthContext)
  const MOCK_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy";
  const { status: wsStatus, lastEvent } = useProjetoRealtime(id, MOCK_TOKEN);

  const fetchDados = async () => {
    try {
      const [dadosProj, msgs, resumoDocs] = await Promise.all([
        apiGet(`/projetos/${id}`),
        apiGet(`/projetos/${id}/mensagens-externas`),
        apiGet(`/projetos/${id}/gestao-documentos/resumo`)
      ]);
      setProjeto(dadosProj);
      setResumo(dadosProj.resumo);
      setMensagens(msgs);
      setResumoDocumental(resumoDocs);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDados();
  }, [id]);

  // Handle Eventos WS
  useEffect(() => {
    if (!lastEvent) return;
    console.log("Recebido Evento WS:", lastEvent.type);
    
    // Independentemente do evento operacional, o fallback de refetch garante a veracidade do banco
    // Ao invez de manipular arrays estáticos aqui com base no socket payload (que evita o perigo)
    fetchDados();
  }, [lastEvent]);

  // Fallback Polling (Se WS falhar)
  useEffect(() => {
    if (wsStatus === 'connected') return; // Se está via WS, não faz polling
    
    const interval = setInterval(() => {
      console.log("Polling Fallback executado");
      fetchDados();
    }, 30000); // 30s
    
    return () => clearInterval(interval);
  }, [wsStatus]);

  const [approvingMsgId, setApprovingMsgId] = useState<string | null>(null);

  const aprovarEEnviar = async (msgId: string) => {
    try {
      setApprovingMsgId(msgId);
      await apiPost(`/projetos/${id}/mensagens-externas/${msgId}/aprovar`, {});
      await apiPost(`/projetos/${id}/mensagens-externas/${msgId}/enviar`, {});
      Alert.alert("Sucesso", "Mensagem enviada (ou simulada em dry-run).");
      fetchDados();
    } catch (e: any) {
      Alert.alert("Erro", e.message);
    } finally {
      setApprovingMsgId(null);
    }
  };

  if (loading && !resumo) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>{error}</Text>
      </View>
    );
  }

  const msgsSaida = mensagens.filter(m => m.direcao === 'outbound' && (m.status === 'draft' || m.status === 'queued'));
  const msgsEntrada = mensagens.filter(m => m.direcao === 'inbound');

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Painel Operacional</Text>
      
      {resumo && (
        <View style={styles.grid}>
          <View style={styles.card}>
            <Text style={styles.cardValue}>{resumo.total_lotes}</Text>
            <Text style={styles.cardLabel}>Total de Lotes</Text>
          </View>
          
          <View style={[styles.card, resumo.lotes_sem_participante > 0 && styles.cardWarning]}>
            <Text style={styles.cardValue}>{resumo.lotes_sem_participante}</Text>
            <Text style={styles.cardLabel}>Sem Participante</Text>
          </View>

          <View style={[styles.card, resumo.magic_links_pendentes > 0 && styles.cardWarning]}>
            <Text style={styles.cardValue}>{resumo.magic_links_pendentes}</Text>
            <Text style={styles.cardLabel}>Links Pendentes</Text>
          </View>

          <View style={[styles.card, resumo.confrontacoes_pendentes > 0 && styles.cardWarning]}>
            <Text style={styles.cardValue}>{resumo.confrontacoes_pendentes}</Text>
            <Text style={styles.cardLabel}>Confrontações Abertas</Text>
          </View>
        </View>
      )}

      <Text style={styles.subtitle}>Gestão Documental</Text>
      {resumoDocumental ? (
        <View style={styles.grid}>
          <View style={styles.card}>
            <Text style={styles.cardValue}>{resumoDocumental.total}</Text>
            <Text style={styles.cardLabel}>Documentos Esperados</Text>
          </View>
          <View style={[styles.card, resumoDocumental.pendentes > 0 && styles.cardWarning]}>
            <Text style={styles.cardValue}>{resumoDocumental.pendentes}</Text>
            <Text style={styles.cardLabel}>Pendentes</Text>
          </View>
          <View style={[styles.card, resumoDocumental.recusados > 0 && {backgroundColor: '#FFEBEE'}]}>
            <Text style={styles.cardValue}>{resumoDocumental.recusados}</Text>
            <Text style={styles.cardLabel}>Recusados</Text>
          </View>
          <View style={styles.card}>
            <Text style={styles.cardValue}>{resumoDocumental.aprovados}</Text>
            <Text style={styles.cardLabel}>Aprovados</Text>
          </View>
        </View>
      ) : (
        <Text style={styles.emptyText}>Carregando informações documentais...</Text>
      )}

      <TouchableOpacity 
        style={[styles.actionButton, {backgroundColor: '#5856D6', marginTop: 10}]}
        onPress={() => router.push(`/projeto/documentos/${id}` as any)}
      >
        <Text style={styles.actionButtonText}>Abrir Lista de Uploads</Text>
      </TouchableOpacity>

      <TouchableOpacity 
        style={styles.actionButton}
        onPress={() => router.push(`/projeto/chat/${id}` as any)}
      >
        <Text style={styles.actionButtonText}>Abrir Chat Operacional</Text>
      </TouchableOpacity>

      <Text style={styles.subtitle}>Caixa de Entrada (Inbound)</Text>
      {msgsEntrada.length === 0 && (
        <Text style={styles.emptyText}>Nenhuma mensagem recebida recentemente.</Text>
      )}
      {msgsEntrada.map(msg => (
        <View key={msg.id} style={[styles.msgCard, { borderLeftColor: '#34C759' }]}>
          <Text style={styles.msgCanal}>Recebido via {msg.canal} | Tel: {msg.telefone} | Status: {msg.status}</Text>
          <Text style={styles.msgConteudo}>"{msg.conteudo}"</Text>
          {msg.status === 'unlinked' && (
            <Text style={{color: '#FF3B30', fontSize: 12, marginBottom: 8}}>⚠️ Telefone desconhecido. Vincule manualmente.</Text>
          )}
          {msg.status === 'ambiguous' && (
            <Text style={{color: '#FF9500', fontSize: 12, marginBottom: 8}}>⚠️ Múltiplos vínculos encontrados.</Text>
          )}
        </View>
      ))}

      <Text style={styles.subtitle}>Respostas Sugeridas ({msgsSaida.length})</Text>
      {msgsSaida.length === 0 && (
        <Text style={styles.emptyText}>Nenhuma mensagem aguardando aprovação.</Text>
      )}
      {msgsSaida.map(msg => (
        <View key={msg.id} style={styles.msgCard}>
          <Text style={styles.msgCanal}>Sugerido para: {msg.telefone || 'Sem número'}</Text>
          <Text style={styles.msgConteudo}>"{msg.conteudo}"</Text>
          <TouchableOpacity 
            style={[styles.approveButton, approvingMsgId === msg.id && { opacity: 0.7 }]} 
            onPress={() => aprovarEEnviar(msg.id)}
            disabled={approvingMsgId === msg.id}
          >
            {approvingMsgId === msg.id ? (
              <ActivityIndicator size="small" color="#FFF" />
            ) : (
              <Text style={styles.approveButtonText}>Aprovar e Enviar</Text>
            )}
          </TouchableOpacity>
        </View>
      ))}

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F2F2F7',
    padding: 16,
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 20,
    color: '#1C1C1E',
  },
  subtitle: {
    fontSize: 18,
    fontWeight: '600',
    marginTop: 30,
    marginBottom: 10,
    color: '#1C1C1E',
  },
  emptyText: {
    color: '#8E8E93',
    fontStyle: 'italic',
  },
  errorText: {
    color: '#FF3B30',
    fontSize: 16,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  card: {
    width: '48%',
    backgroundColor: '#FFFFFF',
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  cardWarning: {
    backgroundColor: '#FFF4E5',
    borderColor: '#FF9500',
    borderWidth: 1,
  },
  cardValue: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#1C1C1E',
    marginBottom: 4,
  },
  cardLabel: {
    fontSize: 14,
    color: '#8E8E93',
    textAlign: 'center',
  },
  actionButton: {
    backgroundColor: '#007AFF',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 10,
  },
  actionButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  msgCard: {
    backgroundColor: '#FFF',
    padding: 16,
    borderRadius: 8,
    marginBottom: 12,
    borderLeftWidth: 4,
    borderLeftColor: '#FF9500'
  },
  msgCanal: {
    fontSize: 12,
    color: '#8E8E93',
    marginBottom: 6
  },
  msgConteudo: {
    fontSize: 15,
    color: '#1C1C1E',
    fontStyle: 'italic',
    marginBottom: 12
  },
  approveButton: {
    backgroundColor: '#34C759',
    padding: 10,
    borderRadius: 6,
    alignItems: 'center'
  },
  approveButtonText: {
    color: '#FFF',
    fontWeight: '600'
  }
});
