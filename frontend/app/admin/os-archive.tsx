import React, { useState, useEffect } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, ScrollView, TextInput,
  ActivityIndicator, Platform, Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { archiveAPI, timesheetAPI, reportAPI } from '../../services/api';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { downloadAndSharePDF } from '../../utils/pdfHelper';

interface DocItem {
  id: string;
  os_number: string;
  client: string;
  location: string;
  service: string;
  supervisor_name: string;
  report_type?: string;
  status?: string;
  created_at: string;
  entries?: any[];
  periodo_inicio?: string;
  periodo_fim?: string;
}

interface OSArchive {
  id: string;
  os_number: string;
  client: string;
  location: string;
  service: string;
  timesheets: DocItem[];
  service_reports: DocItem[];
  daily_reports: DocItem[];
  total_documents: number;
}

const showMsg = (msg: string) => {
  if (Platform.OS === 'web') window.alert(msg);
  else Alert.alert('Info', msg);
};

function getDateRangeText(entries: any[]): string {
  if (!entries || entries.length === 0) return '';
  const dates = entries
    .map((e: any) => e.date).filter(Boolean)
    .map((d: string) => { const [day, month, year] = d.split('/'); return { raw: d, sortKey: `${year}-${month}-${day}` }; })
    .sort((a: any, b: any) => a.sortKey.localeCompare(b.sortKey));
  if (dates.length === 0) return '';
  const unique = [...new Set(dates.map((d: any) => d.raw))];
  return unique.length === 1 ? unique[0] : `${unique[0]} - ${unique[unique.length - 1]}`;
}

function formatDate(dateStr: string) {
  try { return new Date(dateStr).toLocaleDateString('pt-BR'); } catch { return dateStr; }
}

export default function OSArchiveScreen() {
  const router = useRouter();
  const [archives, setArchives] = useState<OSArchive[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [expandedOS, setExpandedOS] = useState<string | null>(null);

  useEffect(() => { loadArchive(); }, []);

  const loadArchive = async () => {
    try {
      const data = await archiveAPI.getOSArchive();
      setArchives(data);
    } catch {
      showMsg('Erro ao carregar arquivo');
    } finally {
      setLoading(false);
    }
  };

  const toggleOS = (osId: string) => {
    setExpandedOS(prev => prev === osId ? null : osId);
  };

  const filtered = archives.filter(os => {
    const q = search.toLowerCase();
    if (!q) return true;
    return os.os_number.toLowerCase().includes(q) ||
      os.client.toLowerCase().includes(q) ||
      os.location.toLowerCase().includes(q) ||
      os.service.toLowerCase().includes(q);
  });

  const handleOpenTimesheetPDF = async (ts: DocItem) => {
    try {
      const backendUrl = process.env.EXPO_PUBLIC_BACKEND_URL || '';
      const nativeUrl = `${backendUrl}/api/timesheets/${ts.id}/pdf?t=${Date.now()}`;
      await downloadAndSharePDF(
        () => timesheetAPI.downloadPDF(ts.id),
        nativeUrl,
        `timesheet_${ts.os_number}.pdf`,
      );
    } catch { showMsg('Erro ao abrir PDF do Timesheet'); }
  };

  const handleOpenReportPDF = async (report: DocItem) => {
    try {
      const backendUrl = process.env.EXPO_PUBLIC_BACKEND_URL || '';
      const nativeUrl = `${backendUrl}/api/reports/${report.id}/pdf?t=${Date.now()}`;
      await downloadAndSharePDF(
        () => reportAPI.downloadPDF(report.id),
        nativeUrl,
        `relatorio_${report.os_number}.pdf`,
      );
    } catch { showMsg('Erro ao abrir PDF do Relatório'); }
  };

  const handleDownloadTimesheetPDF = async (ts: DocItem) => {
    try {
      const backendUrl = process.env.EXPO_PUBLIC_BACKEND_URL || '';
      const nativeUrl = `${backendUrl}/api/timesheets/${ts.id}/pdf?t=${Date.now()}`;
      await downloadAndSharePDF(
        () => timesheetAPI.downloadPDF(ts.id),
        nativeUrl,
        `timesheet_${ts.os_number}_${ts.client.replace(/[^a-zA-Z0-9]/g, '_')}.pdf`,
      );
    } catch { showMsg('Erro ao baixar PDF'); }
  };

  const handleDownloadReportPDF = async (report: DocItem) => {
    try {
      const backendUrl = process.env.EXPO_PUBLIC_BACKEND_URL || '';
      const nativeUrl = `${backendUrl}/api/reports/${report.id}/pdf?t=${Date.now()}`;
      await downloadAndSharePDF(
        () => reportAPI.downloadPDF(report.id),
        nativeUrl,
        `relatorio_${report.os_number}_${report.report_type || 'service'}.pdf`,
      );
    } catch { showMsg('Erro ao baixar PDF'); }
  };

  const getStatusLabel = (s: string) => {
    switch (s) { case 'draft': return 'Rascunho'; case 'completed': return 'Concluído'; default: return s || ''; }
  };
  const getStatusColor = (s: string) => {
    switch (s) { case 'draft': return '#ff9800'; case 'completed': return '#4caf50'; default: return '#999'; }
  };

  const handleRevertTimesheet = async (doc: DocItem) => {
    if (Platform.OS === 'web') { if (!window.confirm(`Devolver timesheet para o supervisor ${doc.supervisor_name}?`)) return; }
    try {
      await timesheetAPI.revert(doc.id);
      if (Platform.OS === 'web') window.alert('Timesheet devolvida ao supervisor!');
      loadArchive();
    } catch { if (Platform.OS === 'web') window.alert('Erro ao devolver timesheet'); }
  };

  const handleRevertReport = async (doc: DocItem) => {
    if (Platform.OS === 'web') { if (!window.confirm(`Devolver relatório para o supervisor ${doc.supervisor_name}?`)) return; }
    try {
      await reportAPI.revert(doc.id);
      if (Platform.OS === 'web') window.alert('Relatório devolvido ao supervisor!');
      loadArchive();
    } catch { if (Platform.OS === 'web') window.alert('Erro ao devolver relatório'); }
  };

  const renderDocSection = (title: string, icon: string, docs: DocItem[], type: 'timesheet' | 'report') => {
    if (docs.length === 0) return null;
    return (
      <View style={s.docSection} data-testid={`doc-section-${type}`}>
        <View style={s.docSectionHeader}>
          <Ionicons name={icon as any} size={18} color="#1a237e" />
          <Text style={s.docSectionTitle}>{title} ({docs.length})</Text>
        </View>
        {docs.map(doc => (
          <View key={doc.id} style={s.docCard} data-testid={`doc-card-${doc.id}`}>
            <View style={s.docInfo}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                <Text style={s.docSupervisor}>{doc.supervisor_name}</Text>
                <View style={{ backgroundColor: '#e8f5e9', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 10 }}>
                  <Text style={{ fontSize: 10, color: '#2e7d32', fontWeight: '600' }}>Finalizado</Text>
                </View>
              </View>
              {type === 'timesheet' && doc.entries && (
                <Text style={s.docDate}>{getDateRangeText(doc.entries)} ({doc.entries.length} entrada{doc.entries.length !== 1 ? 's' : ''})</Text>
              )}
              {type === 'report' && (
                <>
                  {doc.report_type && (
                    <Text style={[s.docDate, { fontWeight: '600' }]}>{doc.report_type === 'service' ? 'Rel. Serviço' : 'Rel. Diário'}</Text>
                  )}
                  {doc.periodo_inicio && (
                    <Text style={s.docDate}>{doc.periodo_inicio}{doc.periodo_fim ? ` a ${doc.periodo_fim}` : ''}</Text>
                  )}
                </>
              )}
            </View>
            <View style={s.docActions}>
              <TouchableOpacity
                onPress={() => type === 'timesheet' ? handleOpenTimesheetPDF(doc) : handleOpenReportPDF(doc)}
                style={s.docActionBtn}
                data-testid={`view-pdf-${doc.id}`}
              >
                <Ionicons name="eye-outline" size={20} color="#1a237e" />
              </TouchableOpacity>
              <TouchableOpacity
                onPress={() => type === 'timesheet' ? handleDownloadTimesheetPDF(doc) : handleDownloadReportPDF(doc)}
                style={s.docActionBtn}
                data-testid={`download-pdf-${doc.id}`}
              >
                <Ionicons name="download-outline" size={20} color="#1a237e" />
              </TouchableOpacity>
              <TouchableOpacity
                onPress={() => type === 'timesheet' ? handleRevertTimesheet(doc) : handleRevertReport(doc)}
                style={[s.docActionBtn, { backgroundColor: '#fff3e0' }]}
                data-testid={`revert-${doc.id}`}
              >
                <Ionicons name="arrow-undo-outline" size={20} color="#e65100" />
              </TouchableOpacity>
            </View>
          </View>
        ))}
      </View>
    );
  };

  if (loading) return <View style={s.center}><ActivityIndicator size="large" color="#1a237e" /></View>;

  return (
    <SafeAreaView style={s.container}>
      <View style={s.header}>
        <TouchableOpacity onPress={() => router.replace('/admin')} style={s.backBtn} data-testid="archive-back-btn">
          <Ionicons name="arrow-back" size={24} color="#1a237e" />
        </TouchableOpacity>
        <Text style={s.title}>Arquivo por O.S.</Text>
        <View style={{ width: 40 }} />
      </View>

      <View style={s.searchContainer}>
        <Ionicons name="search" size={20} color="#999" />
        <TextInput
          style={s.searchInput}
          value={search}
          onChangeText={setSearch}
          placeholder="Buscar por O.S., cliente, local..."
          placeholderTextColor="#aaa"
          data-testid="archive-search-input"
        />
        {search ? (
          <TouchableOpacity onPress={() => setSearch('')} data-testid="archive-clear-search">
            <Ionicons name="close-circle" size={20} color="#999" />
          </TouchableOpacity>
        ) : null}
      </View>

      <ScrollView contentContainerStyle={s.scrollContent}>
        {filtered.length === 0 ? (
          <View style={s.empty}>
            <Ionicons name="folder-open-outline" size={64} color="#ccc" />
            <Text style={s.emptyText}>{search ? 'Nenhuma O.S. encontrada' : 'Nenhuma O.S. cadastrada'}</Text>
          </View>
        ) : (
          filtered.map(os => {
            const isExpanded = expandedOS === os.id;
            const hasDocuments = os.total_documents > 0;
            return (
              <View key={os.id} style={s.osCard} data-testid={`os-card-${os.id}`}>
                <TouchableOpacity
                  style={s.osHeader}
                  onPress={() => toggleOS(os.id)}
                  data-testid={`os-toggle-${os.id}`}
                >
                  <View style={s.osHeaderLeft}>
                    <View style={s.osBadge}>
                      <Text style={s.osBadgeText}>{os.os_number}</Text>
                    </View>
                    <View style={s.osInfo}>
                      <Text style={s.osClient}>{os.client}</Text>
                      <Text style={s.osLocation}>{os.location} - {os.service}</Text>
                    </View>
                  </View>
                  <View style={s.osHeaderRight}>
                    <View style={[s.countBadge, !hasDocuments && { backgroundColor: '#f5f5f5' }]}>
                      <Text style={[s.countText, !hasDocuments && { color: '#999' }]}>
                        {os.total_documents} doc{os.total_documents !== 1 ? 's' : ''}
                      </Text>
                    </View>
                    <Ionicons
                      name={isExpanded ? 'chevron-up' : 'chevron-down'}
                      size={22}
                      color="#1a237e"
                    />
                  </View>
                </TouchableOpacity>

                {isExpanded && (
                  <View style={s.osBody} data-testid={`os-body-${os.id}`}>
                    {os.total_documents === 0 ? (
                      <Text style={s.noDocsText}>Nenhum documento vinculado a esta O.S.</Text>
                    ) : (
                      <>
                        {renderDocSection('Timesheets', 'time-outline', os.timesheets, 'timesheet')}
                        {renderDocSection('Relatórios de Serviço', 'construct-outline', os.service_reports, 'report')}
                        {renderDocSection('Relatórios Diários', 'calendar-outline', os.daily_reports, 'report')}
                      </>
                    )}
                  </View>
                )}
              </View>
            );
          })
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: 16, paddingVertical: 12, backgroundColor: '#fff',
    borderBottomWidth: 1, borderBottomColor: '#e0e0e0',
  },
  backBtn: { padding: 8 },
  title: { fontSize: 20, fontWeight: '600', color: '#1a237e' },
  searchContainer: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff',
    marginHorizontal: 16, marginTop: 12, marginBottom: 4, borderRadius: 10,
    paddingHorizontal: 14, paddingVertical: 10, gap: 10,
    borderWidth: 1, borderColor: '#e0e0e0',
  },
  searchInput: { flex: 1, fontSize: 15, color: '#333', padding: 0 },
  scrollContent: { padding: 16, paddingTop: 8 },
  empty: { alignItems: 'center', paddingVertical: 64 },
  emptyText: { fontSize: 16, color: '#999', marginTop: 16, textAlign: 'center' },
  osCard: {
    backgroundColor: '#fff', borderRadius: 12, marginBottom: 12,
    overflow: 'hidden', elevation: 2,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.1, shadowRadius: 2,
  },
  osHeader: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    padding: 16,
  },
  osHeaderLeft: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  osBadge: {
    backgroundColor: '#1a237e', paddingHorizontal: 12, paddingVertical: 8,
    borderRadius: 8, marginRight: 12,
  },
  osBadgeText: { color: '#fff', fontWeight: '700', fontSize: 13 },
  osInfo: { flex: 1 },
  osClient: { fontSize: 16, fontWeight: '600', color: '#212121' },
  osLocation: { fontSize: 13, color: '#666', marginTop: 2 },
  osHeaderRight: { flexDirection: 'row', alignItems: 'center', gap: 8, marginLeft: 8 },
  countBadge: {
    backgroundColor: '#e3f2fd', paddingHorizontal: 10, paddingVertical: 4,
    borderRadius: 12,
  },
  countText: { fontSize: 12, fontWeight: '600', color: '#1a237e' },
  osBody: {
    borderTopWidth: 1, borderTopColor: '#eee', paddingHorizontal: 16,
    paddingVertical: 12,
  },
  noDocsText: { fontSize: 14, color: '#999', textAlign: 'center', paddingVertical: 16 },
  docSection: { marginBottom: 12 },
  docSectionHeader: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    marginBottom: 8, paddingBottom: 6,
    borderBottomWidth: 1, borderBottomColor: '#f0f0f0',
  },
  docSectionTitle: { fontSize: 14, fontWeight: '600', color: '#1a237e' },
  docCard: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    backgroundColor: '#fafafa', borderRadius: 8, padding: 12, marginBottom: 6,
    borderLeftWidth: 3, borderLeftColor: '#1a237e',
  },
  docInfo: { flex: 1 },
  docSupervisor: { fontSize: 14, fontWeight: '500', color: '#333' },
  docDate: { fontSize: 12, color: '#666', marginTop: 2 },
  docDateSmall: { fontSize: 11, color: '#999' },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 4 },
  statusBadge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4 },
  statusText: { fontSize: 11, fontWeight: '600' },
  docActions: { flexDirection: 'row', gap: 4, marginLeft: 8 },
  docActionBtn: { padding: 8 },
});
