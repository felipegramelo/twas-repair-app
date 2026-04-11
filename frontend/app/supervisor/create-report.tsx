import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, TextInput, ActivityIndicator, Platform, Alert, Modal } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { serviceOrderAPI, reportAPI } from '../../services/api';
import { ServiceOrder } from '../../types';

const WEEKDAYS = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
const MONTHS = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];

function InlineCalendar({ onSelect, selectedDate }: { onSelect: (date: string) => void; selectedDate?: string }) {
  const [currentMonth, setCurrentMonth] = useState(new Date().getMonth());
  const [currentYear, setCurrentYear] = useState(new Date().getFullYear());
  const days = new Date(currentYear, currentMonth + 1, 0).getDate();
  const firstDay = new Date(currentYear, currentMonth, 1).getDay();
  const allCells = [...Array(firstDay).fill(null), ...Array.from({ length: days }, (_, i) => i + 1)];

  const isSelected = (day: number) => {
    if (!selectedDate) return false;
    const formatted = `${String(day).padStart(2, '0')}/${String(currentMonth + 1).padStart(2, '0')}/${currentYear}`;
    return formatted === selectedDate;
  };

  return (
    <View style={{ backgroundColor: '#f8f9fa', borderRadius: 12, padding: 12, marginTop: 8, borderWidth: 1, borderColor: '#e0e0e0' }}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <TouchableOpacity onPress={() => { if (currentMonth === 0) { setCurrentMonth(11); setCurrentYear(y => y - 1); } else setCurrentMonth(m => m - 1); }}>
          <Ionicons name="chevron-back" size={22} color="#000000" />
        </TouchableOpacity>
        <Text style={{ fontSize: 16, fontWeight: '600', color: '#000000' }}>{MONTHS[currentMonth]} {currentYear}</Text>
        <TouchableOpacity onPress={() => { if (currentMonth === 11) { setCurrentMonth(0); setCurrentYear(y => y + 1); } else setCurrentMonth(m => m + 1); }}>
          <Ionicons name="chevron-forward" size={22} color="#000000" />
        </TouchableOpacity>
      </View>
      <View style={{ flexDirection: 'row', justifyContent: 'space-around', marginBottom: 4 }}>
        {WEEKDAYS.map(d => <Text key={d} style={{ width: 36, textAlign: 'center', fontSize: 11, fontWeight: '600', color: '#666' }}>{d}</Text>)}
      </View>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
        {allCells.map((cell, idx) => (
          <TouchableOpacity
            key={idx}
            style={{
              width: '14.28%' as any, height: 36, justifyContent: 'center', alignItems: 'center',
              borderRadius: 18,
              backgroundColor: cell && isSelected(cell) ? '#000000' : 'transparent',
            }}
            onPress={() => cell && onSelect(`${String(cell).padStart(2, '0')}/${String(currentMonth + 1).padStart(2, '0')}/${currentYear}`)}
            disabled={!cell}
          >
            <Text style={{ fontSize: 15, color: cell ? (isSelected(cell) ? '#fff' : '#212121') : 'transparent', fontWeight: cell && isSelected(cell) ? '700' : '400' }}>{cell || ''}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}

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
  const [osModalVisible, setOsModalVisible] = useState(false);
  const [showStartCalendar, setShowStartCalendar] = useState(false);
  const [showEndCalendar, setShowEndCalendar] = useState(false);

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
    else Alert.alert('Aviso', msg);
  };

  const handleCreate = async () => {
    if (!selectedOS) { showMsg('Selecione uma Ordem de Serviço'); return; }
    if (!periodoInicio || (reportType !== 'daily' && !periodoFim)) { showMsg('Preencha a data de início' + (reportType !== 'daily' ? ' e fim' : '')); return; }

    setCreating(true);
    try {
      await reportAPI.create({
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

  const htmlDateToBR = (htmlDate: string): string => {
    if (!htmlDate) return '';
    const [y, m, d] = htmlDate.split('-');
    return `${d}/${m}/${y}`;
  };

  const brDateToHtml = (brDate: string): string => {
    if (!brDate || brDate.length < 10) return '';
    const [d, m, y] = brDate.split('/');
    return `${y}-${m}-${d}`;
  };

  const selectedOSData = serviceOrders.find(o => o.id === selectedOS);

  if (loading) {
    return <SafeAreaView style={styles.container}><ActivityIndicator size="large" color="#000000" style={{ marginTop: 100 }} /></SafeAreaView>;
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.innerContainer}>
        <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={true} keyboardShouldPersistTaps="handled">
          <View style={styles.headerRow}>
            <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
              <Ionicons name="arrow-back" size={24} color="#000000" />
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
              <TouchableOpacity style={styles.dropdownBtn} onPress={() => setOsModalVisible(true)} data-testid="select-os-native-btn">
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

            {/* Period */}
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
                  <TouchableOpacity
                    style={styles.dateInput}
                    onPress={() => { setShowStartCalendar(!showStartCalendar); setShowEndCalendar(false); }}
                    data-testid="date-start-btn"
                  >
                    <Text style={{ fontSize: 15, color: periodoInicio ? '#333' : '#999', textAlign: 'center' }}>
                      {periodoInicio || 'DD/MM/AAAA'}
                    </Text>
                    <Ionicons name={showStartCalendar ? 'chevron-up' : 'calendar'} size={18} color="#000000" style={{ position: 'absolute', right: 12 }} />
                  </TouchableOpacity>
                )}
                {showStartCalendar && Platform.OS !== 'web' && (
                  <InlineCalendar
                    selectedDate={periodoInicio}
                    onSelect={(date) => { setPeriodoInicio(date); setShowStartCalendar(false); }}
                  />
                )}
              </View>
              {reportType !== 'daily' && (
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
                  <TouchableOpacity
                    style={styles.dateInput}
                    onPress={() => { setShowEndCalendar(!showEndCalendar); setShowStartCalendar(false); }}
                    data-testid="date-end-btn"
                  >
                    <Text style={{ fontSize: 15, color: periodoFim ? '#333' : '#999', textAlign: 'center' }}>
                      {periodoFim || 'DD/MM/AAAA'}
                    </Text>
                    <Ionicons name={showEndCalendar ? 'chevron-up' : 'calendar'} size={18} color="#000000" style={{ position: 'absolute', right: 12 }} />
                  </TouchableOpacity>
                )}
                {showEndCalendar && Platform.OS !== 'web' && (
                  <InlineCalendar
                    selectedDate={periodoFim}
                    onSelect={(date) => { setPeriodoFim(date); setShowEndCalendar(false); }}
                  />
                )}
              </View>
              )}
            </View>

            {/* Supervisor */}
            <Text style={[styles.label, { marginTop: 20 }]}>Supervisor</Text>
            <View style={styles.supervisorInfo}>
              <Ionicons name="person-circle-outline" size={24} color="#000000" />
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

      {/* Native OS Selection Modal */}
      <Modal visible={osModalVisible} animationType="slide" transparent onRequestClose={() => setOsModalVisible(false)}>
        <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', padding: 16 }}>
          <View style={{ backgroundColor: '#fff', borderRadius: 16, padding: 24, maxHeight: '80%' }}>
            <Text style={{ fontSize: 20, fontWeight: '600', color: '#000000', marginBottom: 16 }}>Selecionar Ordem de Serviço</Text>
            <ScrollView style={{ maxHeight: 400 }}>
              {serviceOrders.map(os => (
                <TouchableOpacity key={os.id} style={{ padding: 14, borderBottomWidth: 1, borderBottomColor: '#e0e0e0' }} onPress={() => { setSelectedOS(os.id); setOsModalVisible(false); }}>
                  <Text style={{ fontSize: 16, fontWeight: '600', color: '#212121' }}>{os.os_number}</Text>
                  <Text style={{ fontSize: 14, color: '#666', marginTop: 4 }}>{os.client}</Text>
                  <Text style={{ fontSize: 13, color: '#999', marginTop: 2 }}>{os.service}</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
            <TouchableOpacity style={{ backgroundColor: '#f5f5f5', height: 48, borderRadius: 8, justifyContent: 'center', alignItems: 'center', marginTop: 16 }} onPress={() => setOsModalVisible(false)}>
              <Text style={{ fontSize: 16, fontWeight: '600', color: '#666' }}>Fechar</Text>
            </TouchableOpacity>
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
  headerRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 24, gap: 12 },
  backButton: { padding: 8 },
  title: { fontSize: 22, fontWeight: 'bold', color: '#000000', flex: 1 },
  formSection: { backgroundColor: '#fff', borderRadius: 12, padding: 20, marginBottom: 24, ...(Platform.OS === 'web' ? { boxShadow: '0 1px 3px rgba(0,0,0,0.1)' } : { elevation: 2 }) } as any,
  label: { fontSize: 14, fontWeight: '600', color: '#333', marginBottom: 8 },
  dropdownBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', backgroundColor: '#f8f9fa', borderRadius: 8, borderWidth: 1, borderColor: '#e0e0e0', padding: 12 },
  dropdownText: { fontSize: 15, color: '#333', flex: 1 },
  infoCard: { backgroundColor: '#f0f0f0', borderRadius: 8, padding: 12, marginTop: 12 },
  infoLabel: { fontSize: 13, color: '#666', marginBottom: 4 },
  infoValue: { fontWeight: '600', color: '#000000' },
  dateRow: { flexDirection: 'row', gap: 12 },
  dateField: { flex: 1 },
  dateLabel: { fontSize: 12, color: '#666', marginBottom: 4 },
  dateInput: { backgroundColor: '#f8f9fa', borderRadius: 8, borderWidth: 1, borderColor: '#e0e0e0', padding: 12, fontSize: 15, textAlign: 'center', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', position: 'relative' } as any,
  supervisorInfo: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#f8f9fa', padding: 12, borderRadius: 8, borderWidth: 1, borderColor: '#e0e0e0' },
  supervisorName: { fontSize: 15, fontWeight: '500', color: '#333' },
  typeIndicator: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#f8f9fa', padding: 12, borderRadius: 8, borderWidth: 1, borderColor: '#e0e0e0' },
  typeText: { fontSize: 15, fontWeight: '600' },
  createButton: { backgroundColor: '#000000', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', padding: 16, borderRadius: 12, gap: 8 },
  createButtonDisabled: { opacity: 0.6 },
  createButtonText: { color: '#fff', fontSize: 18, fontWeight: '600' },
});
