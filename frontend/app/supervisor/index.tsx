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

type TabType = 'timesheets' | 'service_reports' | 'daily_reports';

export default function SupervisorDashboard() {
  const { user, signOut, ensureReportAuth } = useAuth();
  const router = useRouter();
  const [timesheets, setTimesheets] = useState<Timesheet[]>([]);
  const [serviceReports, setServiceReports] = useState<Report[]>([]);
  const [dailyReports, setDailyReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabType>('timesheets');
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
      setServiceReports(allReports.filter(r => r.report_type === 'service'));
      setDailyReports(allReports.filter(r => r.report_type === 'daily'));
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
      if (report.report_type === 'service') {
        setServiceReports(prev => prev.filter(r => r.id !== report.id));
      } else {
        setDailyReports(prev => prev.filter(r => r.id !== report.id));
      }
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

  const renderTimesheet = ({ item }: { item: Timesheet }) => (
    <TouchableOpacity
      style={styles.tsCard}
      data-testid={`timesheet-card-${item.id}`}
      onPress={() => router.push(`/supervisor/edit-timesheet?id=${item.id}`)}
      activeOpacity={0.7}
    >
      <View style={styles.tsTopRow}>
        <View style={styles.tsBadge}>
          <Text style={styles.tsBadgeText}>{item.os_number}</Text>
        </View>
        <View style={styles.tsActions}>
          <TouchableOpacity onPress={() => handleOpenPDF(item)} style={styles.tsActionButton} data-testid={`open-pdf-btn-${item.id}`}>
            <Ionicons name="document-text-outline" size={20} color="#1a237e" />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => router.push(`/supervisor/edit-timesheet?id=${item.id}`)} style={styles.tsActionButton} data-testid={`edit-btn-${item.id}`}>
            <Ionicons name="pencil" size={20} color="#1a237e" />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => handleDownloadPDF(item)} style={styles.tsActionButton} data-testid={`download-pdf-btn-${item.id}`}>
            <Ionicons name="download-outline" size={20} color="#1a237e" />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => handleDeleteTimesheet(item)} style={styles.tsActionButton} data-testid={`delete-btn-${item.id}`}>
            <Ionicons name="trash-outline" size={20} color="#d32f2f" />
          </TouchableOpacity>
        </View>
      </View>
      <View style={styles.tsCardInfo}>
        <Text style={styles.tsCardTitle}>{item.client}</Text>
        <Text style={styles.tsCardSubtitle}>{item.location}</Text>
        <Text style={styles.tsCardService} numberOfLines={1} data-testid={`timesheet-service-${item.id}`}>{item.service}</Text>
        <Text style={styles.tsCardMeta}>{item.entries.length} entrada(s)</Text>
        {item.entries.length > 0 && (
          <Text style={styles.tsDateRange} data-testid={`timesheet-date-range-${item.id}`}>{getDateRangeText(item.entries)}</Text>
        )}
      </View>
    </TouchableOpacity>
  );

  const renderReport = ({ item }: { item: Report }) => (
    <View style={styles.tsCard} data-testid={`report-card-${item.id}`}>
      <View style={styles.tsTopRow}>
        <View style={styles.tsBadge}>
          <Text style={styles.tsBadgeText}>{item.service_order_number}</Text>
        </View>
        <View style={styles.tsActions}>
          <TouchableOpacity onPress={() => handleOpenReportPDF(item)} style={styles.tsActionButton} data-testid={`report-pdf-btn-${item.id}`}>
            <Ionicons name="document-text-outline" size={20} color="#1a237e" />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => handleDownloadReportPDF(item)} style={styles.tsActionButton} data-testid={`report-download-btn-${item.id}`}>
            <Ionicons name="download-outline" size={20} color="#1a237e" />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => handleDeleteReport(item)} style={styles.tsActionButton} data-testid={`report-delete-btn-${item.id}`}>
            <Ionicons name="trash-outline" size={20} color="#d32f2f" />
          </TouchableOpacity>
        </View>
      </View>
      <View style={styles.tsCardInfo}>
        <Text style={styles.tsCardTitle}>{item.client}</Text>
        <Text style={styles.tsCardSubtitle}>{item.vessel} - {item.equipment}</Text>
        <Text style={styles.tsCardService} numberOfLines={1}>{item.supervisor_name}</Text>
        <View style={styles.statusRow}>
          <View style={[styles.statusBadge, { backgroundColor: getStatusColor(item.status) + '20' }]}>
            <Text style={[styles.statusText, { color: getStatusColor(item.status) }]}>{getStatusLabel(item.status)}</Text>
          </View>
          <Text style={styles.tsCardMeta}>{formatDate(item.created_at)}</Text>
        </View>
      </View>
    </View>
  );

  const tabs: { key: TabType; label: string; icon: string }[] = [
    { key: 'timesheets', label: 'Timesheets', icon: 'time-outline' },
    { key: 'service_reports', label: 'Rel. Serviço', icon: 'construct-outline' },
    { key: 'daily_reports', label: 'Rel. Diário', icon: 'calendar-outline' },
  ];

  const getCurrentData = () => {
    switch (activeTab) {
      case 'timesheets': return timesheets;
      case 'service_reports': return serviceReports;
      case 'daily_reports': return dailyReports;
    }
  };

  const getEmptyMessage = () => {
    switch (activeTab) {
      case 'timesheets': return 'Nenhum timesheet criado ainda';
      case 'service_reports': return 'Nenhum relatório de serviço encontrado';
      case 'daily_reports': return 'Nenhum relatório diário encontrado';
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <View>
            <Text style={styles.title}>TWAS REPAIR</Text>
            <Text style={styles.subtitle}>Bem-vindo, {user?.name}</Text>
          </View>
          <TouchableOpacity onPress={handleLogout} style={styles.logoutButton} data-testid="logout-btn">
            <Ionicons name="log-out-outline" size={24} color="#d32f2f" />
          </TouchableOpacity>
        </View>

        {/* Tab Bar */}
        <View style={styles.tabBar} data-testid="tab-bar">
          {tabs.map(tab => (
            <TouchableOpacity
              key={tab.key}
              style={[styles.tab, activeTab === tab.key && styles.tabActive]}
              onPress={() => setActiveTab(tab.key)}
              data-testid={`tab-${tab.key}`}
            >
              <Ionicons name={tab.icon as any} size={18} color={activeTab === tab.key ? '#1a237e' : '#999'} />
              <Text style={[styles.tabText, activeTab === tab.key && styles.tabTextActive]}>{tab.label}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Create Button */}
        <TouchableOpacity
          style={styles.createButton}
          onPress={() => setShowCreateModal(true)}
          data-testid="create-new-btn"
        >
          <Ionicons name="add-circle" size={24} color="#fff" />
          <Text style={styles.createButtonText}>Criar Novo</Text>
        </TouchableOpacity>

        {/* Content */}
        <View style={styles.section}>
          {loading ? (
            <ActivityIndicator size="large" color="#1a237e" style={{ marginTop: 24 }} />
          ) : getCurrentData().length > 0 ? (
            <FlatList
              data={getCurrentData() as any[]}
              renderItem={activeTab === 'timesheets' ? renderTimesheet : renderReport}
              keyExtractor={(item) => item.id}
              scrollEnabled={false}
            />
          ) : (
            <View style={styles.emptyContainer}>
              <Ionicons name="folder-open-outline" size={48} color="#ccc" />
              <Text style={styles.emptyText}>{getEmptyMessage()}</Text>
            </View>
          )}
        </View>
      </ScrollView>

      {/* Create Modal */}
      <Modal visible={showCreateModal} transparent animationType="fade" data-testid="create-modal">
        <TouchableOpacity style={styles.modalOverlay} activeOpacity={1} onPress={() => setShowCreateModal(false)}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>O que deseja criar?</Text>
            <TouchableOpacity
              style={styles.modalOption}
              onPress={() => handleCreateOption('timesheet')}
              data-testid="create-timesheet-option"
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
              data-testid="create-service-report-option"
            >
              <Ionicons name="construct-outline" size={28} color="#1a237e" />
              <View style={styles.modalOptionText}>
                <Text style={styles.modalOptionTitle}>Relatório de Serviço</Text>
                <Text style={styles.modalOptionDesc}>Relatório técnico do serviço</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#999" />
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.modalOption}
              onPress={() => handleCreateOption('daily_report')}
              data-testid="create-daily-report-option"
            >
              <Ionicons name="calendar-outline" size={28} color="#1a237e" />
              <View style={styles.modalOptionText}>
                <Text style={styles.modalOptionTitle}>Relatório Diário</Text>
                <Text style={styles.modalOptionDesc}>Relatório das atividades diárias</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#999" />
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.modalCancel}
              onPress={() => setShowCreateModal(false)}
              data-testid="create-modal-cancel"
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
  tabBar: { flexDirection: 'row', backgroundColor: '#fff', borderRadius: 12, marginBottom: 16, padding: 4 },
  tab: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 10, borderRadius: 8, gap: 4 },
  tabActive: { backgroundColor: '#e3f2fd' },
  tabText: { fontSize: 12, color: '#999', fontWeight: '500' },
  tabTextActive: { color: '#1a237e', fontWeight: '600' },
  createButton: { backgroundColor: '#1a237e', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', padding: 16, borderRadius: 12, marginBottom: 16 },
  createButtonText: { color: '#fff', fontSize: 18, fontWeight: '600', marginLeft: 8 },
  section: { marginBottom: 24 },
  tsCard: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.1, shadowRadius: 2, elevation: 2 },
  tsTopRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 },
  tsActions: { flexDirection: 'row', gap: 4 },
  tsActionButton: { padding: 8 },
  tsBadge: { backgroundColor: '#e3f2fd', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8, marginRight: 12 },
  tsBadgeText: { color: '#1a237e', fontWeight: '600', fontSize: 12 },
  tsCardInfo: { paddingLeft: 2 },
  tsCardTitle: { fontSize: 16, fontWeight: '600', color: '#212121' },
  tsCardSubtitle: { fontSize: 14, color: '#666', marginTop: 4 },
  tsCardService: { fontSize: 13, color: '#444', marginTop: 2, fontStyle: 'italic' },
  tsCardMeta: { fontSize: 12, color: '#999', marginTop: 4 },
  tsDateRange: { fontSize: 12, color: '#1a237e', marginTop: 4, fontWeight: '500' },
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
