import { StyleSheet, Platform } from 'react-native';


export const ss = StyleSheet.create({
    // ── Layout ──────────────────────────────────────────────
    container: { flex: 1 },

    body: { padding: 16, gap: 12, paddingBottom: 40 },

    // ── Card / seção ────────────────────────────────────────
    card: {
        borderRadius: 12,
        borderWidth: 0.5,
        padding: 16,
    },

    secaoLabel: {
        fontSize: 12,
        fontWeight: '600',
        letterSpacing: 0.8,
        textTransform: 'uppercase',
        marginBottom: 6,
        marginTop: 4,
    },

    // ── Formulário ──────────────────────────────────────────
    campo: { marginBottom: 12 },

    campoRow: { flexDirection: 'row', gap: 10 },

    campoHalf: { flex: 1 },

    campoLabel: {
        fontSize: 11,
        fontWeight: '600',
        letterSpacing: 0.8,
        marginBottom: 6,
    },

    input: {
        borderRadius: 8,
        borderWidth: 0.5,
        paddingHorizontal: 12,
        paddingVertical: Platform.OS === 'ios' ? 12 : 10,
        fontSize: 15,
    },

    // ── Botões de ação ──────────────────────────────────────
    btns: { flexDirection: 'row', gap: 10, marginTop: 4 },

    btnPri: {
        flex: 1,
        borderRadius: 10,
        paddingVertical: 14,
        alignItems: 'center',
        justifyContent: 'center',
    },

    btnPriTxt: { fontSize: 15, fontWeight: '700' },

    btnSec: {
        flex: 1,
        borderRadius: 10,
        paddingVertical: 14,
        alignItems: 'center',
        justifyContent: 'center',
        borderWidth: 0.5,
    },

    btnSecTxt: { fontSize: 15, fontWeight: '600' },

    // ── Resultado ────────────────────────────────────────────
    resultado: {
        borderRadius: 12,
        borderWidth: 1,
        padding: 18,
        gap: 4,
    },

    resLabel: {
        fontSize: 11,
        fontWeight: '600',
        letterSpacing: 0.8,
        textTransform: 'uppercase',
        marginBottom: 2,
    },

    resValor: {
        fontSize: 22,
        fontWeight: '700',
        letterSpacing: 0.3,
    },

    resUnidade: { fontSize: 13 },

    resLinha: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'baseline',
        paddingVertical: 6,
        borderBottomWidth: 0.5,
    },

    // ── Estados  ─────────────────────────────────────────────
    centro: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        gap: 12,
        paddingHorizontal: 24,
    },

    msgCentro: { fontSize: 16, fontWeight: '600', textAlign: 'center' },

    subCentro: { fontSize: 13, textAlign: 'center', lineHeight: 20 },
});
