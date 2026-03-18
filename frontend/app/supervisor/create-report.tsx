import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, Alert, ActivityIndicator, Platform } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { reportsAPI, externalServiceOrderAPI, externalSupervisorAPI } from '../../services/reportsApi';
import { ExternalServiceOrder, ExternalSupervisor } from '../../types';
import { Picker } from '@react-native-picker/picker';

export default function CreateReportScreen() {
  const { user } = useAuth();
  const router = useRouter();
  const { type } = useLocalSearchParams<{ type: string }>();
  const reportType = (type === 'service' ? 'service' : 'daily') as 'daily' | 'service';

  const [serviceOrders, setServiceOrders] = useState<ExternalServiceOrder[]>([]);
  const [supervisors, setSupervisors] = useState<ExternalSupervisor[]>([]);
  const [selectedOS, setSelectedOS] = useState('');
  const [selectedSupervisor, setSelectedSupervisor] = useState('');
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [osData, supData] = await Promise.all([
        externalServiceOrderAPI.getAll(),
        externalSupervisorAPI.getAll(),
      ]);
      setServiceOrders(osData.filter(o => o.status === 'active'));
      setSupervisors(supData);
      // Auto-select supervisor by email match
      const match = supData.find(s => s.email === user?.email);
      if (match) setSelectedSupervisor(match.id);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
      Alert.alert('Erro', 'Erro ao carregar dados. Verifique sua conexão.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!selectedOS) {
      Alert.alert('Erro', 'Selecione uma Ordem de Serviço');
      return;
    }
    if (!selectedSupervisor) {
      Alert.alert('Erro', 'Selecione um Supervisor');
      return;
    }

    const os = serviceOrders.find(o => o.id === selectedOS);
    const sup = supervisors.find(s => s.id === selectedSupervisor);
    if (!os || !sup) return;

    setCreating(true);
    try {
      await reportsAPI.create({
        report_type: reportType,
        service_order_id: os.id,
        service_order_number: os.order_number,
        client: os.client,
        vessel: os.vessel,
        equipment: os.equipment,
        supervisor_id: sup.id,
        supervisor_name: sup.name,
      });
      Alert.alert('Sucesso', `${reportType === 'service' ? 'Relatório de Serviço' : 'Relatório Diário'} criado com sucesso!`);
      router.back();
    } catch (error: any) {
      console.error('Erro ao criar relatório:', error);
      Alert.alert('Erro', 'Erro ao criar relatório: ' + (error.response?.data?.detail || error.message || ''));
    } finally {
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <ActivityIndicator size="large" color="#1a237e" style={{ marginTop: 100 }} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.headerRow}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton} data-testid="back-btn">
            <Ionicons name="arrow-back" size={24} color="#1a237e" />
          </TouchableOpacity>
          <Text style={styles.title}>
            {reportType === 'service' ? 'Novo Relatório de Serviço' : 'Novo Relatório Diário'}
          </Text>
        </View>

        <View style={styles.formSection}>
          <Text style={styles.label}>Ordem de Serviço *</Text>
          <View style={styles.pickerContainer}>
            <Picker
              selectedValue={selectedOS}
              onValueChange={setSelectedOS}
              style={styles.picker}
              data-testid="os-picker"
            >
              <Picker.Item label="Selecione uma O.S..." value="" />
              {serviceOrders.map(os => (
                <Picker.Item
                  key={os.id}
                  label={`${os.order_number} - ${os.client} - ${os.vessel}`}
                  value={os.id}
                />
              ))}
            </Picker>
          </View>

          {selectedOS && (() => {
            const os = serviceOrders.find(o => o.id === selectedOS);
            if (!os) return null;
            return (
              <View style={styles.infoCard} data-testid="selected-os-info">
                <Text style={styles.infoLabel}>Cliente: <Text style={styles.infoValue}>{os.client}</Text></Text>
                <Text style={styles.infoLabel}>Embarcação: <Text style={styles.infoValue}>{os.vessel}</Text></Text>
                <Text style={styles.infoLabel}>Equipamento: <Text style={styles.infoValue}>{os.equipment}</Text></Text>
              </View>
            );
          })()}

          <Text style={[styles.label, { marginTop: 20 }]}>Supervisor *</Text>
          <View style={styles.pickerContainer}>
            <Picker
              selectedValue={selectedSupervisor}
              onValueChange={setSelectedSupervisor}
              style={styles.picker}
              data-testid="supervisor-picker"
            >
              <Picker.Item label="Selecione um supervisor..." value="" />
              {supervisors.map(sup => (
                <Picker.Item key={sup.id} label={sup.name} value={sup.id} />
              ))}
            </Picker>
          </View>

          <Text style={[styles.label, { marginTop: 20 }]}>Tipo de Relatório</Text>
          <View style={styles.typeBadge}>
            <Ionicons
              name={reportType === 'service' ? 'construct-outline' : 'calendar-outline'}
              size={20}
              color="#1a237e"
            />
            <Text style={styles.typeText}>
              {reportType === 'service' ? 'Relatório de Serviço' : 'Relatório Diário'}
            </Text>
          </View>
        </View>

        <TouchableOpacity
          style={[styles.createButton, creating && styles.createButtonDisabled]}
          onPress={handleCreate}
          disabled={creating}
          data-testid="submit-create-report"
        >
          {creating ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <Ionicons name="checkmark-circle" size={24} color="#fff" />
              <Text style={styles.createButtonText}>Criar Relatório</Text>
            </>
          )}
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  scrollContent: { padding: 16 },
  headerRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 24, gap: 12 },
  backButton: { padding: 8 },
  title: { fontSize: 22, fontWeight: 'bold', color: '#1a237e', flex: 1 },
  formSection: { backgroundColor: '#fff', borderRadius: 12, padding: 20, marginBottom: 24 },
  label: { fontSize: 14, fontWeight: '600', color: '#333', marginBottom: 8 },
  pickerContainer: { backgroundColor: '#f8f9fa', borderRadius: 8, borderWidth: 1, borderColor: '#e0e0e0', overflow: 'hidden' },
  picker: { height: 50 },
  infoCard: { backgroundColor: '#e3f2fd', borderRadius: 8, padding: 12, marginTop: 12 },
  infoLabel: { fontSize: 13, color: '#666', marginBottom: 4 },
  infoValue: { fontWeight: '600', color: '#1a237e' },
  typeBadge: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#e3f2fd', padding: 12, borderRadius: 8 },
  typeText: { fontSize: 15, fontWeight: '600', color: '#1a237e' },
  createButton: { backgroundColor: '#1a237e', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', padding: 16, borderRadius: 12, gap: 8 },
  createButtonDisabled: { opacity: 0.6 },
  createButtonText: { color: '#fff', fontSize: 18, fontWeight: '600' },
});
