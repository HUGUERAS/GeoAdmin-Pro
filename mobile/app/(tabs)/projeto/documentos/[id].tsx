import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { apiGet, apiPost } from '../../../../lib/api'; // Mock de importe do projeto

export default function DocumentosScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [pendentes, setPendentes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchDocs = async () => {
    setLoading(true);
    try {
      const data = await apiGet(`/projetos/${id}/gestao-documentos/pendentes`);
      setPendentes(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, [id]);

  const simularUpload = async (docId: string) => {
    try {
      await apiPost(`/projetos/${id}/gestao-documentos/upload`, {
        documento_id: docId,
        nome_arquivo: 'foto_rg.jpg',
        storage_path: 'uploads/dummy/foto_rg.jpg'
      });
      Alert.alert("Sucesso", "Documento enviado (Mock)");
      fetchDocs();
    } catch (err: any) {
      Alert.alert("Erro", err.message);
    }
  };

  if (loading) {
    return (
      <View style={styles.container}>
        <Text>Carregando documentos pendentes...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Lista de Uploads Pendentes</Text>

      {pendentes.length === 0 ? (
        <Text style={styles.emptyText}>Sem pendências para este projeto.</Text>
      ) : (
        pendentes.map(doc => (
          <View key={doc.id} style={styles.card}>
            <Text style={styles.docTipo}>{doc.tipo_documento.toUpperCase()}</Text>
            <Text style={styles.docInfo}>Participante: {doc.participante_id || 'Projeto Geral'}</Text>
            <TouchableOpacity 
              style={styles.uploadBtn}
              onPress={() => simularUpload(doc.id)}
            >
              <Text style={styles.uploadBtnText}>Simular Anexo do Arquivo</Text>
            </TouchableOpacity>
          </View>
        ))
      )}

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16, backgroundColor: '#F2F2F7' },
  title: { fontSize: 22, fontWeight: '700', marginBottom: 16, color: '#000' },
  card: { backgroundColor: '#FFF', padding: 16, borderRadius: 12, marginBottom: 12, elevation: 1 },
  docTipo: { fontSize: 16, fontWeight: 'bold', color: '#000' },
  docInfo: { fontSize: 14, color: '#666', marginTop: 4, marginBottom: 12 },
  emptyText: { fontSize: 14, color: '#666', textAlign: 'center', marginTop: 32 },
  uploadBtn: { backgroundColor: '#007AFF', padding: 12, borderRadius: 8, alignItems: 'center' },
  uploadBtnText: { color: '#FFF', fontWeight: '600' }
});
