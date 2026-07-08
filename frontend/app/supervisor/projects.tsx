import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, Alert, ActivityIndicator, Modal, TextInput } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { projectAPI, Project, ProjectTask } from '../../services/api';
import { downloadAndSharePDF } from '../../utils/pdfHelper';

export default function SupervisorProjectsScreen() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [projects, setProjects] = useState<Project[]>([]);
  const [openId, setOpenId] = useState<string | null>(null);
  const [progressEditor, setProgressEditor] = useState<{ projectId: string; task: ProjectTask } | null>(null);
  const [progressValue, setProgressValue] = useState('0');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await projectAPI.getAll();
      setProjects(list);
    } catch (e: any) {
      Alert.alert('Erro', e?.response?.data?.detail || 'Falha ao carregar projetos');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const orderedTasks = (project: Project): { depth: number; task: ProjectTask }[] => {
    const byParent = new Map<string | null, ProjectTask[]>();
    for (const t of project.tasks) {
      const k = t.parent_id || null;
      if (!byParent.has(k)) byParent.set(k, []);
      byParent.get(k)!.push(t);
    }
    byParent.forEach(l => l.sort((a, b) => (a.order - b.order) || a.name.localeCompare(b.name)));
    const out: { depth: number; task: ProjectTask }[] = [];
    const walk = (p: string | null, d: number) => {
      for (const t of byParent.get(p) || []) {
        out.push({ depth: d, task: t });
        walk(t.id, d + 1);
      }
    };
    walk(null, 0);
    return out;
  };

  const projectProgress = (p: Project) => {
    if (!p.tasks?.length) return 0;
    return Math.round(p.tasks.reduce((a, t) => a + (Number(t.progress_percent) || 0), 0) / p.tasks.length);
  };

  const openProgress = (projectId: string, task: ProjectTask) => {
    setProgressEditor({ projectId, task });
    setProgressValue(String(task.progress_percent ?? 0));
  };

  const saveProgress = async () => {
    if (!progressEditor) return;
    const v = Math.max(0, Math.min(100, parseFloat(progressValue) || 0));
    try {
      const updated = await projectAPI.updateTaskProgress(progressEditor.projectId, progressEditor.task.id, v);
      setProjects(ps => ps.map(p => p.id === updated.id ? updated : p));
      setProgressEditor(null);
    } catch (e: any) {
      Alert.alert('Erro', e?.response?.data?.detail || 'Falha ao salvar progresso');
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} data-testid="sup-projects-back">
          <Ionicons name="arrow-back" size={26} color="#000" />
        </TouchableOpacity>
        <Text style={styles.title}>Projetos</Text>
        <View style={{ width: 26 }} />
      </View>

      {loading ? (
        <ActivityIndicator size="large" style={{ marginTop: 40 }} />
      ) : projects.length === 0 ? (
        <View style={styles.emptyBox}>
          <Ionicons name="folder-open-outline" size={64} color="#bbb" />
          <Text style={styles.emptyText}>Nenhum projeto disponível</Text>
        </View>
      ) : (
        <ScrollView contentContainerStyle={{ padding: 16 }}>
          {projects.map(p => {
            const isOpen = openId === p.id;
            const prog = projectProgress(p);
            return (
              <View key={p.id} style={styles.card} data-testid={`sup-project-${p.id}`}>
                <TouchableOpacity onPress={() => setOpenId(isOpen ? null : p.id)} style={styles.cardHeader}>
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
                    <Ionicons name={isOpen ? "chevron-up" : "chevron-down"} size={22} color="#666" />
                  </View>
                </TouchableOpacity>

                {isOpen && (
                  <View style={styles.tasksArea}>
                    {orderedTasks(p).map(({ depth, task }) => (
                      <View key={task.id} style={[styles.taskRow, { marginLeft: depth * 16 }]}>
                        <View style={{ flex: 1 }}>
                          <Text style={[styles.taskName, depth === 0 && { fontWeight: '700' }]}>{task.name}</Text>
                          <Text style={styles.taskMeta}>
                            {task.duration_value} {task.duration_unit} • {task.start_date || '-'} → {task.end_date || '-'}
                          </Text>
                          <View style={styles.progressBgSm}>
                            <View style={[styles.progressBarSm, { width: `${task.progress_percent}%` }]} />
                          </View>
                        </View>
                        <TouchableOpacity style={styles.progressBadge} onPress={() => openProgress(p.id, task)} data-testid={`sup-task-progress-${task.id}`}>
                          <Text style={styles.progressBadgeText}>{Number(task.progress_percent).toFixed(0)}%</Text>
                          <Ionicons name="create-outline" size={14} color="#fff" />
                        </TouchableOpacity>
                      </View>
                    ))}
                  </View>
                )}
              </View>
            );
          })}
        </ScrollView>
      )}

      <Modal visible={!!progressEditor} transparent animationType="fade" onRequestClose={() => setProgressEditor(null)}>
        <View style={styles.modalOverlay}>
          <View style={styles.progressModalBox}>
            <Text style={styles.modalTitle}>Atualizar Progresso</Text>
            <Text style={{ color: '#666', marginBottom: 12 }} numberOfLines={2}>{progressEditor?.task.name}</Text>
            <TextInput
              style={styles.progressInput}
              value={progressValue}
              onChangeText={setProgressValue}
              keyboardType="numeric"
              placeholder="0-100"
              data-testid="progress-input"
            />
            <Text style={{ color: '#666', fontSize: 12, marginTop: 4 }}>Digite um valor entre 0 e 100</Text>
            <View style={styles.modalActions}>
              <TouchableOpacity style={[styles.btn, styles.btnGhost]} onPress={() => setProgressEditor(null)}>
                <Text style={styles.btnGhostText}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[styles.btn, styles.btnPrimary]} onPress={saveProgress} data-testid="progress-save-btn">
                <Text style={styles.btnPrimaryText}>Salvar</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: 16, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#eee' },
  title: { fontSize: 20, fontWeight: '700', color: '#000' },
  card: { backgroundColor: '#fff', borderRadius: 12, marginBottom: 12, overflow: 'hidden' },
  cardHeader: { flexDirection: 'row', alignItems: 'center', padding: 14, gap: 10 },
  cardTitle: { fontSize: 15, fontWeight: '700', color: '#000' },
  cardSubtitle: { fontSize: 12, color: '#666', marginTop: 2 },
  progressBg: { height: 8, borderRadius: 4, backgroundColor: '#eee', marginTop: 8, overflow: 'hidden' },
  progressBar: { height: '100%', backgroundColor: '#6a1b9a' },
  progressLabel: { fontSize: 11, color: '#666', marginTop: 4 },
  tasksArea: { borderTopWidth: 1, borderTopColor: '#f0f0f0', padding: 8 },
  taskRow: { flexDirection: 'row', alignItems: 'center', gap: 8, padding: 8, backgroundColor: '#fafafa', marginTop: 4, borderRadius: 6 },
  taskName: { fontSize: 13, color: '#000' },
  taskMeta: { fontSize: 11, color: '#666', marginTop: 2 },
  progressBgSm: { height: 5, borderRadius: 3, backgroundColor: '#eee', marginTop: 4, overflow: 'hidden' },
  progressBarSm: { height: '100%', backgroundColor: '#4caf50' },
  progressBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: '#4caf50', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 12 },
  progressBadgeText: { color: '#fff', fontWeight: '700', fontSize: 12 },
  emptyBox: { alignItems: 'center', marginTop: 60 },
  emptyText: { color: '#888', fontSize: 16, marginTop: 12 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center' },
  progressModalBox: { backgroundColor: '#fff', borderRadius: 16, padding: 20, width: '85%', maxWidth: 400 },
  modalTitle: { fontSize: 18, fontWeight: '700', marginBottom: 12 },
  progressInput: { borderWidth: 1, borderColor: '#ddd', borderRadius: 8, padding: 12, fontSize: 24, textAlign: 'center', backgroundColor: '#fafafa' },
  modalActions: { flexDirection: 'row', gap: 12, marginTop: 16 },
  btn: { flex: 1, padding: 12, borderRadius: 10, alignItems: 'center' },
  btnGhost: { backgroundColor: '#f0f0f0' },
  btnGhostText: { color: '#333', fontWeight: '600' },
  btnPrimary: { backgroundColor: '#6a1b9a' },
  btnPrimaryText: { color: '#fff', fontWeight: '700' },
});
