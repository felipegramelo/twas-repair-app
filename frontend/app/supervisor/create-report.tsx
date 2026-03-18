import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, Alert, ActivityIndicator, Platform } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { serviceOrderAPI } from '../../services/api';
import { reportsAPI, externalSupervisorAPI } from '../../services/reportsApi';
import { ServiceOrder } from '../../types';
import { Picker } from '@react-native-picker/picker';

export default function CreateReportScreen() {
  const { user, ensureReportAuth } = useAuth();
  const router = useRouter();
  const { type } = useLocalSearchParams<{ type: string }>();
  const reportType = (type === 'service' ? 'service' : 'daily') as 'daily' | 'service';

  const [serviceOrders, setServiceOrders] = useState<ServiceOrder[]>([]);
  const [selectedOS, setSelectedOS] = useState('');
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      await ensureReportAuth();
      const osData = await serviceOrderAPI.getAll();
      setServiceOrders(osData);
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

    const os = serviceOrders.find(o => o.id === selectedOS);
    if (!os) return;

    setCreating(true);
    try {
      // Find matching supervisor on external API for compatibility
      let supervisorId = user?.id || 'local';
      let supervisorName = user?.name || 'Supervisor';
      try {
        const externalSups = await externalSupervisorAPI.getAll();
        const match = externalSups.find(s => s.email === user?.email);
        if (match) {
          supervisorId = match.id;
          supervisorName = match.name;
        }
      } catch (e) {
        console.warn('Não foi possível buscar supervisores externos:', e);
      }

      await reportsAPI.create({
        report_type: reportType,
        service_order_id: os.id,
        service_order_number: os.os_number,
        client: os.client,
        vessel: os.location,
        equipment: os.service,
        supervisor_id: supervisorId,
        supervisor_name: supervisorName,
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
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
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
            >
              <Picker.Item label="Selecione uma O.S..." value="" />
              {serviceOrders.map(os => (
                <Picker.Item
                  key={os.id}
                  label={`${os.os_number} - ${os.client} - ${os.service}`}
                  value={os.id}
                />
              ))}
            </Picker>
          </View>

          {selectedOS && (() => {
            const os = serviceOrders.find(o => o.id === selectedOS);
            if (!os) return null;
            return (
              <View style={styles.infoCard}>
                <Text style={styles.infoLabel}>Cliente: <Text style={styles.infoValue}>{os.client}</Text></Text>
                <Text style={styles.infoLabel}>Local: <Text style={styles.infoValue}>{os.location}</Text></Text>
                <Text style={styles.infoLabel}>Serviço: <Text style={styles.infoValue}>{os.service}</Text></Text>
              </View>
            );
          })()}

          <Text style={[styles.label, { marginTop: 20 }]}>Supervisor</Text>
          <View style={styles.supervisorInfo}>
            <Ionicons name="person-circle-outline" size={24} color="#1a237e" />
            <Text style={styles.supervisorName}>{user?.name}</Text>
          </View>

          <Text style={[styles.label, { marginTop: 20 }]}>Tipo de Relatório</Text>
          <View style={styles.typeIndicator}>
            <Ionicons
              name={reportType === 'service' ? 'construct-outline' : 'calendar-outline'}
              size={20}
              color={reportType === 'service' ? '#1565c0' : '#2e7d32'}
            />
            <Text style={[styles.typeText, { color: reportType === 'service' ? '#1565c0' : '#2e7d32' }]}>
              {reportType === 'service' ? 'Relatório de Serviço' : 'Relatório Diário'}
            </Text>
          </View>
        </View>

        <TouchableOpacity
          style={[styles.createButton, creating && styles.createButtonDisabled]}
          onPress={handleCreate}
          disabled={creating}
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
  supervisorInfo: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#f8f9fa', padding: 12, borderRadius: 8, borderWidth: 1, borderColor: '#e0e0e0' },
  supervisorName: { fontSize: 15, fontWeight: '500', color: '#333' },
  typeIndicator: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: '#f8f9fa', padding: 12, borderRadius: 8, borderWidth: 1, borderColor: '#e0e0e0' },
  typeText: { fontSize: 15, fontWeight: '600' },
  createButton: { backgroundColor: '#1a237e', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', padding: 16, borderRadius: 12, gap: 8 },
  createButtonDisabled: { opacity: 0.6 },
  createButtonText: { color: '#fff', fontSize: 18, fontWeight: '600' },
});
