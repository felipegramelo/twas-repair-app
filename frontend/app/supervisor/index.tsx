import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, Alert, ActivityIndicator, Platform, Modal, TextInput } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { timesheetAPI, reportAPI, serviceOrderAPI } from '../../services/api';
import { offlineQueue } from '../../services/offlineQueue';
import { useOffline } from '../../contexts/OfflineContext';
import { OfflineBanner } from '../../components/OfflineBanner';
import { BACKEND_URL } from '../../services/config';
import { buildPdfFilename } from '../../utils/pdfHelper';
import { Timesheet, Report, ServiceOrder } from '../../types';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as FileSystem from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';
import { Picker } from '@react-native-picker/picker';

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
  const { user, signOut } = useAuth();
  const router = useRouter();
  const [timesheets, setTimesheets] = useState<Timesheet[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [offlineTimesheets, setOfflineTimesheets] = useState<any[]>([]);
  const [offlineReports, setOfflineReports] = useState<any[]>([]);
  const { pendingCount, isOnline } = useOffline();
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showDuplicateModal, setShowDuplicateModal] = useState(false);
  const [duplicatingReport, setDuplicatingReport] = useState<Report | null>(null);
  const [serviceOrders, setServiceOrders] = useState<ServiceOrder[]>([]);
  const [dupOsId, setDupOsId] = useState('');
  const [dupPeriodoInicio, setDupPeriodoInicio] = useState('');
  const [dupPeriodoFim, setDupPeriodoFim] = useState('');
  const [duplicating, setDuplicating] = useState(false);
  const [authToken, setAuthToken] = useState('');

  useEffect(() => { loadData(); AsyncStorage.getItem('token').then(t => t && setAuthToken(t)); }, []);

  // Reload data whenever the offline queue changes (e.g., new offline draft
  // was created, or items were synced).
  useEffect(() => { loadData(); }, [pendingCount, isOnline]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [tsData, allReports, osData, offTs, offRep] = await Promise.all([
        timesheetAPI.getAll().catch(() => []),
        reportAPI.getAll().catch(() => []),
        serviceOrderAPI.getAll().catch(() => []),
        offlineQueue.getOfflineTimesheets(),
        offlineQueue.getOfflineReports(),
      ]);
      setTimesheets(tsData.filter((t: any) => t.status !== 'finalized'));
      setReports(allReports.filter((r: any) => r.status !== 'finalized'));
      setOfflineTimesheets(offTs);
      setOfflineReports(offRep);
      setServiceOrders(osData);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
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
        const baseURL = BACKEND_URL + '/api';
        const fileName = buildPdfFilename('TM', timesheet.os_number, timesheet.client, timesheet.service);
        const fileUri = `${FileSystem.cacheDirectory}${fileName}`;
        const result = await FileSystem.downloadAsync(
          `${baseURL}/timesheets/${timesheet.id}/pdf?t=${Date.now()}`,
          fileUri,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        if (result.status === 200) {
          const isAvailable = await Sharing.isAvailableAsync();
          if (isAvailable) await Sharing.shareAsync(result.uri, { mimeType: 'application/pdf', UTI: 'com.adobe.pdf', dialogTitle: fileName });
          else Alert.alert('Sucesso', 'PDF salvo em: ' + result.uri);
        } else Alert.alert('Erro', 'Erro ao gerar PDF. Status: ' + result.status);
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
        link.download = buildPdfFilename('TM', timesheet.os_number, timesheet.client, timesheet.service);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      } else {
        const token = await AsyncStorage.getItem('token');
        const baseURL = BACKEND_URL + '/api';
        const fileName = buildPdfFilename('TM', timesheet.os_number, timesheet.client, timesheet.service);
        const fileUri = `${FileSystem.cacheDirectory}${fileName}`;
        const result = await FileSystem.downloadAsync(
          `${baseURL}/timesheets/${timesheet.id}/pdf?t=${Date.now()}`,
          fileUri,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        if (result.status === 200) {
          const isAvailable = await Sharing.isAvailableAsync();
          if (isAvailable) await Sharing.shareAsync(result.uri, { mimeType: 'application/pdf', UTI: 'com.adobe.pdf', dialogTitle: fileName });
          else Alert.alert('Sucesso', 'PDF salvo em: ' + result.uri);
        } else Alert.alert('Erro', 'Erro ao gerar PDF. Status: ' + result.status);
      }
    } catch (error: any) {
      if (Platform.OS === 'web') window.alert('Erro ao baixar PDF');
      else Alert.alert('Erro', 'Erro ao baixar PDF: ' + (error.message || ''));
    }
  };

  const getReportPdfUrl = (reportId: string) => {
    const baseURL = BACKEND_URL || process.env.EXPO_PUBLIC_REPORT_API_URL?.replace('/api', '');
    return `${baseURL}/api/reports/${reportId}/pdf?token=${encodeURIComponent(authToken)}&t=${Date.now()}`;
  };

  const handleOpenReportPDF = async (report: Report) => {
    try {
      if (Platform.OS === 'web') {
        const url = getReportPdfUrl(report.id);
        window.open(url, '_blank');
      } else {
        const token = await AsyncStorage.getItem('token');
        const baseURL = BACKEND_URL + '/api';
        const fileName = buildPdfFilename('REL', report.os_number, report.client, report.service);
        const fileUri = `${FileSystem.cacheDirectory}${fileName}`;
        const result = await FileSystem.downloadAsync(
          `${baseURL}/reports/${report.id}/pdf?token=${encodeURIComponent(token || '')}&t=${Date.now()}`,
          fileUri
        );
        if (result.status === 200) {
          const isAvailable = await Sharing.isAvailableAsync();
          if (isAvailable) await Sharing.shareAsync(result.uri, { mimeType: 'application/pdf', UTI: 'com.adobe.pdf', dialogTitle: fileName });
          else Alert.alert('Sucesso', 'PDF salvo em: ' + result.uri);
        } else Alert.alert('Erro', 'Erro ao gerar PDF. Status: ' + result.status);
      }
    } catch (error: any) {
      if (Platform.OS === 'web') window.alert('Erro ao abrir PDF do relatório');
      else Alert.alert('Erro', 'Erro ao abrir PDF: ' + (error.message || ''));
    }
  };

  const handleDownloadReportPDF = async (report: Report) => {
    try {
      if (Platform.OS === 'web') {
        const url = getReportPdfUrl(report.id);
        window.location.href = url;
      } else {
        const token = await AsyncStorage.getItem('token');
        const baseURL = BACKEND_URL + '/api';
        const fileName = buildPdfFilename('REL', report.os_number, report.client, report.service);
        const fileUri = `${FileSystem.cacheDirectory}${fileName}`;
        const result = await FileSystem.downloadAsync(
          `${baseURL}/reports/${report.id}/pdf?token=${encodeURIComponent(token || '')}&t=${Date.now()}`,
          fileUri
        );
        if (result.status === 200) {
          const isAvailable = await Sharing.isAvailableAsync();
          if (isAvailable) await Sharing.shareAsync(result.uri, { mimeType: 'application/pdf', UTI: 'com.adobe.pdf', dialogTitle: fileName });
          else Alert.alert('Sucesso', 'PDF salvo em: ' + result.uri);
        } else Alert.alert('Erro', 'Erro ao gerar PDF. Status: ' + result.status);
      }
    } catch (error: any) {
      if (Platform.OS === 'web') window.alert('Erro ao baixar PDF do relatório');
      else Alert.alert('Erro', 'Erro ao baixar PDF: ' + (error.message || ''));
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
    } catch { Alert.alert('Erro', 'Erro ao excluir timesheet'); }
  };

  const handleDeleteReport = (report: Report) => {
    const label = report.report_type === 'service' ? 'relatório de serviço' : 'relatório diário';
    if (Platform.OS === 'web') {
      if (window.confirm(`Excluir ${label} ${report.os_number} - ${report.client}?`)) deleteReport(report);
    } else {
      Alert.alert('Confirmar Exclusão', `Excluir ${label}?`, [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Excluir', style: 'destructive', onPress: () => deleteReport(report) },
      ]);
    }
  };

  const deleteReport = async (report: Report) => {
    try {
      await reportAPI.delete(report.id);
      setReports(prev => prev.filter(r => r.id !== report.id));
    } catch { Alert.alert('Erro', 'Erro ao excluir relatório'); }
  };

  const handleDuplicate = (report: Report) => {
    setDuplicatingReport(report);
    setDupOsId(report.os_id);
    setDupPeriodoInicio(report.periodo_inicio || '');
    setDupPeriodoFim(report.periodo_fim || '');
    setShowDuplicateModal(true);
  };

  const confirmDuplicate = async () => {
    if (!duplicatingReport) return;
    setDuplicating(true);
    try {
      await reportAPI.duplicate(duplicatingReport.id, {
        os_id: dupOsId,
        periodo_inicio: dupPeriodoInicio,
        periodo_fim: dupPeriodoFim,
      });
      setShowDuplicateModal(false);
      if (Platform.OS === 'web') window.alert('Relatório duplicado com sucesso!');
      else Alert.alert('Sucesso', 'Relatório duplicado com sucesso!');
      loadData();
    } catch (error: any) {
      Alert.alert('Erro', 'Erro ao duplicar: ' + (error.message || ''));
    } finally {
      setDuplicating(false);
    }
  };

  const handleCreateOption = (option: 'timesheet' | 'service_report' | 'daily_report') => {
    setShowCreateModal(false);
    if (option === 'timesheet') router.push('/supervisor/create-timesheet');
    else router.push(`/supervisor/create-report?type=${option === 'service_report' ? 'service' : 'daily'}`);
  };

  const handleFinalizeTimesheet = async (ts: Timesheet) => {
    const msg = 'Você deseja enviar para o administrador essa Timesheet? Após o envio você não poderá mais editá-la.';
    if (Platform.OS === 'web') { if (!window.confirm(msg)) return; }
    else {
      const confirmed = await new Promise<boolean>((resolve) =>
        Alert.alert('Enviar Timesheet', msg, [
          { text: 'Cancelar', style: 'cancel', onPress: () => resolve(false) },
          { text: 'Enviar', onPress: () => resolve(true) },
        ])
      );
      if (!confirmed) return;
    }
    try {
      await timesheetAPI.finalize(ts.id);
      if (Platform.OS === 'web') window.alert('Timesheet enviada para o administrador com sucesso!');
      else Alert.alert('Sucesso', 'Timesheet enviada para o administrador com sucesso!');
      loadData();
    } catch {
      if (Platform.OS === 'web') window.alert('Erro ao enviar timesheet');
      else Alert.alert('Erro', 'Erro ao enviar timesheet');
    }
  };

  const handleFinalizeReport = async (rpt: Report) => {
    const typeLabel = rpt.report_type === 'service' ? 'Relatório de Serviço' : 'Relatório Diário';
    const msg = `Você deseja enviar para o administrador esse ${typeLabel}? Após o envio você não poderá mais editá-lo.`;
    if (Platform.OS === 'web') { if (!window.confirm(msg)) return; }
    else {
      const confirmed = await new Promise<boolean>((resolve) =>
        Alert.alert(`Enviar ${typeLabel}`, msg, [
          { text: 'Cancelar', style: 'cancel', onPress: () => resolve(false) },
          { text: 'Enviar', onPress: () => resolve(true) },
        ])
      );
      if (!confirmed) return;
    }
    try {
      await reportAPI.finalize(rpt.id);
      if (Platform.OS === 'web') window.alert(`${typeLabel} enviado para o administrador com sucesso!`);
      else Alert.alert('Sucesso', `${typeLabel} enviado para o administrador com sucesso!`);
      loadData();
    } catch {
      if (Platform.OS === 'web') window.alert(`Erro ao enviar ${typeLabel.toLowerCase()}`);
      else Alert.alert('Erro', `Erro ao enviar ${typeLabel.toLowerCase()}`);
    }
  };

  const handleDuplicateTimesheet = async (ts: Timesheet) => {
    if (Platform.OS === 'web') { if (!window.confirm('Deseja duplicar esta timesheet?')) return; }
    else {
      const confirmed = await new Promise<boolean>((resolve) =>
        Alert.alert('Duplicar Timesheet', 'Deseja duplicar esta timesheet?', [
          { text: 'Cancelar', style: 'cancel', onPress: () => resolve(false) },
          { text: 'Duplicar', onPress: () => resolve(true) },
        ])
      );
      if (!confirmed) return;
    }
    try {
      await timesheetAPI.duplicate(ts.id);
      if (Platform.OS === 'web') window.alert('Timesheet duplicada com sucesso!');
      else Alert.alert('Sucesso', 'Timesheet duplicada com sucesso!');
      loadData();
    } catch {
      if (Platform.OS === 'web') window.alert('Erro ao duplicar timesheet');
      else Alert.alert('Erro', 'Erro ao duplicar timesheet');
    }
  };

  const formatDate = (dateStr: string) => {
    try { return new Date(dateStr).toLocaleDateString('pt-BR'); } catch { return dateStr; }
  };

  const formatDateInput = (text: string, setter: (v: string) => void) => {
    const cleaned = text.replace(/\D/g, '');
    let formatted = cleaned;
    if (cleaned.length >= 3 && cleaned.length <= 4) formatted = cleaned.slice(0, 2) + '/' + cleaned.slice(2);
    else if (cleaned.length >= 5) formatted = cleaned.slice(0, 2) + '/' + cleaned.slice(2, 4) + '/' + cleaned.slice(4, 8);
    setter(formatted);
  };

  const getStatusLabel = (s: string) => s === 'draft' ? 'Rascunho' : s === 'finalized' ? 'Finalizado' : s === 'completed' ? 'Concluído' : s === 'approved' ? 'Aprovado' : s;
  const getStatusColor = (s: string) => s === 'draft' ? '#ff9800' : s === 'finalized' ? '#4caf50' : s === 'completed' ? '#4caf50' : s === 'approved' ? '#2196f3' : '#999';
  const getReportTypeLabel = (t: string) => t === 'service' ? 'Rel. Serviço' : 'Rel. Diário';
  const getReportTypeColor = (t: string) => t === 'service' ? '#1565c0' : '#2e7d32';

  const [translateTarget, setTranslateTarget] = useState<{id: string, type: string} | null>(null);
  const [translating, setTranslating] = useState(false);

  const handleTranslate = async (docId: string, docType: string, targetLang: string) => {
    setTranslateTarget(null);
    setTranslating(true);
    try {
      const token = await AsyncStorage.getItem('token');
      const baseURL = BACKEND_URL + '/api';
      const resp = await fetch(`${baseURL}/translate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ document_id: docId, document_type: docType, target_language: targetLang })
      });
      const data = await resp.json();
      if (resp.ok) {
        const langName = targetLang === 'en' ? 'Inglês' : 'Espanhol';
        if (Platform.OS === 'web') window.alert(`Traduzido para ${langName} com sucesso! Uma cópia foi criada.`);
        else Alert.alert('Sucesso', `Traduzido para ${langName} com sucesso! Uma cópia foi criada.`);
        loadData();
      } else {
        const msg = data.detail || 'Erro ao traduzir';
        if (Platform.OS === 'web') window.alert(msg);
        else Alert.alert('Erro', msg);
      }
    } catch (error: any) {
      if (Platform.OS === 'web') window.alert('Erro ao traduzir: ' + (error.message || ''));
      else Alert.alert('Erro', 'Erro ao traduzir: ' + (error.message || ''));
    } finally {
      setTranslating(false);
    }
  };

  const unifiedItems: UnifiedItem[] = [
    ...offlineTimesheets.map(t => ({ kind: 'timesheet' as const, data: t as any })),
    ...offlineReports.map(r => ({ kind: 'report' as const, data: r as any })),
    ...timesheets.map(t => ({ kind: 'timesheet' as const, data: t })),
    ...reports.map(r => ({ kind: 'report' as const, data: r })),
  ];

  return (
    <SafeAreaView style={styles.container}>
      <OfflineBanner />
      <View style={styles.innerContainer}>
        <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={true}>
          <View style={styles.header}>
            <View>
              <Text style={styles.title}>TWAS REPAIR</Text>
              <Text style={styles.subtitle}>Bem-vindo, {user?.name}</Text>
            </View>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <TouchableOpacity onPress={() => router.push('/supervisor/change-password')} style={styles.logoutButton} data-testid="change-password-btn">
                <Ionicons name="key-outline" size={24} color="#000000" />
              </TouchableOpacity>
              <TouchableOpacity onPress={handleLogout} style={styles.logoutButton} data-testid="logout-btn">
                <Ionicons name="log-out-outline" size={24} color="#d32f2f" />
              </TouchableOpacity>
            </View>
          </View>

          <TouchableOpacity style={styles.createButton} onPress={() => setShowCreateModal(true)} data-testid="create-new-btn">
            <Ionicons name="add-circle" size={24} color="#fff" />
            <Text style={styles.createButtonText}>Criar Novo</Text>
          </TouchableOpacity>

          {loading ? (
            <ActivityIndicator size="large" color="#000000" style={{ marginTop: 24 }} />
          ) : unifiedItems.length > 0 ? (
            unifiedItems.map((item) => {
              if (item.kind === 'timesheet') {
                const ts = item.data;
                const isFinalized = (ts as any).status === 'finalized';
                const isOffline = !!(ts as any).is_offline;
                const isShared = !isOffline && ts.supervisor_id !== user?.id;
                return (
                  <TouchableOpacity key={`ts-${ts.id}`} style={[styles.card, isFinalized && { opacity: 0.85 }, isOffline && { borderColor: '#f57c00', borderWidth: 2 }]} onPress={() => !isFinalized && !isShared && !isOffline && router.push(`/supervisor/edit-timesheet?id=${ts.id}`)} activeOpacity={isFinalized || isShared || isOffline ? 1 : 0.7} data-testid={`timesheet-card-${ts.id}`}>
                    <View style={styles.topRow}>
                      <View style={styles.badgeRow}>
                        <View style={styles.badge}><Text style={styles.badgeText}>{ts.os_number}</Text></View>
                        <View style={styles.badgeTypeLine}>
                          <View style={[styles.typeBadge, { backgroundColor: '#f0f0f0' }]}>
                            <Ionicons name="time-outline" size={12} color="#000" />
                            <Text style={[styles.typeBadgeText, { color: '#000' }]}>Timesheet</Text>
                          </View>
                          {isOffline && (
                            <View style={[styles.typeBadge, { backgroundColor: '#fff3e0' }]}>
                              <Ionicons name="cloud-offline" size={12} color="#e65100" />
                              <Text style={[styles.typeBadgeText, { color: '#e65100' }]}>Pendente sincronização</Text>
                            </View>
                          )}
                          {isShared && (
                            <View style={[styles.typeBadge, { backgroundColor: '#e0f2f1' }]}>
                              <Ionicons name="share-social-outline" size={12} color="#00796b" />
                              <Text style={[styles.typeBadgeText, { color: '#00796b' }]}>Compartilhado</Text>
                            </View>
                          )}
                          {isFinalized && (
                            <View style={[styles.typeBadge, { backgroundColor: '#e8f5e9' }]}>
                              <Ionicons name="checkmark-circle" size={12} color="#2e7d32" />
                              <Text style={[styles.typeBadgeText, { color: '#2e7d32' }]}>Finalizado</Text>
                            </View>
                          )}
                          {(ts as any).language && (
                            <View style={[styles.typeBadge, { backgroundColor: '#e3f2fd' }]}>
                              <Ionicons name="language-outline" size={12} color="#1565c0" />
                              <Text style={[styles.typeBadgeText, { color: '#1565c0' }]}>Tradução {(ts as any).language === 'en' ? 'EN' : 'ES'}</Text>
                            </View>
                          )}
                        </View>
                      </View>
                      <View style={styles.actions}>
                        <TouchableOpacity onPress={(e) => { e.stopPropagation(); handleOpenPDF(ts); }} style={styles.actionBtn}><Ionicons name="document-text-outline" size={20} color="#000000" /></TouchableOpacity>
                        {isShared && (
                          <TouchableOpacity onPress={(e) => { e.stopPropagation(); handleDuplicateTimesheet(ts); }} style={styles.actionBtn} data-testid={`duplicate-shared-ts-${ts.id}`}><Ionicons name="copy-outline" size={20} color="#000000" /></TouchableOpacity>
                        )}
                        {!isFinalized && !isShared && (
                          <>
                            <TouchableOpacity onPress={(e) => { e.stopPropagation(); router.push(`/supervisor/edit-timesheet?id=${ts.id}`); }} style={styles.actionBtn}><Ionicons name="pencil" size={20} color="#000000" /></TouchableOpacity>
                            <TouchableOpacity onPress={(e) => { e.stopPropagation(); handleDeleteTimesheet(ts); }} style={styles.actionBtn}><Ionicons name="trash-outline" size={20} color="#d32f2f" /></TouchableOpacity>
                            <TouchableOpacity onPress={(e) => { e.stopPropagation(); handleDuplicateTimesheet(ts); }} style={styles.actionBtn} data-testid={`duplicate-ts-${ts.id}`}><Ionicons name="copy-outline" size={20} color="#000000" /></TouchableOpacity>
                            <TouchableOpacity onPress={(e) => { e.stopPropagation(); handleFinalizeTimesheet(ts); }} style={[styles.actionBtn, { backgroundColor: '#e8f5e9', borderRadius: 6 }]} data-testid={`finalize-ts-${ts.id}`}><Ionicons name="send" size={18} color="#2e7d32" /></TouchableOpacity>
                          </>
                        )}
                        <TouchableOpacity onPress={(e) => { e.stopPropagation(); handleDownloadPDF(ts); }} style={styles.actionBtn}><Ionicons name="download-outline" size={20} color="#000000" /></TouchableOpacity>
                        <TouchableOpacity onPress={(e) => { e.stopPropagation(); setTranslateTarget({id: ts.id, type: 'timesheet'}); }} style={styles.actionBtn} data-testid={`translate-ts-${ts.id}`}><Ionicons name="language-outline" size={20} color="#0066cc" /></TouchableOpacity>
                      </View>
                    </View>
                    <View style={styles.cardInfo}>
                      <Text style={styles.cardTitle}>{ts.client}</Text>
                      <Text style={styles.cardSubtitle}>{ts.location}</Text>
                      <Text style={styles.cardService} numberOfLines={1}>{ts.service}</Text>
                      {isShared && <Text style={{ fontSize: 12, color: '#00796b', marginTop: 2 }}>Por: {ts.supervisor_name}</Text>}
                      <Text style={styles.cardMeta}>{ts.entries.length} entrada(s)</Text>
                      {ts.entries.length > 0 && <Text style={styles.dateRange}>{getDateRangeText(ts.entries)}</Text>}
                    </View>
                  </TouchableOpacity>
                );
              }
              const rpt = item.data;
              const isRptFinalized = rpt.status === 'finalized';
              const isRptOffline = !!(rpt as any).is_offline;
              const isRptShared = !isRptOffline && rpt.supervisor_id !== user?.id;
              return (
                <TouchableOpacity key={`rpt-${rpt.id}`} style={[styles.card, isRptFinalized && { opacity: 0.85 }, isRptOffline && { borderColor: '#f57c00', borderWidth: 2 }]} onPress={() => !isRptFinalized && !isRptShared && !isRptOffline && router.push(`/supervisor/edit-report?id=${rpt.id}`)} activeOpacity={isRptFinalized || isRptShared || isRptOffline ? 1 : 0.7} data-testid={`report-card-${rpt.id}`}>
                  <View style={styles.topRow}>
                    <View style={styles.badgeRow}>
                      <View style={styles.badge}><Text style={styles.badgeText}>{rpt.os_number}</Text></View>
                      <View style={styles.badgeTypeLine}>
                        <View style={[styles.typeBadge, { backgroundColor: getReportTypeColor(rpt.report_type) + '15' }]}>
                          <Ionicons name={rpt.report_type === 'service' ? 'construct-outline' : 'calendar-outline'} size={12} color={getReportTypeColor(rpt.report_type)} />
                          <Text style={[styles.typeBadgeText, { color: getReportTypeColor(rpt.report_type) }]}>{getReportTypeLabel(rpt.report_type)}</Text>
                        </View>
                        {isRptOffline && (
                          <View style={[styles.typeBadge, { backgroundColor: '#fff3e0' }]}>
                            <Ionicons name="cloud-offline" size={12} color="#e65100" />
                            <Text style={[styles.typeBadgeText, { color: '#e65100' }]}>Pendente sincronização</Text>
                          </View>
                        )}
                        {isRptShared && (
                          <View style={[styles.typeBadge, { backgroundColor: '#e0f2f1' }]}>
                            <Ionicons name="share-social-outline" size={12} color="#00796b" />
                            <Text style={[styles.typeBadgeText, { color: '#00796b' }]}>Compartilhado</Text>
                          </View>
                        )}
                        {isRptFinalized && (
                          <View style={[styles.typeBadge, { backgroundColor: '#e8f5e9' }]}>
                            <Ionicons name="checkmark-circle" size={12} color="#2e7d32" />
                            <Text style={[styles.typeBadgeText, { color: '#2e7d32' }]}>Finalizado</Text>
                          </View>
                        )}
                        {(rpt as any).language && (
                          <View style={[styles.typeBadge, { backgroundColor: '#e3f2fd' }]}>
                            <Ionicons name="language-outline" size={12} color="#1565c0" />
                            <Text style={[styles.typeBadgeText, { color: '#1565c0' }]}>Tradução {(rpt as any).language === 'en' ? 'EN' : 'ES'}</Text>
                          </View>
                        )}
                      </View>
                    </View>
                    <View style={styles.actions}>
                      <TouchableOpacity onPress={(e) => { e.stopPropagation(); handleOpenReportPDF(rpt); }} style={styles.actionBtn}><Ionicons name="document-text-outline" size={20} color="#000000" /></TouchableOpacity>
                      {isRptShared && (
                        <TouchableOpacity onPress={(e) => { e.stopPropagation(); handleDuplicate(rpt); }} style={styles.actionBtn} data-testid={`duplicate-shared-report-${rpt.id}`}><Ionicons name="copy-outline" size={20} color="#000000" /></TouchableOpacity>
                      )}
                      {!isRptFinalized && !isRptShared && (
                        <>
                          <TouchableOpacity onPress={(e) => { e.stopPropagation(); router.push(`/supervisor/edit-report?id=${rpt.id}`); }} style={styles.actionBtn}><Ionicons name="pencil" size={20} color="#000000" /></TouchableOpacity>
                          <TouchableOpacity onPress={(e) => { e.stopPropagation(); handleDuplicate(rpt); }} style={styles.actionBtn} data-testid={`duplicate-report-${rpt.id}`}><Ionicons name="copy-outline" size={20} color="#000000" /></TouchableOpacity>
                          <TouchableOpacity onPress={(e) => { e.stopPropagation(); handleDeleteReport(rpt); }} style={styles.actionBtn}><Ionicons name="trash-outline" size={20} color="#d32f2f" /></TouchableOpacity>
                          <TouchableOpacity onPress={(e) => { e.stopPropagation(); handleFinalizeReport(rpt); }} style={[styles.actionBtn, { backgroundColor: '#e8f5e9', borderRadius: 6 }]} data-testid={`finalize-rpt-${rpt.id}`}><Ionicons name="send" size={18} color="#2e7d32" /></TouchableOpacity>
                        </>
                      )}
                      <TouchableOpacity onPress={(e) => { e.stopPropagation(); handleDownloadReportPDF(rpt); }} style={styles.actionBtn}><Ionicons name="download-outline" size={20} color="#000000" /></TouchableOpacity>
                      <TouchableOpacity onPress={(e) => { e.stopPropagation(); setTranslateTarget({id: rpt.id, type: 'report'}); }} style={styles.actionBtn} data-testid={`translate-rpt-${rpt.id}`}><Ionicons name="language-outline" size={20} color="#0066cc" /></TouchableOpacity>
                    </View>
                  </View>
                  <View style={styles.cardInfo}>
                    <Text style={styles.cardTitle}>{rpt.client}</Text>
                    <Text style={styles.cardSubtitle}>{rpt.location} - {rpt.service}</Text>
                    {isRptShared && <Text style={{ fontSize: 12, color: '#00796b', marginTop: 2 }}>Por: {rpt.supervisor_name}</Text>}
                    {!isRptShared && <Text style={styles.cardService} numberOfLines={1}>{rpt.supervisor_name}</Text>}
                    <View style={styles.statusRow}>
                      <View style={[styles.statusBadge, { backgroundColor: getStatusColor(rpt.status) + '20' }]}>
                        <Text style={[styles.statusText, { color: getStatusColor(rpt.status) }]}>{getStatusLabel(rpt.status)}</Text>
                      </View>
                      <Text style={styles.cardMeta}>{formatDate(rpt.created_at)}</Text>
                    </View>
                  </View>
                </TouchableOpacity>
              );
            })
          ) : (
            <View style={styles.emptyContainer}>
              <Ionicons name="folder-open-outline" size={48} color="#ccc" />
              <Text style={styles.emptyText}>Nenhum registro criado ainda</Text>
            </View>
          )}
        </ScrollView>
      </View>

      {/* Create Modal */}
      <Modal visible={showCreateModal} transparent animationType="fade">
        <TouchableOpacity style={styles.modalOverlay} activeOpacity={1} onPress={() => setShowCreateModal(false)}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>O que deseja criar?</Text>
            <TouchableOpacity style={styles.modalOption} onPress={() => handleCreateOption('timesheet')} data-testid="create-timesheet-option">
              <Ionicons name="time-outline" size={28} color="#000000" />
              <View style={styles.modalOptionText}>
                <Text style={styles.modalOptionTitle}>Timesheet</Text>
                <Text style={styles.modalOptionDesc}>Registro de horas trabalhadas</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#999" />
            </TouchableOpacity>
            <TouchableOpacity style={styles.modalOption} onPress={() => handleCreateOption('service_report')} data-testid="create-service-report-option">
              <Ionicons name="construct-outline" size={28} color="#1565c0" />
              <View style={styles.modalOptionText}>
                <Text style={styles.modalOptionTitle}>Relatório de Serviço</Text>
                <Text style={styles.modalOptionDesc}>Relatório técnico do serviço</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#999" />
            </TouchableOpacity>
            <TouchableOpacity style={styles.modalOption} onPress={() => handleCreateOption('daily_report')} data-testid="create-daily-report-option">
              <Ionicons name="calendar-outline" size={28} color="#2e7d32" />
              <View style={styles.modalOptionText}>
                <Text style={styles.modalOptionTitle}>Relatório Diário</Text>
                <Text style={styles.modalOptionDesc}>Relatório das atividades diárias</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#999" />
            </TouchableOpacity>
            <TouchableOpacity style={styles.modalCancel} onPress={() => setShowCreateModal(false)}>
              <Text style={styles.modalCancelText}>Cancelar</Text>
            </TouchableOpacity>
          </View>
        </TouchableOpacity>
      </Modal>

      {/* Translate Language Modal */}
      <Modal visible={!!translateTarget} transparent animationType="fade">
        <TouchableOpacity style={styles.modalOverlay} activeOpacity={1} onPress={() => setTranslateTarget(null)}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Traduzir para...</Text>
            <TouchableOpacity style={styles.modalOption} onPress={() => translateTarget && handleTranslate(translateTarget.id, translateTarget.type, 'en')} data-testid="translate-en">
              <Text style={{ fontSize: 28 }}>EN</Text>
              <View style={styles.modalOptionText}>
                <Text style={styles.modalOptionTitle}>Inglês</Text>
                <Text style={styles.modalOptionDesc}>Criar cópia traduzida em inglês</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#999" />
            </TouchableOpacity>
            <TouchableOpacity style={styles.modalOption} onPress={() => translateTarget && handleTranslate(translateTarget.id, translateTarget.type, 'es')} data-testid="translate-es">
              <Text style={{ fontSize: 28 }}>ES</Text>
              <View style={styles.modalOptionText}>
                <Text style={styles.modalOptionTitle}>Espanhol</Text>
                <Text style={styles.modalOptionDesc}>Criar cópia traduzida em espanhol</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#999" />
            </TouchableOpacity>
            <TouchableOpacity style={styles.modalCancel} onPress={() => setTranslateTarget(null)}>
              <Text style={styles.modalCancelText}>Cancelar</Text>
            </TouchableOpacity>
          </View>
        </TouchableOpacity>
      </Modal>

      {/* Translating Overlay */}
      {translating && (
        <View style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center', zIndex: 9999 }}>
          <View style={{ backgroundColor: '#fff', padding: 24, borderRadius: 12, alignItems: 'center' }}>
            <ActivityIndicator size="large" color="#000" />
            <Text style={{ marginTop: 12, fontSize: 16, fontWeight: '600' }}>Traduzindo...</Text>
            <Text style={{ marginTop: 4, fontSize: 12, color: '#666' }}>Isso pode levar alguns segundos</Text>
          </View>
        </View>
      )}

      {/* Duplicate Modal */}
      <Modal visible={showDuplicateModal} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.duplicateModalContent}>
            <Text style={styles.modalTitle}>Duplicar Relatório</Text>
            {duplicatingReport && (
              <Text style={styles.dupInfo}>
                Original: {duplicatingReport.os_number} - {duplicatingReport.client}
              </Text>
            )}
            <Text style={styles.dupLabel}>Ordem de Serviço</Text>
            <View style={styles.pickerContainer}>
              <Picker selectedValue={dupOsId} onValueChange={setDupOsId} style={styles.picker}>
                {serviceOrders.map(os => (
                  <Picker.Item key={os.id} label={`${os.os_number} - ${os.client}`} value={os.id} />
                ))}
              </Picker>
            </View>
            <Text style={styles.dupLabel}>Período</Text>
            <View style={styles.dateRow}>
              <View style={styles.dateField}>
                <Text style={styles.dateLabel}>Início</Text>
                <TextInput style={styles.dateInput} value={dupPeriodoInicio} onChangeText={(t) => formatDateInput(t, setDupPeriodoInicio)} placeholder="DD/MM/AAAA" keyboardType="numeric" maxLength={10} />
              </View>
              <View style={styles.dateField}>
                <Text style={styles.dateLabel}>Fim</Text>
                <TextInput style={styles.dateInput} value={dupPeriodoFim} onChangeText={(t) => formatDateInput(t, setDupPeriodoFim)} placeholder="DD/MM/AAAA" keyboardType="numeric" maxLength={10} />
              </View>
            </View>
            <View style={styles.dupActions}>
              <TouchableOpacity style={styles.dupCancelBtn} onPress={() => setShowDuplicateModal(false)}>
                <Text style={styles.dupCancelText}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[styles.dupConfirmBtn, duplicating && { opacity: 0.6 }]} onPress={confirmDuplicate} disabled={duplicating} data-testid="confirm-duplicate-btn">
                {duplicating ? <ActivityIndicator color="#fff" size="small" /> : (
                  <>
                    <Ionicons name="copy-outline" size={18} color="#fff" />
                    <Text style={styles.dupConfirmText}>Duplicar</Text>
                  </>
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
  innerContainer: { flex: 1, ...(Platform.OS === 'web' ? { height: '100vh', overflow: 'hidden' } : {}) } as any,
  scrollContent: { padding: 16, paddingBottom: 32 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 },
  title: { fontSize: 28, fontWeight: 'bold', color: '#000000' },
  subtitle: { fontSize: 16, color: '#666', marginTop: 4 },
  logoutButton: { padding: 8 },
  createButton: { backgroundColor: '#000000', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', padding: 16, borderRadius: 12, marginBottom: 16 },
  createButtonText: { color: '#fff', fontSize: 18, fontWeight: '600', marginLeft: 8 },
  card: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 12, ...(Platform.OS === 'web' ? { boxShadow: '0 1px 3px rgba(0,0,0,0.1)' } : { elevation: 2 }) } as any,
  topRow: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 10 },
  badgeRow: { flexDirection: 'column', alignItems: 'flex-start', gap: 4, flexShrink: 1 },
  badgeTypeLine: { flexDirection: 'row', alignItems: 'center', gap: 6, flexWrap: 'wrap' },
  badge: { backgroundColor: '#f0f0f0', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 8 },
  badgeText: { color: '#000000', fontWeight: '600', fontSize: 12 },
  typeBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6 },
  typeBadgeText: { fontSize: 11, fontWeight: '600' },
  actions: { flexDirection: 'row', gap: 2 },
  actionBtn: { padding: 6 },
  cardInfo: { paddingLeft: 2 },
  cardTitle: { fontSize: 16, fontWeight: '600', color: '#212121' },
  cardSubtitle: { fontSize: 14, color: '#666', marginTop: 4 },
  cardService: { fontSize: 13, color: '#444', marginTop: 2, fontStyle: 'italic' },
  cardMeta: { fontSize: 12, color: '#999', marginTop: 4 },
  dateRange: { fontSize: 12, color: '#000000', marginTop: 4, fontWeight: '500' },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 6 },
  statusBadge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4 },
  statusText: { fontSize: 11, fontWeight: '600' },
  emptyContainer: { alignItems: 'center', justifyContent: 'center', paddingVertical: 48 },
  emptyText: { fontSize: 14, color: '#999', marginTop: 12 },
  // Create Modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center', padding: 24 },
  modalContent: { backgroundColor: '#fff', borderRadius: 16, padding: 24, width: '100%', maxWidth: 400 },
  modalTitle: { fontSize: 20, fontWeight: '700', color: '#000000', marginBottom: 20, textAlign: 'center' },
  modalOption: { flexDirection: 'row', alignItems: 'center', padding: 16, borderRadius: 12, backgroundColor: '#f8f9fa', marginBottom: 12 },
  modalOptionText: { flex: 1, marginLeft: 12 },
  modalOptionTitle: { fontSize: 16, fontWeight: '600', color: '#212121' },
  modalOptionDesc: { fontSize: 12, color: '#666', marginTop: 2 },
  modalCancel: { alignItems: 'center', paddingVertical: 12, marginTop: 4 },
  modalCancelText: { fontSize: 16, color: '#999', fontWeight: '500' },
  // Duplicate Modal
  duplicateModalContent: { backgroundColor: '#fff', borderRadius: 16, padding: 24, width: '100%', maxWidth: 440 },
  dupInfo: { fontSize: 13, color: '#666', textAlign: 'center', marginBottom: 16 },
  dupLabel: { fontSize: 14, fontWeight: '600', color: '#333', marginBottom: 8, marginTop: 12 },
  pickerContainer: { backgroundColor: '#f8f9fa', borderRadius: 8, borderWidth: 1, borderColor: '#e0e0e0', overflow: 'hidden' },
  picker: { height: 50 },
  dateRow: { flexDirection: 'row', gap: 12 },
  dateField: { flex: 1 },
  dateLabel: { fontSize: 12, color: '#666', marginBottom: 4 },
  dateInput: { backgroundColor: '#f8f9fa', borderRadius: 8, borderWidth: 1, borderColor: '#e0e0e0', padding: 12, fontSize: 15, textAlign: 'center' },
  dupActions: { flexDirection: 'row', gap: 12, marginTop: 20 },
  dupCancelBtn: { flex: 1, padding: 14, borderRadius: 12, alignItems: 'center', backgroundColor: '#f5f5f5', borderWidth: 1, borderColor: '#e0e0e0' },
  dupCancelText: { fontSize: 16, color: '#666', fontWeight: '500' },
  dupConfirmBtn: { flex: 1, padding: 14, borderRadius: 12, alignItems: 'center', backgroundColor: '#000000', flexDirection: 'row', justifyContent: 'center', gap: 8 },
  dupConfirmText: { fontSize: 16, color: '#fff', fontWeight: '600' },
});
