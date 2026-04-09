import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, FlatList, Alert, ActivityIndicator, Platform, Modal } from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { reportAPI, supervisorAPI, sharingAPI } from '../../services/api';
import { downloadAndSharePDF } from '../../utils/pdfHelper';

interface ReportItem {
  id: string;
  report_type: string;
  os_number: string;
  client: string;
  location: string;
  service: string;
  supervisor_name: string;
  supervisor_id: string;
  shared_with: string[];
  status: string;
  created_at: string;
}

export default function ServiceReportsScreen() {
  const router = useRouter();
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [supervisors, setSupervisors] = useState<any[]>([]);
  const [shareModalVisible, setShareModalVisible] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<ReportItem | null>(null);
  const [selectedSupervisors, setSelectedSupervisors] = useState<string[]>([]);
  const [sharing, setSharing] = useState(false);

  useEffect(() => { loadReports(); loadSupervisors(); }, []);

  const loadReports = async () => {
    try {
      const all = await reportAPI.getAll();
      setReports(all.filter((r: ReportItem) => r.report_type === 'service'));
    } catch (error) {
      console.error('Erro ao carregar relatórios:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadSupervisors = async () => {
    try { const data = await supervisorAPI.getAll(); setSupervisors(data); } catch {}
  };

  const handleOpenPDF = async (report: ReportItem) => {
    try {
      const backendUrl = process.env.EXPO_PUBLIC_BACKEND_URL || '';
      const nativeUrl = `${backendUrl}/api/reports/${report.id}/pdf?t=${Date.now()}`;
      await downloadAndSharePDF(() => reportAPI.downloadPDF(report.id), nativeUrl, `relatorio_servico_${report.os_number}.pdf`);
    } catch (error) {
      if (Platform.OS === 'web') window.alert('Erro ao abrir PDF');
      else Alert.alert('Erro', 'Erro ao abrir PDF');
    }
  };

  const handleDownloadPDF = async (report: ReportItem) => {
    try {
      const backendUrl = process.env.EXPO_PUBLIC_BACKEND_URL || '';
      const nativeUrl = `${backendUrl}/api/reports/${report.id}/pdf?t=${Date.now()}`;
      await downloadAndSharePDF(() => reportAPI.downloadPDF(report.id), nativeUrl, `relatorio_servico_${report.os_number}.pdf`);
      if (Platform.OS === 'web') window.alert('PDF baixado com sucesso!');
    } catch (error) {
      if (Platform.OS === 'web') window.alert('Erro ao baixar PDF');
      else Alert.alert('Erro', 'Erro ao baixar PDF');
    }
  };

  const openShareModal = (report: ReportItem) => {
    setSelectedDoc(report);
    setSelectedSupervisors(report.shared_with || []);
    setShareModalVisible(true);
  };

  const toggleSupervisor = (supId: string) => {
    setSelectedSupervisors(prev =>
      prev.includes(supId) ? prev.filter(id => id !== supId) : [...prev, supId]
    );
  };

  const handleSaveSharing = async () => {
    if (!selectedDoc) return;
    setSharing(true);
    try {
      const currentShared = selectedDoc.shared_with || [];
      const toAdd = selectedSupervisors.filter(id => !currentShared.includes(id));
      const toRemove = currentShared.filter(id => !selectedSupervisors.includes(id));

      if (toAdd.length > 0) {
        await sharingAPI.share(selectedDoc.id, 'report', toAdd);
      }
      if (toRemove.length > 0) {
        await sharingAPI.unshare(selectedDoc.id, 'report', toRemove);
      }

      setReports(prev => prev.map(r => r.id === selectedDoc.id ? { ...r, shared_with: selectedSupervisors } : r));
      setShareModalVisible(false);
      if (Platform.OS === 'web') window.alert('Compartilhamento atualizado!');
      else Alert.alert('Sucesso', 'Compartilhamento atualizado!');
    } catch (error) {
      if (Platform.OS === 'web') window.alert('Erro ao compartilhar');
      else Alert.alert('Erro', 'Erro ao compartilhar');
    } finally {
      setSharing(false);
    }
  };

  const formatDate = (dateStr: string) => {
    try { return new Date(dateStr).toLocaleDateString('pt-BR'); } catch { return dateStr; }
  };
  const getStatusLabel = (s: string) => { switch (s) { case 'draft': return 'Rascunho'; case 'completed': return 'Concluído'; case 'finalized': return 'Finalizado'; default: return s; } };
  const getStatusColor = (s: string) => { switch (s) { case 'draft': return '#ff9800'; case 'completed': return '#4caf50'; case 'finalized': return '#1a237e'; default: return '#999'; } };

  const renderReport = ({ item }: { item: ReportItem }) => (
    <View style={styles.card}>
      <View style={styles.topRow}>
        <View style={styles.badge}><Text style={styles.badgeText}>{item.os_number}</Text></View>
        <View style={styles.actions}>
          <TouchableOpacity onPress={() => openShareModal(item)} style={styles.actionBtn} data-testid={`share-btn-${item.id}`}>
            <Ionicons name="share-social-outline" size={20} color={item.shared_with?.length ? '#4caf50' : '#666'} />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => handleOpenPDF(item)} style={styles.actionBtn}>
            <Ionicons name="document-text-outline" size={20} color="#1a237e" />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => handleDownloadPDF(item)} style={styles.actionBtn}>
            <Ionicons name="download-outline" size={20} color="#1a237e" />
          </TouchableOpacity>
        </View>
      </View>
      <View style={styles.cardInfo}>
        <Text style={styles.cardTitle}>{item.client}</Text>
        <Text style={styles.cardSubtitle}>{item.location} - {item.service}</Text>
        <Text style={styles.cardMeta}>{item.supervisor_name}</Text>
        {item.shared_with?.length > 0 && (
          <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 4, gap: 4 }}>
            <Ionicons name="people-outline" size={14} color="#4caf50" />
            <Text style={{ fontSize: 11, color: '#4caf50' }}>Compartilhado com {item.shared_with.length} supervisor(es)</Text>
          </View>
        )}
        <View style={styles.statusRow}>
          <View style={[styles.statusBadge, { backgroundColor: getStatusColor(item.status) + '20' }]}>
            <Text style={[styles.statusText, { color: getStatusColor(item.status) }]}>{getStatusLabel(item.status)}</Text>
          </View>
          <Text style={styles.dateText}>{formatDate(item.created_at)}</Text>
        </View>
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.headerRow}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}><Ionicons name="arrow-back" size={24} color="#1a237e" /></TouchableOpacity>
          <Text style={styles.title}>Relatórios de Serviço</Text>
        </View>
        {loading ? (
          <ActivityIndicator size="large" color="#1a237e" style={{ marginTop: 48 }} />
        ) : reports.length > 0 ? (
          <FlatList data={reports} renderItem={renderReport} keyExtractor={item => item.id} scrollEnabled={false} />
        ) : (
          <View style={styles.empty}><Ionicons name="construct-outline" size={48} color="#ccc" /><Text style={styles.emptyText}>Nenhum relatório de serviço encontrado</Text></View>
        )}
      </ScrollView>

      {/* Share Modal */}
      <Modal visible={shareModalVisible} animationType="slide" transparent onRequestClose={() => setShareModalVisible(false)}>
        <View style={styles.modalOverlay}><View style={styles.modalContent}>
          <Text style={styles.modalTitle}>Compartilhar Documento</Text>
          <Text style={{ fontSize: 14, color: '#666', marginBottom: 16 }}>
            Selecione os supervisores que terão acesso:
          </Text>
          <ScrollView style={{ maxHeight: 300 }}>
            {supervisors.filter(s => s.id !== selectedDoc?.supervisor_id).map(sup => (
              <TouchableOpacity key={sup.id} style={styles.supItem} onPress={() => toggleSupervisor(sup.id)}>
                <Ionicons name={selectedSupervisors.includes(sup.id) ? 'checkbox' : 'square-outline'} size={24} color="#1a237e" />
                <View style={{ marginLeft: 12, flex: 1 }}>
                  <Text style={{ fontSize: 15, fontWeight: '500', color: '#212121' }}>{sup.name}</Text>
                  <Text style={{ fontSize: 13, color: '#666' }}>{sup.email}</Text>
                </View>
              </TouchableOpacity>
            ))}
            {supervisors.filter(s => s.id !== selectedDoc?.supervisor_id).length === 0 && (
              <Text style={{ padding: 16, textAlign: 'center', color: '#999' }}>Nenhum outro supervisor encontrado</Text>
            )}
          </ScrollView>
          <View style={styles.modalBtns}>
            <TouchableOpacity style={[styles.modalBtn, styles.cancelBtn]} onPress={() => setShareModalVisible(false)}>
              <Text style={styles.cancelText}>Cancelar</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[styles.modalBtn, styles.confirmBtn]} onPress={handleSaveSharing} disabled={sharing}>
              {sharing ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.confirmText}>Salvar</Text>}
            </TouchableOpacity>
          </View>
        </View></View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  scrollContent: { padding: 16 },
  headerRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 20, gap: 12 },
  backBtn: { padding: 8 },
  title: { fontSize: 22, fontWeight: 'bold', color: '#1a237e' },
  card: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.1, shadowRadius: 2, elevation: 2 },
  topRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 },
  badge: { backgroundColor: '#e3f2fd', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8 },
  badgeText: { color: '#1a237e', fontWeight: '600', fontSize: 12 },
  actions: { flexDirection: 'row', gap: 4 },
  actionBtn: { padding: 8 },
  cardInfo: { paddingLeft: 2 },
  cardTitle: { fontSize: 16, fontWeight: '600', color: '#212121' },
  cardSubtitle: { fontSize: 14, color: '#666', marginTop: 4 },
  cardMeta: { fontSize: 13, color: '#444', marginTop: 2, fontStyle: 'italic' },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 6 },
  statusBadge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4 },
  statusText: { fontSize: 11, fontWeight: '600' },
  dateText: { fontSize: 12, color: '#999' },
  empty: { alignItems: 'center', paddingVertical: 48 },
  emptyText: { fontSize: 14, color: '#999', marginTop: 12 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', padding: 16 },
  modalContent: { backgroundColor: '#fff', borderRadius: 16, padding: 24, maxHeight: '80%' },
  modalTitle: { fontSize: 20, fontWeight: '600', color: '#1a237e', marginBottom: 8 },
  supItem: { flexDirection: 'row', alignItems: 'center', padding: 12, borderBottomWidth: 1, borderBottomColor: '#f0f0f0' },
  modalBtns: { flexDirection: 'row', gap: 12, marginTop: 16 },
  modalBtn: { flex: 1, height: 48, borderRadius: 8, justifyContent: 'center', alignItems: 'center' },
  cancelBtn: { backgroundColor: '#f5f5f5' },
  cancelText: { color: '#666', fontSize: 16, fontWeight: '600' },
  confirmBtn: { backgroundColor: '#1a237e' },
  confirmText: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
