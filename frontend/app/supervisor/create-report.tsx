import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, TextInput, ActivityIndicator, Platform } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { serviceOrderAPI, reportAPI } from '../../services/api';
import { ServiceOrder } from '../../types';

export default function CreateReportScreen() {
  const { user } = useAuth();
  const router = useRouter();
  const { type } = useLocalSearchParams<{ type: string }>();
  const reportType = (type === 'service' ? 'service' : 'daily') as 'daily' | 'service';

  const [serviceOrders, setServiceOrders] = useState<ServiceOrder[]>([]);
  const [selectedOS, setSelectedOS] = useState('');
  const [periodoInicio, setPeriodoInicio] = useState('');
  const [periodoFim, setPeriodoFim] = useState('');
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showOSDropdown, setShowOSDropdown] = useState(false);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const osData = await serviceOrderAPI.getAll();
      setServiceOrders(osData);
    } catch (error) {
      showMsg('Erro ao carregar ordens de serviço.');
    } finally {
      setLoading(false);
    }
  };

  const showMsg = (msg: string) => {
    if (Platform.OS === 'web') window.alert(msg);
  };

  const handleCreate = async () => {
    if (!selectedOS) { showMsg('Selecione uma Ordem de Serviço'); return; }
    if (!periodoInicio || !periodoFim) { showMsg('Preencha as datas de início e fim'); return; }

    setCreating(true);
    try {
      const result = await reportAPI.create({
        report_type: reportType,
        os_id: selectedOS,
        periodo_inicio: periodoInicio,
        periodo_fim: periodoFim,
        executado_por: user?.name || '',
      });
      const label = reportType === 'service' ? 'Relatório de Serviço' : 'Relatório Diário';
      showMsg(`${label} criado com sucesso!`);
      router.push('/supervisor');
    } catch (error: any) {
      const detail = error.response?.data?.detail || error.message || 'Erro desconhecido';
      showMsg('Erro ao criar relatório: ' + detail);
    } finally {
      setCreating(false);
    }
  };

  // Convert HTML date (YYYY-MM-DD) to DD/MM/YYYY
  const htmlDateToBR = (htmlDate: string): string => {
    if (!htmlDate) return '';
    const [y, m, d] = htmlDate.split('-');
    return `${d}/${m}/${y}`;
  };

  // Convert DD/MM/YYYY to YYYY-MM-DD for HTML input
  const brDateToHtml = (brDate: string): string => {
    if (!brDate || brDate.length < 10) return '';
    const [d, m, y] = brDate.split('/');
    return `${y}-${m}-${d}`;
  };

  const selectedOSData = serviceOrders.find(o => o.id === selectedOS);

  if (loading) {
    return <SafeAreaView style={styles.container}><ActivityIndicator size="large" color="#1a237e" style={{ marginTop: 100 }} /></SafeAreaView>;
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.innerContainer}>
        <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={true}>
          <View style={styles.headerRow}>
            <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
              <Ionicons name="arrow-back" size={24} color="#1a237e" />
            </TouchableOpacity>
            <Text style={styles.title}>
              {reportType === 'service' ? 'Novo Relatório de Serviço' : 'Novo Relatório Diário'}
            </Text>
          </View>

          <View style={styles.formSection}>
            {/* OS Selection */}
            <Text style={styles.label}>Ordem de Serviço *</Text>
            {Platform.OS === 'web' ? (
              <select
                value={selectedOS}
                onChange={(e: any) => setSelectedOS(e.target.value)}
                style={{
                  width: '100%', padding: 12, fontSize: 15, borderRadius: 8,
                  border: '1px solid #e0e0e0', backgroundColor: '#f8f9fa',
                  color: selectedOS ? '#333' : '#999', cursor: 'pointer',
                }}
              >
                <option value="">Selecione uma O.S...</option>
                {serviceOrders.map(os => (
                  <option key={os.id} value={os.id}>{os.os_number} - {os.client} - {os.service}</option>
                ))}
              </select>
            ) : (
              <TouchableOpacity style={styles.dropdownBtn} onPress={() => setShowOSDropdown(!showOSDropdown)}>
                <Text style={[styles.dropdownText, !selectedOS && { color: '#999' }]}>
                  {selectedOSData ? `${selectedOSData.os_number} - ${selectedOSData.client}` : 'Selecione uma O.S...'}
                </Text>
                <Ionicons name="chevron-down" size={18} color="#666" />
              </TouchableOpacity>
            )}

            {/* OS Info Card */}
            {selectedOSData && (
              <View style={styles.infoCard}>
                <Text style={styles.infoLabel}>Cliente: <Text style={styles.infoValue}>{selectedOSData.client}</Text></Text>
                <Text style={styles.infoLabel}>Local: <Text style={styles.infoValue}>{selectedOSData.location}</Text></Text>
                <Text style={styles.infoLabel}>Serviço: <Text style={styles.infoValue}>{selectedOSData.service}</Text></Text>
              </View>
            )}

            {/* Period with Calendar */}
            <Text style={[styles.label, { marginTop: 20 }]}>Período *</Text>
            <View style={styles.dateRow}>
              <View style={styles.dateField}>
                <Text style={styles.dateLabel}>Data Início</Text>
                {Platform.OS === 'web' ? (
                  <input
                    type="date"
                    value={brDateToHtml(periodoInicio)}
                    onChange={(e: any) => setPeriodoInicio(htmlDateToBR(e.target.value))}
                    style={{
                      width: '100%', padding: 12, fontSize: 15, borderRadius: 8,
                      border: '1px solid #e0e0e0', backgroundColor: '#f8f9fa',
                      textAlign: 'center', cursor: 'pointer', boxSizing: 'border-box',
                    }}
                  />
                ) : (
                  <TextInput style={styles.dateInput} value={periodoInicio} placeholder="DD/MM/AAAA" keyboardType="numeric" maxLength={10}
                    onChangeText={(t) => {
                      const c = t.replace(/\D/g, '');
                      let f = c;
                      if (c.length >= 3 && c.length <= 4) f = c.slice(0,2)+'/'+c.slice(2);
                      else if (c.length >= 5) f = c.slice(0,2)+'/'+c.slice(2,4)+'/'+c.slice(4,8);
                      setPeriodoInicio(f);
                    }}
                  />
                )}
              </View>
              <View style={styles.dateField}>
                <Text style={styles.dateLabel}>Data Fim</Text>
                {Platform.OS === 'web' ? (
                  <input
                    type="date"
                    value={brDateToHtml(periodoFim)}
                    onChange={(e: any) => setPeriodoFim(htmlDateToBR(e.target.value))}
                    style={{
                      width: '100%', padding: 12, fontSize: 15, borderRadius: 8,
                      border: '1px solid #e0e0e0', backgroundColor: '#f8f9fa',
                      textAlign: 'center', cursor: 'pointer', boxSizing: 'border-box',
                    }}
                  />
                ) : (
                  <TextInput style={styles.dateInput} value={periodoFim} placeholder="DD/MM/AAAA" keyboardType="numeric" maxLength={10}
                    onChangeText={(t) => {
                      const c = t.replace(/\D/g, '');
                      let f = c;
                      if (c.length >= 3 && c.length <= 4) f = c.slice(0,2)+'/'+c.slice(2);
                      else if (c.length >= 5) f = c.slice(0,2)+'/'+c.slice(2,4)+'/'+c.slice(4,8);
                      setPeriodoFim(f);
                    }}
                  />
                )}
              </View>
            </View>

            {/* Supervisor */}
            <Text style={[styles.label, { marginTop: 20 }]}>Supervisor</Text>
            <View style={styles.supervisorInfo}>
              <Ionicons name="person-circle-outline" size={24} color="#1a237e" />
              <Text style={styles.supervisorName}>{user?.name}</Text>
            </View>

            {/* Report Type */}
            <Text style={[styles.label, { marginTop: 20 }]}>Tipo de Relatório</Text>
            <View style={styles.typeIndicator}>
              <Ionicons name={reportType === 'service' ? 'construct-outline' : 'calendar-outline'} size={20} color={reportType === 'service' ? '#1565c0' : '#2e7d32'} />
              <Text style={[styles.typeText, { color: reportType === 'service' ? '#1565c0' : '#2e7d32' }]}>
                {reportType === 'service' ? 'Relatório de Serviço' : 'Relatório Diário'}
              </Text>
            </View>
          </View>

          <TouchableOpacity
            style={[styles.createButton, creating && styles.createButtonDisabled]}
            onPress={handleCreate}
            disabled={creating}
            data-testid="create-report-btn"
          >
            {creating ? <ActivityIndicator color="#fff" /> : (
              <>
                <Ionicons name="checkmark-circle" size={24} color="#fff" />
                <Text style={styles.createButtonText}>Criar Relatório</Text>
              </>
            )}
          </TouchableOpacity>
        </ScrollView>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  innerContainer: { flex: 1, ...(Platform.OS === 'web' ? { height: '100vh', overflow: 'hidden' } : {}) } as any,
  scrollContent: { padding: 16, paddingBottom: 32 },
  headerRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 24, gap: 12 },
  backButton: { padding: 8 },
  title: { fontSize: 22, fontWeight: 'bold', color: '#1a237e', flex: 1 },
  formSection: { backgroundColor: '#fff', borderRadius: 12, padding: 20, marginBottom: 24, ...(Platform.OS === 'web' ? { boxShadow: '0 1px 3px rgba(0,0,0,0.1)' } : { elevation: 2 }) } as any,
  label: { fontSize: 14, fontWeight: '600', color: '#333', marginBottom: 8 },
  dropdownBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', backgroundColor: '#f8f9fa', borderRadius: 8, borderWidth: 1, borderColor: '#e0e0e0', padding: 12 },
  dropdownText: { fontSize: 15, color: '#333', flex: 1 },
  infoCard: { backgroundColor: '#e3f2fd', borderRadius: 8, padding: 12, marginTop: 12 },
  infoLabel: { fontSize: 13, color: '#666', marginBottom: 4 },
  infoValue: { fontWeight: '600', color: '#1a237e' },
  dateRow: { flexDirection: 'row', gap: 12 },
  dateField: { flex: 1 },
  dateLabel: { fontSize: 12, color: '#666', marginBottom: 4 },
  dateInput: { backgroundColor: '#f8f9fa', borderRadius: 8, borderWidth: 1, borderColor: '#e0e0e0', padding: 12, fontSize: 15, textAlign: 'center' },
  supervisorInfo: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#f8f9fa', padding: 12, borderRadius: 8, borderWidth: 1, borderColor: '#e0e0e0' },
  supervisorName: { fontSize: 15, fontWeight: '500', color: '#333' },
  typeIndicator: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#f8f9fa', padding: 12, borderRadius: 8, borderWidth: 1, borderColor: '#e0e0e0' },
  typeText: { fontSize: 15, fontWeight: '600' },
  createButton: { backgroundColor: '#1a237e', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', padding: 16, borderRadius: 12, gap: 8 },
  createButtonDisabled: { opacity: 0.6 },
  createButtonText: { color: '#fff', fontSize: 18, fontWeight: '600' },
});
