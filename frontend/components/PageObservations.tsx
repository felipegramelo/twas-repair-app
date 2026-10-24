import React from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Platform, Alert } from 'react-native';

const CHARS_PER_LINE = 105;
const MAX_LINES = 11;
const MAX_CHARS = 1200;

const visualLines = (text: string) =>
  text.split(/\r\n|\r|\n/).reduce((t, l) => t + Math.max(1, Math.ceil(l.length / CHARS_PER_LINE)), 0);

export const clampObservations = (text: string): string => {
  if (visualLines(text) <= MAX_LINES && text.length <= MAX_CHARS) return text;
  const msg = `Limite atingido: máximo de ${MAX_CHARS} caracteres ou ${MAX_LINES} linhas visuais.`;
  if (Platform.OS === 'web') window.alert(msg); else Alert.alert('Limite atingido', msg);
  const out: string[] = [];
  let count = 0;
  for (const line of text.split(/\r\n|\r|\n/)) {
    const needed = Math.max(1, Math.ceil(line.length / CHARS_PER_LINE));
    if (count + needed <= MAX_LINES) { out.push(line); count += needed; }
    else { const rem = MAX_LINES - count; if (rem > 0) out.push(line.substring(0, rem * CHARS_PER_LINE)); break; }
  }
  return out.join('\n').substring(0, MAX_CHARS);
};

interface Props {
  pages: number;
  observations: string;
  pageObservations: Record<string, string>;
  onChange: (next: Record<string, string>) => void;
}

// Observations for pages 2+: copied from page 1 by default, editable per page.
export const PageObservations = ({ pages, observations, pageObservations, onChange }: Props) => {
  if (pages <= 1) return null;
  return (
    <>
      {Array.from({ length: pages - 1 }, (_, i) => String(i + 2)).map((p) => {
        const overridden = pageObservations[p] !== undefined;
        const value = overridden ? pageObservations[p] : observations;
        return (
          <View key={`obs-page-${p}`} style={styles.section} testID={`page-observations-${p}`}>
            <View style={styles.row}>
              <Text style={styles.label}>Observações — Página {p}</Text>
              <Text style={[styles.counter, (visualLines(value) > MAX_LINES || value.length >= MAX_CHARS) && styles.counterWarn]}>
                {value.length}/{MAX_CHARS} ({visualLines(value)}/{MAX_LINES} linhas)
              </Text>
            </View>
            <Text style={styles.hint} testID={`page-observations-${p}-hint`}>
              {overridden ? 'Texto próprio desta página.' : 'Copiado da página 1 — edite se necessário.'}
            </Text>
            <TextInput
              style={styles.input}
              value={value}
              placeholder="Observações desta página"
              onChangeText={(t) => onChange({ ...pageObservations, [p]: clampObservations(t) })}
              multiline
              numberOfLines={6}
              blurOnSubmit={false}
              testID={`page-observations-${p}-input`}
            />
            {overridden && (
              <TouchableOpacity
                onPress={() => { const next = { ...pageObservations }; delete next[p]; onChange(next); }}
                testID={`page-observations-${p}-reset`}
              >
                <Text style={styles.reset}>Voltar a copiar da página 1</Text>
              </TouchableOpacity>
            )}
          </View>
        );
      })}
    </>
  );
};

const styles = StyleSheet.create({
  section: { marginBottom: 24 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  label: { fontSize: 16, fontWeight: '600', color: '#212121', marginBottom: 4 },
  counter: { fontSize: 12, color: '#999' },
  counterWarn: { color: '#d32f2f' },
  hint: { fontSize: 12, color: '#666', fontStyle: 'italic', marginBottom: 8 },
  input: { backgroundColor: '#fff', borderRadius: 8, padding: 16, fontSize: 16, borderWidth: 1, borderColor: '#e0e0e0', minHeight: 100, textAlignVertical: 'top' },
  reset: { fontSize: 13, color: '#1565c0', marginTop: 8, fontWeight: '600' },
});
