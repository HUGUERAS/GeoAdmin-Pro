import React, { useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { apiPost, getApiBaseUrl } from '@/lib/api';

type InversoResponse = {
  distancia: number;
  azimute_decimal: number;
  azimute_graus_ms: string;
};

type Campo = 'x1' | 'y1' | 'x2' | 'y2';

export default function CalculosScreen() {
  const [form, setForm] = useState({
    x1: '',
    y1: '',
    x2: '',
    y2: '',
  });
  const [resultado, setResultado] = useState<InversoResponse | null>(null);
  const [erro, setErro] = useState('');
  const [carregando, setCarregando] = useState(false);

  function atualizarCampo(campo: Campo, valor: string) {
    setForm((estadoAtual) => ({
      ...estadoAtual,
      [campo]: valor,
    }));
  }

  async function calcularInverso() {
    setErro('');
    setResultado(null);

    const payload = Object.fromEntries(
      Object.entries(form).map(([chave, valor]) => [chave, Number(valor.replace(',', '.'))])
    ) as Record<Campo, number>;

    if (Object.values(payload).some((valor) => Number.isNaN(valor))) {
      setErro('Preencha os quatro campos com números válidos.');
      return;
    }

    try {
      setCarregando(true);
      const resposta = await apiPost<InversoResponse>('/geo/inverso', payload);
      setResultado(resposta);
    } catch (error) {
      setErro(error instanceof Error ? error.message : 'Falha ao calcular inverso.');
    } finally {
      setCarregando(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Cálculos</Text>
      <Text style={styles.subtitle}>
        Esta tela já chama o backend real em <Text style={styles.highlight}>{getApiBaseUrl()}</Text>
      </Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Cálculo Inverso</Text>
        <Text style={styles.cardSubtitle}>
          Informe dois pontos para obter distância e azimute via endpoint <Text style={styles.highlight}>/geo/inverso</Text>.
        </Text>

        <View style={styles.grid}>
          <CampoInput label="X1" value={form.x1} onChangeText={(valor) => atualizarCampo('x1', valor)} />
          <CampoInput label="Y1" value={form.y1} onChangeText={(valor) => atualizarCampo('y1', valor)} />
          <CampoInput label="X2" value={form.x2} onChangeText={(valor) => atualizarCampo('x2', valor)} />
          <CampoInput label="Y2" value={form.y2} onChangeText={(valor) => atualizarCampo('y2', valor)} />
        </View>

        <Pressable onPress={calcularInverso} style={styles.button}>
          <Text style={styles.buttonText}>Calcular no backend</Text>
        </Pressable>

        {carregando ? (
          <View style={styles.loadingRow}>
            <ActivityIndicator color="#FFFFFF" />
            <Text style={styles.loadingText}>Consultando backend...</Text>
          </View>
        ) : null}

        {erro ? <Text style={styles.error}>{erro}</Text> : null}

        {resultado ? (
          <View style={styles.resultBox}>
            <LinhaResultado label="Distância" value={`${resultado.distancia.toFixed(6)} m`} />
            <LinhaResultado label="Azimute decimal" value={`${resultado.azimute_decimal.toFixed(6)}°`} />
            <LinhaResultado label="Azimute GMS" value={resultado.azimute_graus_ms} />
          </View>
        ) : null}
      </View>
    </ScrollView>
  );
}

function CampoInput({
  label,
  value,
  onChangeText,
}: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
}) {
  return (
    <View style={styles.inputGroup}>
      <Text style={styles.inputLabel}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        keyboardType="numeric"
        placeholder="0.0"
        placeholderTextColor="#666666"
        style={styles.input}
      />
    </View>
  );
}

function LinhaResultado({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.resultRow}>
      <Text style={styles.resultLabel}>{label}</Text>
      <Text style={styles.resultValue}>{value}</Text>
    </View>
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
  card: {
    backgroundColor: '#141414',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: '#222222',
    gap: 14,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  cardSubtitle: {
    fontSize: 13,
    color: '#B8B8B8',
    lineHeight: 18,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  inputGroup: {
    width: '47%',
    gap: 6,
  },
  inputLabel: {
    color: '#E8E8E8',
    fontSize: 13,
    fontWeight: '600',
  },
  input: {
    backgroundColor: '#0f0f0f',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#2C2C2C',
    color: '#FFFFFF',
    paddingHorizontal: 12,
    paddingVertical: 12,
  },
  button: {
    backgroundColor: '#1E5EFF',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '700',
  },
  loadingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  loadingText: {
    color: '#D9D9D9',
  },
  error: {
    color: '#FF9F9F',
    lineHeight: 20,
  },
  resultBox: {
    backgroundColor: '#0f0f0f',
    borderRadius: 12,
    padding: 14,
    gap: 10,
  },
  resultRow: {
    gap: 4,
  },
  resultLabel: {
    color: '#8C8C8C',
    fontSize: 12,
    textTransform: 'uppercase',
  },
  resultValue: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
});

