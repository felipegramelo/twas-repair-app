import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, TextInput, Alert, ActivityIndicator, Platform } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { reportAPI } from '../../services/api';

export default function EditReportScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [report, setReport] = useState<any>(null);

  // Editable fields
  const [periodo, setPeriodo] = useState('');
  const [executadoPor, setExecutadoPor] = useState('');
  const [introduction, setIntroduction] = useState('');
  const [equipmentDesc, setEquipmentDesc] = useState('');
  const [objective, setObjective] = useState('');
  const [serviceDescription, setServiceDescription] = useState('');
  const [observations, setObservations] = useState('');

  useEffect(() => {
    loadReport();
  }, []);

  const loadReport = async () => {
    try {
      const data = await reportAPI.getById(id!);
      setReport(data);
      setPeriodo(data.periodo || '');
      setExecutadoPor(data.executado_por || '');
      setIntroduction(data.introduction || '');
      setEquipmentDesc(data.equipment_desc || '');
      setObjective(data.objective || '');
      setServiceDescription(data.service_description || '');
      setObservations(data.observations || '');
    } catch (error) {
      console.error('Erro ao carregar relatório:', error);
      Alert.alert('Erro', 'Erro ao carregar relatório');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await reportAPI.update(id!, {
        periodo,
        executado_por: executadoPor,
        introduction,
        equipment_desc: equipmentDesc,
        objective,
        service_description: serviceDescription,
        observations,
      });
      if (Platform.OS === 'web') {
        window.alert('Relatório salvo com sucesso!');
      } else {
        Alert.alert('Sucesso', 'Relatório salvo com sucesso!');
      }
      router.back();
    } catch (error: any) {
      console.error('Erro ao salvar:', error);
      Alert.alert('Erro', 'Erro ao salvar: ' + (error.message || ''));
    } finally {
      setSaving(false);
    }
  };

  const handleOpenPDF = async () => {
    try {
      if (Platform.OS === 'web') {
        const blob = await reportAPI.downloadPDF(id!);
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank');
      }
    } catch (error) {
      if (Platform.OS === 'web') window.alert('Erro ao gerar PDF');
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <ActivityIndicator size="large" color="#1a237e" style={{ marginTop: 100 }} />
      </SafeAreaView>
    );
  }

  if (!report) {
    return (
      <SafeAreaView style={styles.container}>
        <Text style={{ padding: 20, textAlign: 'center' }}>Relatório não encontrado</Text>
      </SafeAreaView>
    );
  }

  const isService = report.report_type === 'service';

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.headerRow}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color="#1a237e" />
          </TouchableOpacity>
          <Text style={styles.title} numberOfLines={1}>
            {isService ? 'Editar Rel. Serviço' : 'Editar Rel. Diário'}
          </Text>
          <TouchableOpacity onPress={handleOpenPDF} style={styles.pdfButton}>
            <Ionicons name="document-text-outline" size={22} color="#1a237e" />
          </TouchableOpacity>
        </View>

        {/* Report Info (read-only) */}
        <View style={styles.infoCard}>
          <View style={styles.infoBadge}>
            <Text style={styles.infoBadgeText}>{report.os_number}</Text>
          </View>
          <Text style={styles.infoClient}>{report.client}</Text>
          <Text style={styles.infoLocation}>{report.location} - {report.service}</Text>
        </View>

        {/* Editable Fields */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Informações Gerais</Text>

          <Text style={styles.label}>Período</Text>
          <TextInput
            style={styles.input}
            value={periodo}
            onChangeText={setPeriodo}
            placeholder="Ex: 10/01 a 15/01/2026"
          />

          <Text style={styles.label}>Executado Por</Text>
          <TextInput
            style={styles.input}
            value={executadoPor}
            onChangeText={setExecutadoPor}
            placeholder="Ex: TWAS REPAIR"
          />
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>1. Introdução</Text>
          <TextInput
            style={styles.textarea}
            value={introduction}
            onChangeText={setIntroduction}
            placeholder="Descreva a introdução do relatório..."
            multiline
            textAlignVertical="top"
          />
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>2. Equipamentos</Text>
          <TextInput
            style={styles.textarea}
            value={equipmentDesc}
            onChangeText={setEquipmentDesc}
            placeholder="Descreva os equipamentos utilizados..."
            multiline
            textAlignVertical="top"
          />
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>3. Objetivo</Text>
          <TextInput
            style={styles.textarea}
            value={objective}
            onChangeText={setObjective}
            placeholder="Descreva o objetivo do serviço..."
            multiline
            textAlignVertical="top"
          />
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>
            {isService ? '4. Descrição dos Serviços' : '4. Descrição das Atividades'}
          </Text>
          <TextInput
            style={[styles.textarea, { minHeight: 150 }]}
            value={serviceDescription}
            onChangeText={setServiceDescription}
            placeholder={isService ? "Descreva os serviços realizados..." : "Descreva as atividades diárias..."}
            multiline
            textAlignVertical="top"
          />
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>5. Observações</Text>
          <TextInput
            style={styles.textarea}
            value={observations}
            onChangeText={setObservations}
            placeholder="Adicione observações relevantes..."
            multiline
            textAlignVertical="top"
          />
        </View>

        <TouchableOpacity
          style={[styles.saveButton, saving && styles.saveButtonDisabled]}
          onPress={handleSave}
          disabled={saving}
        >
          {saving ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <Ionicons name="save" size={22} color="#fff" />
              <Text style={styles.saveButtonText}>Salvar Relatório</Text>
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
  headerRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 16, gap: 8 },
  backButton: { padding: 8 },
  title: { fontSize: 20, fontWeight: 'bold', color: '#1a237e', flex: 1 },
  pdfButton: { padding: 8 },
  infoCard: { backgroundColor: '#e3f2fd', borderRadius: 12, padding: 16, marginBottom: 16 },
  infoBadge: { backgroundColor: '#1a237e', alignSelf: 'flex-start', paddingHorizontal: 12, paddingVertical: 4, borderRadius: 6, marginBottom: 8 },
  infoBadgeText: { color: '#fff', fontWeight: '600', fontSize: 12 },
  infoClient: { fontSize: 16, fontWeight: '600', color: '#1a237e' },
  infoLocation: { fontSize: 13, color: '#555', marginTop: 4 },
  section: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 12 },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: '#1a237e', marginBottom: 12 },
  label: { fontSize: 13, fontWeight: '600', color: '#333', marginBottom: 6, marginTop: 8 },
  input: { backgroundColor: '#f8f9fa', borderRadius: 8, borderWidth: 1, borderColor: '#e0e0e0', padding: 12, fontSize: 15, color: '#333' },
  textarea: { backgroundColor: '#f8f9fa', borderRadius: 8, borderWidth: 1, borderColor: '#e0e0e0', padding: 12, fontSize: 15, color: '#333', minHeight: 100 },
  saveButton: { backgroundColor: '#1a237e', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', padding: 16, borderRadius: 12, gap: 8, marginBottom: 32 },
  saveButtonDisabled: { opacity: 0.6 },
  saveButtonText: { color: '#fff', fontSize: 18, fontWeight: '600' },
});
