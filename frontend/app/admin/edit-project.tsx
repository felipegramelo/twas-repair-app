import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, TextInput, Alert, ActivityIndicator, Modal, Switch, Platform } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { projectAPI, Project, ProjectTask } from '../../services/api';

interface TaskForm {
  id?: string;
  name: string;
  parent_id: string | null;
  duration_value: string;
  duration_unit: 'dias' | 'hrs';
  start_date: string;
  end_date: string;
  progress_percent: string;
  order: number;
  notes: string;
}

const emptyTask = (): TaskForm => ({
  name: '', parent_id: null, duration_value: '', duration_unit: 'dias',
  start_date: '', end_date: '', progress_percent: '0', order: 0, notes: '',
});

export default function EditProjectScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [project, setProject] = useState<Project | null>(null);
  const [showTaskModal, setShowTaskModal] = useState(false);
  const [taskForm, setTaskForm] = useState<TaskForm>(emptyTask());
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const p = await projectAPI.getById(id);
      setProject(p);
    } catch (e: any) {
      Alert.alert('Erro', e?.response?.data?.detail || 'Falha ao carregar');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  // Order tasks hierarchically
  const orderedTasks = useCallback((): { depth: number; task: ProjectTask }[] => {
    if (!project) return [];
    const byParent = new Map<string | null, ProjectTask[]>();
    for (const t of project.tasks) {
      const key = t.parent_id || null;
      if (!byParent.has(key)) byParent.set(key, []);
      byParent.get(key)!.push(t);
    }
    byParent.forEach(lst => lst.sort((a, b) => (a.order - b.order) || a.name.localeCompare(b.name)));
    const out: { depth: number; task: ProjectTask }[] = [];
    const walk = (parent: string | null, depth: number) => {
      for (const t of byParent.get(parent) || []) {
        out.push({ depth, task: t });
        walk(t.id, depth + 1);
      }
    };
    walk(null, 0);
    return out;
  }, [project]);

  const saveProjectMeta = async (patch: Partial<Project>) => {
    if (!project) return;
    setSaving(true);
    try {
      const p = await projectAPI.update(project.id, patch);
      setProject(p);
    } catch (e: any) {
      Alert.alert('Erro', e?.response?.data?.detail || 'Falha ao salvar');
    } finally {
      setSaving(false);
    }
  };

  const openNewTask = (parent_id: string | null = null) => {
    setEditingTaskId(null);
    setTaskForm({ ...emptyTask(), parent_id });
    setShowTaskModal(true);
  };

  const openEditTask = (t: ProjectTask) => {
    setEditingTaskId(t.id);
    setTaskForm({
      id: t.id, name: t.name, parent_id: t.parent_id, duration_value: String(t.duration_value ?? ''),
      duration_unit: (t.duration_unit as any) || 'dias',
      start_date: t.start_date || '', end_date: t.end_date || '',
      progress_percent: String(t.progress_percent ?? 0), order: t.order || 0, notes: t.notes || '',
    });
    setShowTaskModal(true);
  };

  const saveTask = async () => {
    if (!project) return;
    if (!taskForm.name.trim()) {
      Alert.alert('Erro', 'Informe o nome da tarefa');
      return;
    }
    const payload = {
      name: taskForm.name.trim(),
      parent_id: taskForm.parent_id || null,
      duration_value: parseFloat(taskForm.duration_value) || 0,
      duration_unit: taskForm.duration_unit,
      start_date: taskForm.start_date || null,
      end_date: taskForm.end_date || null,
      progress_percent: Math.max(0, Math.min(100, parseFloat(taskForm.progress_percent) || 0)),
      order: taskForm.order,
      notes: taskForm.notes,
    };
    try {
      if (editingTaskId) {
        await projectAPI.updateTask(project.id, editingTaskId, payload);
      } else {
        await projectAPI.addTask(project.id, payload);
      }
      setShowTaskModal(false);
      await load();
    } catch (e: any) {
      Alert.alert('Erro', e?.response?.data?.detail || 'Falha ao salvar tarefa');
    }
  };

  const deleteTask = async (taskId: string) => {
    const confirmDel = Platform.OS === 'web' ? window.confirm('Excluir esta tarefa e suas sub-tarefas?') : true;
    if (!confirmDel) return;
    try {
      await projectAPI.removeTask(project!.id, taskId);
      await load();
    } catch (e: any) {
      Alert.alert('Erro', e?.response?.data?.detail || 'Falha ao excluir');
    }
  };

  if (loading || !project) {
    return (
      <SafeAreaView style={styles.container}>
        <ActivityIndicator size="large" style={{ marginTop: 60 }} />
      </SafeAreaView>
    );
  }

  const tasks = orderedTasks();
  const overallProgress = project.tasks?.length
    ? Math.round(project.tasks.reduce((a, t) => a + (Number(t.progress_percent) || 0), 0) / project.tasks.length)
    : 0;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} data-testid="edit-project-back">
          <Ionicons name="arrow-back" size={26} color="#000" />
        </TouchableOpacity>
        <Text style={styles.title} numberOfLines={1}>{project.title}</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView contentContainerStyle={{ padding: 16 }}>
        {/* Project meta */}
        <View style={styles.metaCard}>
          <Text style={styles.metaTitle}>OS: {project.os_number}</Text>
          <Text style={styles.metaLine}>Embarcação: {project.embarcacao || '-'}</Text>
          <Text style={styles.metaLine}>Cliente: {project.client || '-'}</Text>
          <Text style={styles.metaLine}>Início: {project.start_date || '-'}  •  Término: {project.end_date || '-'}</Text>

          <View style={styles.progressBg}>
            <View style={[styles.progressBar, { width: `${overallProgress}%` }]} />
          </View>
          <Text style={styles.progressLabel}>{overallProgress}% concluído • {project.tasks?.length || 0} tarefas</Text>

          <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 12 }}>
            <Switch value={!!project.lock_end_date} onValueChange={v => saveProjectMeta({ lock_end_date: v })} data-testid="lock-end-date-switch" />
            <Text style={{ marginLeft: 8, color: '#333' }}>Fixar data final (não recalcular automaticamente)</Text>
          </View>
        </View>

        {/* Tasks list */}
        <View style={styles.tasksHeader}>
          <Text style={styles.sectionTitle}>Cronograma de Tarefas</Text>
          <TouchableOpacity style={styles.addTaskBtn} onPress={() => openNewTask(null)} data-testid="add-root-task-btn">
            <Ionicons name="add" size={18} color="#fff" />
            <Text style={styles.addTaskText}>Fase</Text>
          </TouchableOpacity>
        </View>

        {tasks.length === 0 ? (
          <View style={styles.emptyBox}>
            <Text style={styles.emptyText}>Nenhuma tarefa. Adicione uma fase para começar.</Text>
          </View>
        ) : tasks.map(({ depth, task }) => (
          <View key={task.id} style={[styles.taskRow, depth > 0 && { marginLeft: 20 * depth }]} data-testid={`task-row-${task.id}`}>
            <View style={{ flex: 1 }}>
              <Text style={[styles.taskName, depth === 0 && { fontWeight: '700' }]} numberOfLines={2}>{task.name}</Text>
              <Text style={styles.taskMeta}>
                {task.duration_value} {task.duration_unit} • {task.start_date || '-'} → {task.end_date || '-'}
              </Text>
              <View style={styles.progressBgSm}>
                <View style={[styles.progressBarSm, { width: `${task.progress_percent}%` }]} />
              </View>
              <Text style={styles.taskProgress}>{Number(task.progress_percent).toFixed(0)}%</Text>
            </View>
            <View style={styles.taskActions}>
              <TouchableOpacity onPress={() => openNewTask(task.id)} data-testid={`add-child-${task.id}`}>
                <Ionicons name="add-circle-outline" size={22} color="#1976d2" />
              </TouchableOpacity>
              <TouchableOpacity onPress={() => openEditTask(task)} data-testid={`edit-task-${task.id}`}>
                <Ionicons name="create-outline" size={22} color="#666" />
              </TouchableOpacity>
              <TouchableOpacity onPress={() => deleteTask(task.id)} data-testid={`delete-task-${task.id}`}>
                <Ionicons name="trash-outline" size={22} color="#d32f2f" />
              </TouchableOpacity>
            </View>
          </View>
        ))}
      </ScrollView>

      {/* Task Modal */}
      <Modal visible={showTaskModal} animationType="slide" transparent onRequestClose={() => setShowTaskModal(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalBox}>
            <Text style={styles.modalTitle}>{editingTaskId ? 'Editar Tarefa' : 'Nova Tarefa'}</Text>
            <ScrollView>
              <Text style={styles.label}>Nome *</Text>
              <TextInput style={styles.input} value={taskForm.name} onChangeText={t => setTaskForm(f => ({ ...f, name: t }))} placeholder="Ex: Disassembly the Thruster" data-testid="task-name-input" />

              <Text style={styles.label}>Tarefa pai (opcional)</Text>
              <ScrollView horizontal style={{ maxHeight: 44 }}>
                <TouchableOpacity style={[styles.chip, !taskForm.parent_id && styles.chipSelected]} onPress={() => setTaskForm(f => ({ ...f, parent_id: null }))}>
                  <Text style={[styles.chipText, !taskForm.parent_id && styles.chipTextSelected]}>-- Raiz --</Text>
                </TouchableOpacity>
                {project.tasks.filter(t => t.id !== editingTaskId).map(t => (
                  <TouchableOpacity key={t.id} style={[styles.chip, taskForm.parent_id === t.id && styles.chipSelected]} onPress={() => setTaskForm(f => ({ ...f, parent_id: t.id }))}>
                    <Text style={[styles.chipText, taskForm.parent_id === t.id && styles.chipTextSelected]} numberOfLines={1}>{t.name}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>

              <View style={{ flexDirection: 'row', gap: 12 }}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.label}>Duração</Text>
                  <TextInput style={styles.input} value={taskForm.duration_value} onChangeText={t => setTaskForm(f => ({ ...f, duration_value: t }))} keyboardType="numeric" placeholder="7,75" data-testid="task-duration-input" />
                </View>
                <View style={{ width: 120 }}>
                  <Text style={styles.label}>Unidade</Text>
                  <View style={{ flexDirection: 'row', gap: 6 }}>
                    <TouchableOpacity style={[styles.unitBtn, taskForm.duration_unit === 'dias' && styles.unitBtnSel]} onPress={() => setTaskForm(f => ({ ...f, duration_unit: 'dias' }))}>
                      <Text style={taskForm.duration_unit === 'dias' ? styles.unitTxtSel : styles.unitTxt}>dias</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={[styles.unitBtn, taskForm.duration_unit === 'hrs' && styles.unitBtnSel]} onPress={() => setTaskForm(f => ({ ...f, duration_unit: 'hrs' }))}>
                      <Text style={taskForm.duration_unit === 'hrs' ? styles.unitTxtSel : styles.unitTxt}>hrs</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              </View>

              <Text style={styles.label}>Data Início (YYYY-MM-DD)</Text>
              <TextInput style={styles.input} value={taskForm.start_date} onChangeText={t => setTaskForm(f => ({ ...f, start_date: t }))} placeholder="2026-01-14" data-testid="task-start-input" />

              <Text style={styles.label}>Data Término (YYYY-MM-DD)</Text>
              <TextInput style={styles.input} value={taskForm.end_date} onChangeText={t => setTaskForm(f => ({ ...f, end_date: t }))} placeholder="2026-01-23" data-testid="task-end-input" />

              <Text style={styles.label}>Progresso (%)</Text>
              <TextInput style={styles.input} value={taskForm.progress_percent} onChangeText={t => setTaskForm(f => ({ ...f, progress_percent: t }))} keyboardType="numeric" placeholder="0-100" data-testid="task-progress-input" />

              <Text style={styles.label}>Notas</Text>
              <TextInput style={[styles.input, { height: 60 }]} value={taskForm.notes} onChangeText={t => setTaskForm(f => ({ ...f, notes: t }))} multiline />
            </ScrollView>

            <View style={styles.modalActions}>
              <TouchableOpacity style={[styles.btn, styles.btnGhost]} onPress={() => setShowTaskModal(false)}>
                <Text style={styles.btnGhostText}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[styles.btn, styles.btnPrimary]} onPress={saveTask} data-testid="task-save-btn">
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
  title: { fontSize: 18, fontWeight: '700', color: '#000', flex: 1, marginHorizontal: 12 },
  metaCard: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 16, borderLeftWidth: 4, borderLeftColor: '#6a1b9a' },
  metaTitle: { fontSize: 15, fontWeight: '700', color: '#000' },
  metaLine: { color: '#444', marginTop: 4, fontSize: 13 },
  progressBg: { height: 10, borderRadius: 5, backgroundColor: '#eee', marginTop: 12, overflow: 'hidden' },
  progressBar: { height: '100%', backgroundColor: '#6a1b9a' },
  progressLabel: { fontSize: 12, color: '#666', marginTop: 4 },
  tasksHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: '#000' },
  addTaskBtn: { flexDirection: 'row', backgroundColor: '#6a1b9a', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8, alignItems: 'center', gap: 4 },
  addTaskText: { color: '#fff', fontWeight: '600' },
  taskRow: { backgroundColor: '#fff', borderRadius: 10, padding: 12, marginBottom: 8, flexDirection: 'row', alignItems: 'center', gap: 10 },
  taskName: { fontSize: 14, color: '#000' },
  taskMeta: { fontSize: 11, color: '#666', marginTop: 2 },
  progressBgSm: { height: 6, borderRadius: 3, backgroundColor: '#eee', marginTop: 6, overflow: 'hidden' },
  progressBarSm: { height: '100%', backgroundColor: '#4caf50' },
  taskProgress: { fontSize: 11, color: '#666', marginTop: 2, textAlign: 'right' },
  taskActions: { flexDirection: 'row', gap: 8 },
  emptyBox: { padding: 30, alignItems: 'center' },
  emptyText: { color: '#888' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modalBox: { backgroundColor: '#fff', borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20, maxHeight: '90%' },
  modalTitle: { fontSize: 20, fontWeight: '700', marginBottom: 16 },
  label: { fontSize: 13, color: '#333', marginTop: 12, marginBottom: 6, fontWeight: '600' },
  input: { borderWidth: 1, borderColor: '#ddd', borderRadius: 8, padding: 10, fontSize: 15, backgroundColor: '#fafafa' },
  chip: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 16, backgroundColor: '#eee', marginRight: 8, marginTop: 4, maxWidth: 200 },
  chipSelected: { backgroundColor: '#6a1b9a' },
  chipText: { color: '#333', fontSize: 12 },
  chipTextSelected: { color: '#fff', fontWeight: '600' },
  unitBtn: { flex: 1, padding: 10, borderWidth: 1, borderColor: '#ddd', borderRadius: 8, alignItems: 'center' },
  unitBtnSel: { backgroundColor: '#6a1b9a', borderColor: '#6a1b9a' },
  unitTxt: { color: '#333' },
  unitTxtSel: { color: '#fff', fontWeight: '600' },
  modalActions: { flexDirection: 'row', gap: 12, marginTop: 16 },
  btn: { flex: 1, padding: 14, borderRadius: 10, alignItems: 'center' },
  btnGhost: { backgroundColor: '#f0f0f0' },
  btnGhostText: { color: '#333', fontWeight: '600' },
  btnPrimary: { backgroundColor: '#6a1b9a' },
  btnPrimaryText: { color: '#fff', fontWeight: '700' },
});
