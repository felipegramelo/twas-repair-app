import React, { useEffect, useState, useCallback } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, TextInput, Alert, ActivityIndicator, Modal, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { projectAPI, serviceOrderAPI, Project } from '../../services/api';
import { ServiceOrder } from '../types';
import { downloadAndSharePDF } from '../../utils/pdfHelper';

const notify = (title: string, message: string) => {
  if (Platform.OS === 'web') {
    // eslint-disable-next-line no-alert
    window.alert(`${title}\n\n${message}`);
  } else {
    Alert.alert(title, message);
  }
};

export default function AdminProjectsScreen() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [projects, setProjects] = useState<Project[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [serviceOrders, setServiceOrders] = useState<ServiceOrder[]>([]);
  const [form, setForm] = useState({
    os_number: '',
    title: '',
    embarcacao: '',
    client: '',
    start_date: '',
    end_date: '',
    description: '',
  });

  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [list, sos] = await Promise.all([projectAPI.getAll(), serviceOrderAPI.getAll()]);
      setProjects(list);
      setServiceOrders(sos as any);
    } catch (e: any) {
      notify('Erro', e?.response?.data?.detail || 'Falha ao carregar projetos');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const pickOS = (osNumber: string) => {
    const so: any = serviceOrders.find((s: any) => s.os_number === osNumber);
    setForm(f => ({
      ...f,
      os_number: osNumber,
      embarcacao: so?.embarcacao || '',
      client: so?.client || '',
      title: f.title || `Projeto - ${so?.service || osNumber}`,
    }));
  };

  const create = async () => {
    if (!form.os_number.trim()) {
      notify('Erro', 'Digite ou selecione uma Ordem de Serviço');
      return;
    }
    setCreating(true);
    try {
      const payload = {
        os_number: form.os_number.trim(),
        title: form.title.trim() || `Projeto - OS ${form.os_number.trim()}`,
        embarcacao: form.embarcacao || '',
        client: form.client || '',
        start_date: form.start_date || null,
        end_date: form.end_date || null,
        description: form.description || '',
        tasks: [],
      };
      const p = await projectAPI.create(payload as any);
      setShowCreate(false);
      setForm({ os_number: '', title: '', embarcacao: '', client: '', start_date: '', end_date: '', description: '' });
      // give the modal a tick to close before navigating
      setTimeout(() => {
        router.push(`/admin/edit-project?id=${p.id}`);
      }, 100);
    } catch (e: any) {
      const detail = e?.response?.data?.detail || e?.message || 'Falha ao criar projeto';
      notify('Erro', typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setCreating(false);
    }
  };

  const remove = async (id: string) => {
    const ok = Platform.OS === 'web' ? window.confirm('Excluir este projeto?') : true;
    if (!ok) return;
    try {
      await projectAPI.remove(id);
      await load();
    } catch (e: any) {
      notify('Erro', e?.response?.data?.detail || 'Falha ao excluir');
    }
  };

  const overallProgress = (p: Project): number => {
    if (!p.tasks?.length) return 0;
    const s = p.tasks.reduce((a, t) => a + (Number(t.progress_percent) || 0), 0);
    return Math.round(s / p.tasks.length);
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} data-testid="admin-projects-back">
          <Ionicons name="arrow-back" size={26} color="#000" />
        </TouchableOpacity>
        <Text style={styles.title}>Projetos</Text>
        <TouchableOpacity onPress={() => setShowCreate(true)} data-testid="admin-projects-new-btn">
          <Ionicons name="add-circle" size={30} color="#6a1b9a" />
        </TouchableOpacity>
      </View>

      {loading ? (
        <ActivityIndicator size="large" style={{ marginTop: 40 }} />
      ) : (
        <ScrollView contentContainerStyle={styles.scrollContent}>
          {projects.length === 0 ? (
            <View style={styles.emptyBox}>
              <Ionicons name="folder-open-outline" size={64} color="#bbb" />
              <Text style={styles.emptyText}>Nenhum projeto cadastrado</Text>
              <Text style={styles.emptyHint}>Clique no + acima para criar</Text>
            </View>
          ) : projects.map(p => (
            <View key={p.id} style={styles.card} data-testid={`admin-project-card-${p.id}`}>
              <View style={{ flex: 1 }}>
                <Text style={styles.cardTitle}>{p.title}</Text>
                <Text style={styles.cardSubtitle}>OS: {p.os_number} • {p.embarcacao || '-'}</Text>
                <View style={styles.progressBg}>
                  <View style={[styles.progressBar, { width: `${overallProgress(p)}%` }]} />
                </View>
                <Text style={styles.progressLabel}>{overallProgress(p)}% concluído • {p.tasks?.length || 0} tarefas</Text>
              </View>
              <View style={styles.cardActions}>
                <TouchableOpacity onPress={() => router.push(`/admin/edit-project?id=${p.id}`)} data-testid={`admin-project-edit-${p.id}`}>
                  <Ionicons name="create-outline" size={22} color="#1976d2" />
                </TouchableOpacity>
                <TouchableOpacity onPress={() => downloadAndSharePDF(projectAPI.pdfUrl(p.id, false), `${p.os_number} - ${p.title} - PROJETO.pdf`, true)} data-testid={`admin-project-view-${p.id}`}>
                  <Ionicons name="eye-outline" size={22} color="#388e3c" />
                </TouchableOpacity>
                <TouchableOpacity onPress={() => downloadAndSharePDF(projectAPI.pdfUrl(p.id, true), `${p.os_number} - ${p.title} - PROJETO.pdf`, false)} data-testid={`admin-project-download-${p.id}`}>
                  <Ionicons name="download-outline" size={22} color="#f57c00" />
                </TouchableOpacity>
                <TouchableOpacity onPress={() => remove(p.id)} data-testid={`admin-project-delete-${p.id}`}>
                  <Ionicons name="trash-outline" size={22} color="#d32f2f" />
                </TouchableOpacity>
              </View>
            </View>
          ))}
        </ScrollView>
      )}

      <Modal visible={showCreate} animationType="slide" transparent onRequestClose={() => setShowCreate(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalBox}>
            <Text style={styles.modalTitle}>Novo Projeto</Text>
            <ScrollView>
              <Text style={styles.label}>Ordem de Serviço *</Text>
              <TextInput
                style={styles.input}
                value={form.os_number}
                onChangeText={t => setForm(f => ({ ...f, os_number: t.trim() }))}
                placeholder="Digite ou selecione abaixo (ex: 2603-25)"
                autoCapitalize="characters"
                data-testid="project-os-input"
              />
              {serviceOrders.length > 0 && (
                <>
                  <Text style={styles.hint}>Ou selecione uma existente ({serviceOrders.length} disponíveis):</Text>
                  <ScrollView horizontal showsHorizontalScrollIndicator style={{ maxHeight: 52, marginTop: 4 }}>
                    {serviceOrders.map((so: any) => (
                      <TouchableOpacity
                        key={so.id || so.os_number}
                        style={[styles.chip, form.os_number === so.os_number && styles.chipSelected]}
                        onPress={() => pickOS(so.os_number)}
                        data-testid={`os-chip-${so.os_number}`}
                      >
                        <Text style={[styles.chipText, form.os_number === so.os_number && styles.chipTextSelected]}>{so.os_number}</Text>
                      </TouchableOpacity>
                    ))}
                  </ScrollView>
                </>
              )}
              {serviceOrders.length === 0 && (
                <Text style={styles.hint}>Nenhuma O.S. cadastrada. Digite o número acima manualmente.</Text>
              )}

              <Text style={styles.label}>Título (opcional)</Text>
              <TextInput style={styles.input} value={form.title} onChangeText={t => setForm(f => ({ ...f, title: t }))} placeholder="Ex: Amaralina Star Thruster Overhaul SN 3826" data-testid="project-title-input" />

              <Text style={styles.label}>Embarcação</Text>
              <TextInput style={styles.input} value={form.embarcacao} onChangeText={t => setForm(f => ({ ...f, embarcacao: t }))} />

              <Text style={styles.label}>Cliente</Text>
              <TextInput style={styles.input} value={form.client} onChangeText={t => setForm(f => ({ ...f, client: t }))} />

              <Text style={styles.label}>Data Início (YYYY-MM-DD)</Text>
              <TextInput style={styles.input} value={form.start_date} onChangeText={t => setForm(f => ({ ...f, start_date: t }))} placeholder="2026-01-14" />

              <Text style={styles.label}>Data Término (YYYY-MM-DD)</Text>
              <TextInput style={styles.input} value={form.end_date} onChangeText={t => setForm(f => ({ ...f, end_date: t }))} placeholder="2026-01-29" />

              <Text style={styles.label}>Descrição</Text>
              <TextInput style={[styles.input, { height: 60 }]} value={form.description} onChangeText={t => setForm(f => ({ ...f, description: t }))} multiline />
            </ScrollView>
            <View style={styles.modalActions}>
              <TouchableOpacity style={[styles.btn, styles.btnGhost]} onPress={() => setShowCreate(false)} data-testid="project-cancel-btn">
                <Text style={styles.btnGhostText}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[styles.btn, styles.btnPrimary, creating && { opacity: 0.6 }]} onPress={create} disabled={creating} data-testid="project-create-btn">
                {creating ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.btnPrimaryText}>Criar e adicionar tarefas</Text>
                )}
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
  scrollContent: { padding: 16, gap: 12 },
  card: { backgroundColor: '#fff', borderRadius: 12, padding: 16, flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.06, shadowRadius: 3, elevation: 1 },
  cardTitle: { fontSize: 16, fontWeight: '600', color: '#000' },
  cardSubtitle: { fontSize: 13, color: '#666', marginTop: 2 },
  progressBg: { height: 8, borderRadius: 4, backgroundColor: '#eee', marginTop: 8, overflow: 'hidden' },
  progressBar: { height: '100%', backgroundColor: '#6a1b9a' },
  progressLabel: { fontSize: 12, color: '#666', marginTop: 4 },
  cardActions: { flexDirection: 'row', gap: 10 },
  emptyBox: { alignItems: 'center', padding: 40 },
  emptyText: { color: '#888', fontSize: 16, marginTop: 12 },
  emptyHint: { color: '#aaa', fontSize: 13, marginTop: 4 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modalBox: { backgroundColor: '#fff', borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20, maxHeight: '90%' },
  modalTitle: { fontSize: 20, fontWeight: '700', marginBottom: 16 },
  label: { fontSize: 13, color: '#333', marginTop: 12, marginBottom: 6, fontWeight: '600' },
  input: { borderWidth: 1, borderColor: '#ddd', borderRadius: 8, padding: 10, fontSize: 15, backgroundColor: '#fafafa' },
  chip: { paddingHorizontal: 14, paddingVertical: 10, borderRadius: 20, backgroundColor: '#eee', marginRight: 8, marginTop: 4, borderWidth: 1, borderColor: '#ccc' },
  chipSelected: { backgroundColor: '#6a1b9a', borderColor: '#6a1b9a' },
  chipText: { color: '#333', fontSize: 13, fontWeight: '600' },
  chipTextSelected: { color: '#fff', fontWeight: '700' },
  hint: { fontSize: 12, color: '#666', marginTop: 8, fontStyle: 'italic' },
  modalActions: { flexDirection: 'row', gap: 12, marginTop: 20 },
  btn: { flex: 1, padding: 14, borderRadius: 10, alignItems: 'center' },
  btnGhost: { backgroundColor: '#f0f0f0' },
  btnGhostText: { color: '#333', fontWeight: '600' },
  btnPrimary: { backgroundColor: '#6a1b9a' },
  btnPrimaryText: { color: '#fff', fontWeight: '700' },
});
