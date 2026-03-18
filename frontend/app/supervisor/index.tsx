import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, FlatList, Alert, ActivityIndicator, Platform, Modal } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { timesheetAPI } from '../../services/api';
import { reportsAPI } from '../../services/reportsApi';
import { Timesheet, Report } from '../../types';
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
  return `Timesheet do dia ${first} até ${last}`;
}

type UnifiedItem = 
  | { kind: 'timesheet'; data: Timesheet }
  | { kind: 'report'; data: Report };

export default function SupervisorDashboard() {
  const { user, signOut, ensureReportAuth } = useAuth();
  const router = useRouter();
  const [timesheets, setTimesheets] = useState<Timesheet[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const tsData = await timesheetAPI.getAll();
      setTimesheets(tsData);
    } catch (error) {
      console.error('Erro ao carregar timesheets:', error);
    }
    try {
      await ensureReportAuth();
      const allReports = await reportsAPI.getAll();
      setReports(allReports);
    } catch (error) {
      console.error('Erro ao carregar relatórios:', error);
    }
    setLoading(false);
  };

  const handleLogout = async () => {
    await signOut();
    router.replace('/');
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
      console.error('Erro ao abrir PDF:', error);
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
      console.error('Erro ao baixar PDF:', error);
      if (Platform.OS === 'web') window.alert('Erro ao baixar PDF');
      else Alert.alert('Erro', 'Erro ao baixar PDF: ' + (error.message || ''));
    }
  };

  const handleOpenReportPDF = async (report: Report) => {
    try {
      if (Platform.OS === 'web') {
        const blob = await reportsAPI.downloadPDF(report.id);
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank');
      } else {
        Alert.alert('Info', 'PDF disponível apenas na versão web por enquanto.');
      }
    } catch (error: any) {
      console.error('Erro ao abrir PDF do relatório:', error);
      if (Platform.OS === 'web') window.alert('Erro ao abrir PDF do relatório');
      else Alert.alert('Erro', 'Erro ao abrir PDF');
    }
  };

  const handleDownloadReportPDF = async (report: Report) => {
    try {
      if (Platform.OS === 'web') {
        const blob = await reportsAPI.downloadPDF(report.id);
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `relatorio_${report.service_order_number}_${report.client.replace(/[^a-zA-Z0-9]/g, '_')}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        window.alert('PDF baixado com sucesso!');
      } else {
        Alert.alert('Info', 'Download disponível apenas na versão web por enquanto.');
      }
    } catch (error: any) {
      console.error('Erro ao baixar PDF do relatório:', error);
      if (Platform.OS === 'web') window.alert('Erro ao baixar PDF do relatório');
      else Alert.alert('Erro', 'Erro ao baixar PDF');
    }
  };

  const handleDeleteTimesheet = (timesheet: Timesheet) => {
    if (Platform.OS === 'web') {
      if (window.confirm(`Excluir timesheet ${timesheet.os_number} - ${timesheet.client}?`)) {
        deleteTimesheet(timesheet.id);
      }
    } else {
      Alert.alert('Confirmar Exclusão', `Excluir timesheet ${timesheet.os_number} - ${timesheet.client}?`, [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Excluir', style: 'destructive', onPress: () => deleteTimesheet(timesheet.id) },
      ]);
    }
  };

  const deleteTimesheet = async (id: string) => {
    try {
      await timesheetAPI.delete(id);
      setTimesheets(prev => prev.filter(t => t.id !== id));
      Alert.alert('Sucesso', 'Timesheet excluído com sucesso!');
    } catch (error) {
      Alert.alert('Erro', 'Erro ao excluir timesheet');
    }
  };

  const handleDeleteReport = (report: Report) => {
    const label = report.report_type === 'service' ? 'relatório de serviço' : 'relatório diário';
    if (Platform.OS === 'web') {
      if (window.confirm(`Excluir ${label} ${report.service_order_number} - ${report.client}?`)) {
        deleteReport(report);
      }
    } else {
      Alert.alert('Confirmar Exclusão', `Excluir ${label} ${report.service_order_number} - ${report.client}?`, [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Excluir', style: 'destructive', onPress: () => deleteReport(report) },
      ]);
    }
  };

  const deleteReport = async (report: Report) => {
    try {
      await reportsAPI.delete(report.id);
      setReports(prev => prev.filter(r => r.id !== report.id));
      Alert.alert('Sucesso', 'Relatório excluído com sucesso!');
    } catch (error) {
      Alert.alert('Erro', 'Erro ao excluir relatório');
    }
  };

  const handleCreateOption = (option: 'timesheet' | 'service_report' | 'daily_report') => {
    setShowCreateModal(false);
    if (option === 'timesheet') {
      router.push('/supervisor/create-timesheet');
    } else {
      router.push(`/supervisor/create-report?type=${option === 'service_report' ? 'service' : 'daily'}`);
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('pt-BR');
    } catch { return dateStr; }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'draft': return 'Rascunho';
      case 'completed': return 'Concluído';
      case 'approved': return 'Aprovado';
      default: return status;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'draft': return '#ff9800';
      case 'completed': return '#4caf50';
      case 'approved': return '#2196f3';
      default: return '#999';
    }
  };

  const getReportTypeLabel = (type: string) => {
    return type === 'service' ? 'Rel. Serviço' : 'Rel. Diário';
  };

  const getReportTypeColor = (type: string) => {
    return type === 'service' ? '#1565c0' : '#2e7d32';
  };

  // Build unified list
  const unifiedItems: UnifiedItem[] = [
    ...timesheets.map(t => ({ kind: 'timesheet' as const, data: t })),
    ...reports.map(r => ({ kind: 'report' as const, data: r })),
  ];

  const renderTimesheetCard = (item: Timesheet) => (
    <TouchableOpacity
      style={styles.card}
      onPress={() => router.push(`/supervisor/edit-timesheet?id=${item.id}`)}
      activeOpacity={0.7}
    >
      <View style={styles.topRow}>
        <View style={styles.badgeRow}>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{item.os_number}</Text>
          </View>
          <View style={[styles.typeBadge, { backgroundColor: '#e8eaf6' }]}>
            <Ionicons name="time-outline" size={12} color="#1a237e" />
            <Text style={[styles.typeBadgeText, { color: '#1a237e' }]}>Timesheet</Text>
          </View>
        </View>
        <View style={styles.actions}>
          <TouchableOpacity onPress={() => handleOpenPDF(item)} style={styles.actionBtn}>
            <Ionicons name="document-text-outline" size={20} color="#1a237e" />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => router.push(`/supervisor/edit-timesheet?id=${item.id}`)} style={styles.actionBtn}>
            <Ionicons name="pencil" size={20} color="#1a237e" />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => handleDownloadPDF(item)} style={styles.actionBtn}>
            <Ionicons name="download-outline" size={20} color="#1a237e" />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => handleDeleteTimesheet(item)} style={styles.actionBtn}>
            <Ionicons name="trash-outline" size={20} color="#d32f2f" />
          </TouchableOpacity>
        </View>
      </View>
      <View style={styles.cardInfo}>
        <Text style={styles.cardTitle}>{item.client}</Text>
        <Text style={styles.cardSubtitle}>{item.location}</Text>
        <Text style={styles.cardService} numberOfLines={1}>{item.service}</Text>
        <Text style={styles.cardMeta}>{item.entries.length} entrada(s)</Text>
        {item.entries.length > 0 && (
          <Text style={styles.dateRange}>{getDateRangeText(item.entries)}</Text>
        )}
      </View>
    </TouchableOpacity>
  );

  const renderReportCard = (item: Report) => (
    <View style={styles.card}>
      <View style={styles.topRow}>
        <View style={styles.badgeRow}>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{item.service_order_number}</Text>
          </View>
          <View style={[styles.typeBadge, { backgroundColor: getReportTypeColor(item.report_type) + '15' }]}>
            <Ionicons name={item.report_type === 'service' ? 'construct-outline' : 'calendar-outline'} size={12} color={getReportTypeColor(item.report_type)} />
            <Text style={[styles.typeBadgeText, { color: getReportTypeColor(item.report_type) }]}>{getReportTypeLabel(item.report_type)}</Text>
          </View>
        </View>
        <View style={styles.actions}>
          <TouchableOpacity onPress={() => handleOpenReportPDF(item)} style={styles.actionBtn}>
            <Ionicons name="document-text-outline" size={20} color="#1a237e" />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => handleDownloadReportPDF(item)} style={styles.actionBtn}>
            <Ionicons name="download-outline" size={20} color="#1a237e" />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => handleDeleteReport(item)} style={styles.actionBtn}>
            <Ionicons name="trash-outline" size={20} color="#d32f2f" />
          </TouchableOpacity>
        </View>
      </View>
      <View style={styles.cardInfo}>
        <Text style={styles.cardTitle}>{item.client}</Text>
        <Text style={styles.cardSubtitle}>{item.vessel} - {item.equipment}</Text>
        <Text style={styles.cardService} numberOfLines={1}>{item.supervisor_name}</Text>
        <View style={styles.statusRow}>
          <View style={[styles.statusBadge, { backgroundColor: getStatusColor(item.status) + '20' }]}>
            <Text style={[styles.statusText, { color: getStatusColor(item.status) }]}>{getStatusLabel(item.status)}</Text>
          </View>
          <Text style={styles.cardMeta}>{formatDate(item.created_at)}</Text>
        </View>
      </View>
    </View>
  );

  const renderItem = ({ item }: { item: UnifiedItem }) => {
    if (item.kind === 'timesheet') return renderTimesheetCard(item.data);
    return renderReportCard(item.data);
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <View>
            <Text style={styles.title}>TWAS REPAIR</Text>
            <Text style={styles.subtitle}>Bem-vindo, {user?.name}</Text>
          </View>
          <TouchableOpacity onPress={handleLogout} style={styles.logoutButton}>
            <Ionicons name="log-out-outline" size={24} color="#d32f2f" />
          </TouchableOpacity>
        </View>

        {/* Create Button */}
        <TouchableOpacity
          style={styles.createButton}
          onPress={() => setShowCreateModal(true)}
        >
          <Ionicons name="add-circle" size={24} color="#fff" />
          <Text style={styles.createButtonText}>Criar Novo</Text>
        </TouchableOpacity>

        {/* Unified List */}
        <View style={styles.section}>
          {loading ? (
            <ActivityIndicator size="large" color="#1a237e" style={{ marginTop: 24 }} />
          ) : unifiedItems.length > 0 ? (
            <FlatList
              data={unifiedItems}
              renderItem={renderItem}
              keyExtractor={(item) => `${item.kind}-${item.data.id}`}
              scrollEnabled={false}
            />
          ) : (
            <View style={styles.emptyContainer}>
              <Ionicons name="folder-open-outline" size={48} color="#ccc" />
              <Text style={styles.emptyText}>Nenhum registro criado ainda</Text>
            </View>
          )}
        </View>
      </ScrollView>

      {/* Create Modal */}
      <Modal visible={showCreateModal} transparent animationType="fade">
        <TouchableOpacity style={styles.modalOverlay} activeOpacity={1} onPress={() => setShowCreateModal(false)}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>O que deseja criar?</Text>
            <TouchableOpacity
              style={styles.modalOption}
              onPress={() => handleCreateOption('timesheet')}
            >
              <Ionicons name="time-outline" size={28} color="#1a237e" />
              <View style={styles.modalOptionText}>
                <Text style={styles.modalOptionTitle}>Timesheet</Text>
                <Text style={styles.modalOptionDesc}>Registro de horas trabalhadas</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#999" />
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.modalOption}
              onPress={() => handleCreateOption('service_report')}
            >
              <Ionicons name="construct-outline" size={28} color="#1565c0" />
              <View style={styles.modalOptionText}>
                <Text style={styles.modalOptionTitle}>Relatório de Serviço</Text>
                <Text style={styles.modalOptionDesc}>Relatório técnico do serviço</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#999" />
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.modalOption}
              onPress={() => handleCreateOption('daily_report')}
            >
              <Ionicons name="calendar-outline" size={28} color="#2e7d32" />
              <View style={styles.modalOptionText}>
                <Text style={styles.modalOptionTitle}>Relatório Diário</Text>
                <Text style={styles.modalOptionDesc}>Relatório das atividades diárias</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#999" />
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.modalCancel}
              onPress={() => setShowCreateModal(false)}
            >
              <Text style={styles.modalCancelText}>Cancelar</Text>
            </TouchableOpacity>
          </View>
        </TouchableOpacity>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  scrollContent: { padding: 16 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 },
  title: { fontSize: 28, fontWeight: 'bold', color: '#1a237e' },
  subtitle: { fontSize: 16, color: '#666', marginTop: 4 },
  logoutButton: { padding: 8 },
  createButton: { backgroundColor: '#1a237e', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', padding: 16, borderRadius: 12, marginBottom: 16 },
  createButtonText: { color: '#fff', fontSize: 18, fontWeight: '600', marginLeft: 8 },
  section: { marginBottom: 24 },
  card: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.1, shadowRadius: 2, elevation: 2 },
  topRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 },
  badgeRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  badge: { backgroundColor: '#e3f2fd', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 8 },
  badgeText: { color: '#1a237e', fontWeight: '600', fontSize: 12 },
  typeBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6 },
  typeBadgeText: { fontSize: 11, fontWeight: '600' },
  actions: { flexDirection: 'row', gap: 4 },
  actionBtn: { padding: 8 },
  cardInfo: { paddingLeft: 2 },
  cardTitle: { fontSize: 16, fontWeight: '600', color: '#212121' },
  cardSubtitle: { fontSize: 14, color: '#666', marginTop: 4 },
  cardService: { fontSize: 13, color: '#444', marginTop: 2, fontStyle: 'italic' },
  cardMeta: { fontSize: 12, color: '#999', marginTop: 4 },
  dateRange: { fontSize: 12, color: '#1a237e', marginTop: 4, fontWeight: '500' },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 6 },
  statusBadge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4 },
  statusText: { fontSize: 11, fontWeight: '600' },
  emptyContainer: { alignItems: 'center', justifyContent: 'center', paddingVertical: 48 },
  emptyText: { fontSize: 14, color: '#999', marginTop: 12 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center', padding: 24 },
  modalContent: { backgroundColor: '#fff', borderRadius: 16, padding: 24, width: '100%', maxWidth: 400 },
  modalTitle: { fontSize: 20, fontWeight: '700', color: '#1a237e', marginBottom: 20, textAlign: 'center' },
  modalOption: { flexDirection: 'row', alignItems: 'center', padding: 16, borderRadius: 12, backgroundColor: '#f8f9fa', marginBottom: 12 },
  modalOptionText: { flex: 1, marginLeft: 12 },
  modalOptionTitle: { fontSize: 16, fontWeight: '600', color: '#212121' },
  modalOptionDesc: { fontSize: 12, color: '#666', marginTop: 2 },
  modalCancel: { alignItems: 'center', paddingVertical: 12, marginTop: 4 },
  modalCancelText: { fontSize: 16, color: '#999', fontWeight: '500' },
});
