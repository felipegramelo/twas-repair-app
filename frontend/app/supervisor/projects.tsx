import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, Alert, ActivityIndicator, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { projectAPI, Project } from '../../services/api';
import { downloadAndSharePDF } from '../../utils/pdfHelper';

const notify = (title: string, message: string) => {
  if (Platform.OS === 'web') {
    // eslint-disable-next-line no-alert
    window.alert(`${title}\n\n${message}`);
  } else {
    Alert.alert(title, message);
  }
};

export default function SupervisorProjectsScreen() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [projects, setProjects] = useState<Project[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await projectAPI.getAll();
      setProjects(list);
    } catch (e: any) {
      notify('Erro', e?.response?.data?.detail || 'Falha ao carregar projetos');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const overallProgress = (p: Project) => {
    if (!p.tasks?.length) return 0;
    return Math.round(p.tasks.reduce((a, t) => a + (Number(t.progress_percent) || 0), 0) / p.tasks.length);
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} data-testid="sup-projects-back">
          <Ionicons name="arrow-back" size={26} color="#000" />
        </TouchableOpacity>
        <Text style={styles.title}>Meus Projetos</Text>
        <View style={{ width: 26 }} />
      </View>

      {loading ? (
        <ActivityIndicator size="large" style={{ marginTop: 40 }} />
      ) : projects.length === 0 ? (
        <View style={styles.emptyBox}>
          <Ionicons name="folder-open-outline" size={64} color="#bbb" />
          <Text style={styles.emptyText}>Nenhum projeto atribuído a você</Text>
          <Text style={styles.emptyHint}>Aguarde um Administrador compartilhar projetos</Text>
        </View>
      ) : (
        <ScrollView contentContainerStyle={{ padding: 16 }}>
          {projects.map(p => {
            const prog = overallProgress(p);
            return (
              <TouchableOpacity
                key={p.id}
                style={styles.card}
                onPress={() => router.push(`/admin/edit-project?id=${p.id}`)}
                data-testid={`sup-project-${p.id}`}
              >
                <View style={{ flex: 1 }}>
                  <Text style={styles.cardTitle}>{p.title}</Text>
                  <Text style={styles.cardSubtitle}>OS: {p.os_number} • {p.embarcacao || '-'}</Text>
                  <View style={styles.progressBg}>
                    <View style={[styles.progressBar, { width: `${prog}%` }]} />
                  </View>
                  <Text style={styles.progressLabel}>{prog}% • {p.tasks?.length || 0} tarefas</Text>
                </View>
                <View style={{ flexDirection: 'row', gap: 8, alignItems: 'center' }}>
                  <TouchableOpacity onPress={() => downloadAndSharePDF(projectAPI.pdfUrl(p.id, false), `${p.os_number} - ${p.title} - PROJETO.pdf`, true)} data-testid={`sup-project-view-${p.id}`}>
                    <Ionicons name="eye-outline" size={22} color="#388e3c" />
                  </TouchableOpacity>
                  <TouchableOpacity onPress={() => downloadAndSharePDF(projectAPI.pdfUrl(p.id, true), `${p.os_number} - ${p.title} - PROJETO.pdf`, false)} data-testid={`sup-project-download-${p.id}`}>
                    <Ionicons name="download-outline" size={22} color="#f57c00" />
                  </TouchableOpacity>
                  <Ionicons name="chevron-forward" size={22} color="#666" />
                </View>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: 16, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#eee' },
  title: { fontSize: 20, fontWeight: '700', color: '#000' },
  card: { backgroundColor: '#fff', borderRadius: 12, padding: 16, flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 12 },
  cardTitle: { fontSize: 15, fontWeight: '700', color: '#000' },
  cardSubtitle: { fontSize: 12, color: '#666', marginTop: 2 },
  progressBg: { height: 8, borderRadius: 4, backgroundColor: '#eee', marginTop: 8, overflow: 'hidden' },
  progressBar: { height: '100%', backgroundColor: '#6a1b9a' },
  progressLabel: { fontSize: 11, color: '#666', marginTop: 4 },
  emptyBox: { alignItems: 'center', marginTop: 60, padding: 20 },
  emptyText: { color: '#888', fontSize: 16, marginTop: 12, fontWeight: '600' },
  emptyHint: { color: '#aaa', fontSize: 13, marginTop: 4, textAlign: 'center' },
});
