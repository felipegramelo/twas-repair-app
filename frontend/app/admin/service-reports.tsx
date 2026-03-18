import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, FlatList, Alert, ActivityIndicator, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '../../contexts/AuthContext';
import { reportsAPI } from '../../services/reportsApi';
import { Report } from '../../types';

export default function ServiceReportsScreen() {
  const router = useRouter();
  const { ensureReportAuth } = useAuth();
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    try {
      await ensureReportAuth();
      const all = await reportsAPI.getAll();
      setReports(all.filter(r => r.report_type === 'service'));
    } catch (error) {
      console.error('Erro ao carregar relatórios:', error);
      Alert.alert('Erro', 'Erro ao carregar relatórios de serviço');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenPDF = async (report: Report) => {
    try {
      if (Platform.OS === 'web') {
        const blob = await reportsAPI.downloadPDF(report.id);
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank');
      } else {
        Alert.alert('Info', 'PDF disponível apenas na versão web.');
      }
    } catch (error) {
      if (Platform.OS === 'web') window.alert('Erro ao abrir PDF do relatório');
      else Alert.alert('Erro', 'Erro ao abrir PDF');
    }
  };

  const handleDownloadPDF = async (report: Report) => {
    try {
      if (Platform.OS === 'web') {
        const blob = await reportsAPI.downloadPDF(report.id);
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `relatorio_servico_${report.service_order_number}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        window.alert('PDF baixado com sucesso!');
      } else {
        Alert.alert('Info', 'Download disponível apenas na versão web.');
      }
    } catch (error) {
      if (Platform.OS === 'web') window.alert('Erro ao baixar PDF');
      else Alert.alert('Erro', 'Erro ao baixar PDF');
    }
  };

  const formatDate = (dateStr: string) => {
    try { return new Date(dateStr).toLocaleDateString('pt-BR'); }
    catch { return dateStr; }
  };

  const getStatusLabel = (s: string) => {
    switch (s) { case 'draft': return 'Rascunho'; case 'completed': return 'Concluído'; case 'approved': return 'Aprovado'; default: return s; }
  };
  const getStatusColor = (s: string) => {
    switch (s) { case 'draft': return '#ff9800'; case 'completed': return '#4caf50'; case 'approved': return '#2196f3'; default: return '#999'; }
  };

  const renderReport = ({ item }: { item: Report }) => (
    <View style={styles.card} data-testid={`service-report-card-${item.id}`}>
      <View style={styles.topRow}>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{item.service_order_number}</Text>
        </View>
        <View style={styles.actions}>
          <TouchableOpacity onPress={() => handleOpenPDF(item)} style={styles.actionBtn} data-testid={`sr-pdf-${item.id}`}>
            <Ionicons name="document-text-outline" size={20} color="#1a237e" />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => handleDownloadPDF(item)} style={styles.actionBtn} data-testid={`sr-download-${item.id}`}>
            <Ionicons name="download-outline" size={20} color="#1a237e" />
          </TouchableOpacity>
        </View>
      </View>
      <View style={styles.cardInfo}>
        <Text style={styles.cardTitle}>{item.client}</Text>
        <Text style={styles.cardSubtitle}>{item.vessel} - {item.equipment}</Text>
        <Text style={styles.cardMeta}>{item.supervisor_name}</Text>
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
          <TouchableOpacity onPress={() => router.back()} style={styles.backBtn} data-testid="back-btn">
            <Ionicons name="arrow-back" size={24} color="#1a237e" />
          </TouchableOpacity>
          <Text style={styles.title}>Relatórios de Serviço</Text>
        </View>

        {loading ? (
          <ActivityIndicator size="large" color="#1a237e" style={{ marginTop: 48 }} />
        ) : reports.length > 0 ? (
          <FlatList data={reports} renderItem={renderReport} keyExtractor={item => item.id} scrollEnabled={false} />
        ) : (
          <View style={styles.empty}>
            <Ionicons name="construct-outline" size={48} color="#ccc" />
            <Text style={styles.emptyText}>Nenhum relatório de serviço encontrado</Text>
          </View>
        )}
      </ScrollView>
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
});
