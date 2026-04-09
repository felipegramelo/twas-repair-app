import React, { useState, useEffect } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, FlatList, ActivityIndicator, Alert, Platform, Modal, ScrollView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { timesheetAPI, supervisorAPI, sharingAPI } from '../../services/api';
import { Timesheet } from '../../types';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as FileSystem from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';

function getDateRangeText(entries: Timesheet['entries']): string {
  if (!entries || entries.length === 0) return '';
  const dates = entries
    .map(e => e.date)
    .filter(Boolean)
    .map(d => {
      const [day, month, year] = d.split('/');
      return { raw: d, sortKey: `${year}-${month}-${day}` };
    })
    .sort((a, b) => a.sortKey.localeCompare(b.sortKey));
  if (dates.length === 0) return '';
  const uniqueDates = [...new Set(dates.map(d => d.raw))];
  const first = uniqueDates[0];
  const last = uniqueDates[uniqueDates.length - 1];
  if (first === last) return `Timesheet do dia ${first}`;
  return `Timesheet do dia ${first} ate ${last}`;
}

export default function AdminTimesheetsScreen() {
  const router = useRouter();
  const [timesheets, setTimesheets] = useState<Timesheet[]>([]);
  const [loading, setLoading] = useState(true);
  const [supervisors, setSupervisors] = useState<any[]>([]);
  const [shareModalVisible, setShareModalVisible] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<Timesheet | null>(null);
  const [selectedSupervisors, setSelectedSupervisors] = useState<string[]>([]);
  const [sharing, setSharing] = useState(false);

  useEffect(() => { loadTimesheets(); loadSupervisors(); }, []);

  const loadTimesheets = async () => {
    try {
      const data = await timesheetAPI.getAll();
      setTimesheets(data);
    } catch (error: any) {
      if (Platform.OS === 'web') window.alert('Erro ao carregar timesheets');
      else Alert.alert('Erro', 'Erro ao carregar timesheets');
    } finally {
      setLoading(false);
    }
  };

  const loadSupervisors = async () => {
    try { const data = await supervisorAPI.getAll(); setSupervisors(data); } catch {}
  };

  const handleOpenPDF = async (timesheet: Timesheet) => {
    try {
      if (Platform.OS === 'web') {
        const blob = await timesheetAPI.downloadPDF(timesheet.id);
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank');
      } else {
        const token = await AsyncStorage.getItem('token');
        const baseURL = process.env.EXPO_PUBLIC_BACKEND_URL + '/api';
        const fileUri = `${FileSystem.cacheDirectory}timesheet_${timesheet.id}_${Date.now()}.pdf`;
        const result = await FileSystem.downloadAsync(
          `${baseURL}/timesheets/${timesheet.id}/pdf?t=${Date.now()}`,
          fileUri,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        if (result.status === 200) {
          const isAvailable = await Sharing.isAvailableAsync();
          if (isAvailable) {
            await Sharing.shareAsync(result.uri, { mimeType: 'application/pdf', UTI: 'com.adobe.pdf' });
          } else {
            Alert.alert('Sucesso', 'PDF salvo em: ' + result.uri);
          }
        } else {
          Alert.alert('Erro', 'Erro ao gerar PDF. Status: ' + result.status);
        }
      }
    } catch (error: any) {
      if (Platform.OS === 'web') window.alert('Erro ao abrir PDF');
      else Alert.alert('Erro', 'Erro ao abrir PDF: ' + (error.message || ''));
    }
  };

  const handleDownloadPDF = async (timesheet: Timesheet) => {
    try {
      if (Platform.OS === 'web') {
        const blob = await timesheetAPI.downloadPDF(timesheet.id);
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `timesheet_${timesheet.os_number}_${timesheet.client.replace(/[^a-zA-Z0-9]/g, '_')}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        window.alert('PDF baixado com sucesso!');
      } else {
        const token = await AsyncStorage.getItem('token');
        const baseURL = process.env.EXPO_PUBLIC_BACKEND_URL + '/api';
        const fileName = `timesheet_${timesheet.os_number || 'ts'}_${Date.now()}.pdf`;
        const fileUri = `${FileSystem.documentDirectory}${fileName}`;
        const result = await FileSystem.downloadAsync(
          `${baseURL}/timesheets/${timesheet.id}/pdf?t=${Date.now()}`,
          fileUri,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        if (result.status === 200) {
          const isAvailable = await Sharing.isAvailableAsync();
          if (isAvailable) {
            await Sharing.shareAsync(result.uri, { mimeType: 'application/pdf', UTI: 'com.adobe.pdf', dialogTitle: 'Salvar PDF' });
          } else {
            Alert.alert('Sucesso', 'PDF salvo com sucesso!');
          }
        } else {
          Alert.alert('Erro', 'Erro ao baixar PDF. Status: ' + result.status);
        }
      }
    } catch (error: any) {
      if (Platform.OS === 'web') window.alert('Erro ao baixar PDF');
      else Alert.alert('Erro', 'Erro ao baixar PDF: ' + (error.message || ''));
    }
  };

  const handleDelete = (timesheet: Timesheet) => {
    if (Platform.OS === 'web') {
      if (window.confirm(`Excluir timesheet ${timesheet.os_number} - ${timesheet.client}?`)) {
        deleteTimesheet(timesheet.id);
      }
    } else {
      Alert.alert(
        'Confirmar Exclusao',
        `Excluir timesheet ${timesheet.os_number} - ${timesheet.client}?`,
        [
          { text: 'Cancelar', style: 'cancel' },
          { text: 'Excluir', style: 'destructive', onPress: () => deleteTimesheet(timesheet.id) },
        ]
      );
    }
  };

  const deleteTimesheet = async (id: string) => {
    try {
      await timesheetAPI.delete(id);
      setTimesheets(prev => prev.filter(t => t.id !== id));
      if (Platform.OS === 'web') window.alert('Timesheet excluido!');
      else Alert.alert('Sucesso', 'Timesheet excluido com sucesso!');
    } catch (error: any) {
      if (Platform.OS === 'web') window.alert('Erro ao excluir');
      else Alert.alert('Erro', 'Erro ao excluir timesheet');
    }
  };

  const openShareModal = (ts: Timesheet) => {
    setSelectedDoc(ts);
    setSelectedSupervisors(ts.shared_with || []);
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
        await sharingAPI.share(selectedDoc.id, 'timesheet', toAdd);
      }
      if (toRemove.length > 0) {
        await sharingAPI.unshare(selectedDoc.id, 'timesheet', toRemove);
      }

      setTimesheets(prev => prev.map(t => t.id === selectedDoc.id ? { ...t, shared_with: [...selectedSupervisors] } : t));
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

  const renderTimesheet = ({ item }: { item: Timesheet }) => (
    <View style={styles.card} data-testid={`timesheet-card-${item.id}`}>
      <View style={styles.topRow}>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{item.os_number}</Text>
        </View>
        <View style={styles.actions}>
          <TouchableOpacity onPress={() => openShareModal(item)} style={styles.actionButton} data-testid={`share-ts-btn-${item.id}`}>
            <Ionicons name="share-social-outline" size={22} color={(item.shared_with?.length || 0) > 0 ? '#4caf50' : '#666'} />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => handleOpenPDF(item)} style={styles.actionButton} data-testid={`open-pdf-btn-${item.id}`}>
            <Ionicons name="document-text-outline" size={22} color="#1a237e" />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => handleDownloadPDF(item)} style={styles.actionButton} data-testid={`download-pdf-btn-${item.id}`}>
            <Ionicons name="download-outline" size={22} color="#1a237e" />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => handleDelete(item)} style={styles.actionButton} data-testid={`delete-btn-${item.id}`}>
            <Ionicons name="trash-outline" size={22} color="#d32f2f" />
          </TouchableOpacity>
        </View>
      </View>
      <View style={styles.cardInfo}>
        <Text style={styles.cardTitle}>{item.client}</Text>
        <Text style={styles.cardSubtitle}>{item.location}</Text>
        <Text style={styles.cardService} numberOfLines={1} data-testid={`timesheet-service-${item.id}`}>{item.service}</Text>
        <Text style={styles.cardMeta}>Supervisor: {item.supervisor_name}</Text>
        <Text style={styles.cardMeta}>{item.entries.length} entrada(s)</Text>
        {item.entries.length > 0 && (
          <Text style={styles.dateRange} data-testid={`timesheet-date-range-${item.id}`}>{getDateRangeText(item.entries)}</Text>
        )}
        {(item.shared_with?.length || 0) > 0 && (
          <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 4 }}>
            <Ionicons name="people-outline" size={14} color="#4caf50" />
            <Text style={{ fontSize: 11, color: '#4caf50', marginLeft: 4 }}>Compartilhado com {item.shared_with!.length} supervisor(es)</Text>
          </View>
        )}
      </View>
    </View>
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#1a237e" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#1a237e" />
        </TouchableOpacity>
        <Text style={styles.title}>Todos os Timesheets</Text>
        <View style={{ width: 40 }} />
      </View>

      <FlatList
        data={timesheets}
        renderItem={renderTimesheet}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Ionicons name="time-outline" size={64} color="#ccc" />
            <Text style={styles.emptyText}>Nenhum timesheet criado</Text>
          </View>
        }
      />

      {/* Share Modal */}
      <Modal visible={shareModalVisible} animationType="slide" transparent onRequestClose={() => setShareModalVisible(false)}>
        <View style={styles.modalOverlay}><View style={styles.modalContent}>
          <Text style={styles.modalTitle}>Compartilhar Timesheet</Text>
          <Text style={{ fontSize: 14, color: '#666', marginBottom: 16 }}>
            Selecione os supervisores que terao acesso:
          </Text>
          <ScrollView style={{ maxHeight: 300 }}>
            {supervisors.filter(s => s.id !== selectedDoc?.supervisor_id).map(sup => (
              <TouchableOpacity key={sup.id} style={styles.supItem} onPress={() => toggleSupervisor(sup.id)} data-testid={`share-ts-sup-${sup.id}`}>
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
            <TouchableOpacity style={[styles.modalBtn, styles.cancelMBtn]} onPress={() => setShareModalVisible(false)} data-testid="share-ts-cancel-btn">
              <Text style={styles.cancelMText}>Cancelar</Text>
            </TouchableOpacity>
            <TouchableOpacity style={[styles.modalBtn, styles.confirmMBtn]} onPress={handleSaveSharing} disabled={sharing} data-testid="share-ts-save-btn">
              {sharing ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.confirmMText}>Salvar</Text>}
            </TouchableOpacity>
          </View>
        </View></View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 12, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#e0e0e0' },
  backButton: { padding: 8 },
  title: { fontSize: 20, fontWeight: '600', color: '#1a237e' },
  listContent: { padding: 16 },
  card: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.1, shadowRadius: 2, elevation: 2 },
  topRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 },
  badge: { backgroundColor: '#e3f2fd', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8 },
  badgeText: { color: '#1a237e', fontWeight: '600', fontSize: 12 },
  cardInfo: { paddingLeft: 2 },
  cardTitle: { fontSize: 16, fontWeight: '600', color: '#212121' },
  cardSubtitle: { fontSize: 14, color: '#666', marginTop: 4 },
  cardService: { fontSize: 13, color: '#444', marginTop: 2, fontStyle: 'italic' },
  cardMeta: { fontSize: 12, color: '#999', marginTop: 4 },
  dateRange: { fontSize: 12, color: '#1a237e', marginTop: 4, fontWeight: '500' },
  actions: { flexDirection: 'row', gap: 4 },
  actionButton: { padding: 8 },
  emptyContainer: { alignItems: 'center', justifyContent: 'center', paddingVertical: 64 },
  emptyText: { fontSize: 16, color: '#999', marginTop: 16 },
  // Share Modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', padding: 16 },
  modalContent: { backgroundColor: '#fff', borderRadius: 16, padding: 24, maxHeight: '80%' },
  modalTitle: { fontSize: 20, fontWeight: '600', color: '#1a237e', marginBottom: 8 },
  supItem: { flexDirection: 'row', alignItems: 'center', padding: 12, borderBottomWidth: 1, borderBottomColor: '#f0f0f0' },
  modalBtns: { flexDirection: 'row', gap: 12, marginTop: 16 },
  modalBtn: { flex: 1, height: 48, borderRadius: 8, justifyContent: 'center', alignItems: 'center' },
  cancelMBtn: { backgroundColor: '#f5f5f5' },
  cancelMText: { color: '#666', fontSize: 16, fontWeight: '600' },
  confirmMBtn: { backgroundColor: '#1a237e' },
  confirmMText: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
