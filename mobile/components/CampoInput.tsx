/**
 * mobile/components/CampoInput.tsx
 * Input field padronizado — elimina o padrão Campo repetido em 14 telas.
 *
 * Uso:
 *   <CampoInput label="NORTE (m)" value={norte} onChangeText={setNorte} placeholder="7395000.000" />
 *
 * Aceita qualquer prop de TextInput via spread.
 */
import { View, Text, TextInput, StyleSheet, TextInputProps } from 'react-native'
import { Colors } from '../constants/Colors'

interface Props extends TextInputProps {
    label: string
}

export function CampoInput({ label, style, ...resto }: Props) {
    const C = Colors.dark
    return (
        <View style={s.campo}>
            <Text style={[s.label, { color: C.muted }]}>{label}</Text>
            <TextInput
                style={[
                    s.input,
                    { color: C.text, borderColor: C.cardBorder, backgroundColor: C.background },
                    style,
                ]}
                placeholderTextColor={C.muted}
                keyboardType="numeric"
                returnKeyType="next"
                autoCorrect={false}
                autoCapitalize="none"
                {...resto}
            />
        </View>
    )
}

const s = StyleSheet.create({
    campo: { marginBottom: 12 },
    label: {
        fontSize: 11,
        fontWeight: '600',
        letterSpacing: 0.8,
        marginBottom: 6,
    },
    input: {
        borderRadius: 8,
        borderWidth: 0.5,
        paddingHorizontal: 12,
        paddingVertical: 11,
        fontSize: 15,
    },
})
