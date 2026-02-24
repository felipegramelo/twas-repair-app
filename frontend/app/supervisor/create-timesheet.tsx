import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  TextInput,
  Modal,
  Alert,
  ActivityIndicator,
  Platform,
  KeyboardAvoidingView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { serviceOrderAPI, employeeAPI, timesheetAPI } from '../../services/api';
import { ServiceOrder, Employee, TimesheetEntry } from '../../types';

export default function CreateTimesheetScreen() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // Data
  const [serviceOrders, setServiceOrders] = useState<ServiceOrder[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  
  // Selected values
  const [selectedSO, setSelectedSO] = useState<ServiceOrder | null>(null);
  const [entries, setEntries] = useState<TimesheetEntry[]>([]);
  const [observations, setObservations] = useState('');
  
  // Modals
  const [soModalVisible, setSOModalVisible] = useState(false);
  const [employeeModalVisible, setEmployeeModalVisible] = useState(false);
  const [employeePickerVisible, setEmployeePickerVisible] = useState(false);
  const [editingEntryIndex, setEditingEntryIndex] = useState<number | null>(null);
  
  // Entry form
  const [entryDate, setEntryDate] = useState('');
  const [selectedEmployee, setSelectedEmployee] = useState<Employee | null>(null);
  const [serviceStart, setServiceStart] = useState('');
  const [serviceEnd, setServiceEnd] = useState('');
  const [travelStart, setTravelStart] = useState('');
  const [travelEnd, setTravelEnd] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [soData, empData] = await Promise.all([
        serviceOrderAPI.getAll(),
        employeeAPI.getAll(),
      ]);
      setServiceOrders(soData);
      setEmployees(empData);
    } catch (error: any) {
      Alert.alert('Erro', 'Erro ao carregar dados');
    } finally {
      setLoading(false);
    }
  };

  const openAddEntryModal = () => {
    setEditingEntryIndex(null);
    resetEntryForm();
    setEmployeeModalVisible(true);
  };

  const resetEntryForm = () => {
    setEntryDate('');
    setSelectedEmployee(null);
    setServiceStart('');
    setServiceEnd('');
    setTravelStart('');
    setTravelEnd('');
  };

  const handleAddEntry = () => {
    if (!entryDate || !selectedEmployee || !serviceStart || !serviceEnd) {
      Alert.alert('Erro', 'Preencha data, funcionário, início e fim do serviço');
      return;
    }

    const newEntry: TimesheetEntry = {
      date: entryDate,
      employee_id: selectedEmployee.id,
      employee_name: selectedEmployee.name,
      employee_function: selectedEmployee.function,
      service_start: serviceStart,
      service_end: serviceEnd,
      travel_start: travelStart,
      travel_end: travelEnd,
    };

    if (editingEntryIndex !== null) {
      const newEntries = [...entries];
      newEntries[editingEntryIndex] = newEntry;
      setEntries(newEntries);
    } else {
      setEntries([...entries, newEntry]);
    }

    setEmployeeModalVisible(false);
    resetEntryForm();
  };

  const handleEditEntry = (index: number) => {
    const entry = entries[index];
    setEditingEntryIndex(index);
    setEntryDate(entry.date);
    const emp = employees.find(e => e.id === entry.employee_id);
    setSelectedEmployee(emp || null);
    setServiceStart(entry.service_start);
    setServiceEnd(entry.service_end);
    setTravelStart(entry.travel_start || '');
    setTravelEnd(entry.travel_end || '');
    setEmployeeModalVisible(true);
  };

  const handleDeleteEntry = (index: number) => {
    Alert.alert(
      'Confirmar',
      'Deseja remover esta entrada?',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Remover',
          style: 'destructive',
          onPress: () => {
            const newEntries = entries.filter((_, i) => i !== index);
            setEntries(newEntries);
          },
        },
      ]
    );
  };

  const handleSave = async () => {
    if (!selectedSO) {
      Alert.alert('Erro', 'Selecione uma Ordem de Serviço');
      return;
    }

    if (entries.length === 0) {
      Alert.alert('Erro', 'Adicione pelo menos uma entrada');
      return;
    }

    setSaving(true);
    try {
      await timesheetAPI.create(selectedSO.id, entries, observations);
      Alert.alert('Sucesso', 'Timesheet criado com sucesso', [
        { text: 'OK', onPress: () => router.back() },
      ]);
    } catch (error: any) {
      Alert.alert('Erro', 'Erro ao salvar timesheet');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#1a237e" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#1a237e" />
        </TouchableOpacity>
        <Text style={styles.title}>Novo Timesheet</Text>
        <View style={{ width: 40 }} />
      </View>

      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.flex}
      >
        <ScrollView contentContainerStyle={styles.scrollContent}>
          {/* Service Order Selection */}
          <View style={styles.section}>
            <Text style={styles.label}>Ordem de Serviço *</Text>
            <TouchableOpacity
              style={styles.selectButton}
              onPress={() => setSOModalVisible(true)}
            >
              <Text style={selectedSO ? styles.selectButtonTextSelected : styles.selectButtonText}>
                {selectedSO ? `${selectedSO.os_number} - ${selectedSO.client}` : 'Selecionar O.S.'}
              </Text>
              <Ionicons name="chevron-down" size={20} color="#666" />
            </TouchableOpacity>
          </View>

          {/* Entries */}
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text style={styles.label}>Entradas ({entries.length})</Text>
              <TouchableOpacity onPress={openAddEntryModal} style={styles.addEntryButton}>
                <Ionicons name="add" size={20} color="#1a237e" />
                <Text style={styles.addEntryText}>Adicionar</Text>
              </TouchableOpacity>
            </View>

            {entries.map((entry, index) => (
              <View key={index} style={styles.entryCard}>
                <View style={styles.entryCardContent}>
                  <View style={styles.entryBadge}>
                    <Text style={styles.entryBadgeText}>{entry.employee_function}</Text>
                  </View>
                  <View style={styles.entryInfo}>
                    <Text style={styles.entryName}>{entry.employee_name}</Text>
                    <Text style={styles.entryDetail}>Data: {entry.date}</Text>
                    <Text style={styles.entryDetail}>
                      Serviço: {entry.service_start} - {entry.service_end}
                    </Text>
                    {entry.travel_start && (
                      <Text style={styles.entryDetail}>
                        Viagem: {entry.travel_start} - {entry.travel_end}
                      </Text>
                    )}
                  </View>
                </View>
                <View style={styles.entryActions}>
                  <TouchableOpacity onPress={() => handleEditEntry(index)}>
                    <Ionicons name="pencil" size={20} color="#1a237e" />
                  </TouchableOpacity>
                  <TouchableOpacity onPress={() => handleDeleteEntry(index)}>
                    <Ionicons name="trash" size={20} color="#d32f2f" />
                  </TouchableOpacity>
                </View>
              </View>
            ))}

            {entries.length === 0 && (
              <View style={styles.emptyEntries}>
                <Ionicons name="people-outline" size={48} color="#ccc" />
                <Text style={styles.emptyText}>Nenhuma entrada adicionada</Text>
              </View>
            )}
          </View>

          {/* Observations */}
          <View style={styles.section}>
            <Text style={styles.label}>Observações</Text>
            <TextInput
              style={[styles.input, styles.textArea]}
              placeholder="Adicione observações (opcional)"
              value={observations}
              onChangeText={setObservations}
              multiline
              numberOfLines={4}
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
              <Text style={styles.saveButtonText}>Salvar Timesheet</Text>
            )}
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>

      {/* Service Order Modal */}
      <Modal
        visible={soModalVisible}
        animationType="slide"
        transparent
        onRequestClose={() => setSOModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Selecionar Ordem de Serviço</Text>
            <ScrollView style={styles.modalList}>
              {serviceOrders.map((so) => (
                <TouchableOpacity
                  key={so.id}
                  style={styles.modalItem}
                  onPress={() => {
                    setSelectedSO(so);
                    setSOModalVisible(false);
                  }}
                >
                  <Text style={styles.modalItemTitle}>{so.os_number}</Text>
                  <Text style={styles.modalItemSubtitle}>{so.client}</Text>
                  <Text style={styles.modalItemDetail}>{so.location}</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
            <TouchableOpacity
              style={styles.modalCloseButton}
              onPress={() => setSOModalVisible(false)}
            >
              <Text style={styles.modalCloseButtonText}>Fechar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* Employee Entry Modal */}
      <Modal
        visible={employeeModalVisible}
        animationType="slide"
        transparent
        onRequestClose={() => setEmployeeModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <ScrollView>
              <Text style={styles.modalTitle}>
                {editingEntryIndex !== null ? 'Editar Entrada' : 'Adicionar Entrada'}
              </Text>

              <Text style={styles.inputLabel}>Data (DD/MM/YYYY) *</Text>
              <TextInput
                style={styles.input}
                placeholder="Ex: 07/08/2025"
                value={entryDate}
                onChangeText={setEntryDate}
              />

              <Text style={styles.inputLabel}>Funcionário *</Text>
              <TouchableOpacity
                style={styles.selectButton}
                onPress={() => setEmployeePickerVisible(true)}
              >
                <Text style={selectedEmployee ? styles.selectButtonTextSelected : styles.selectButtonText}>
                  {selectedEmployee ? `${selectedEmployee.name} (${selectedEmployee.function})` : 'Selecionar'}
                </Text>
                <Ionicons name="chevron-down" size={20} color="#666" />
              </TouchableOpacity>

              <Text style={styles.inputLabel}>Serviço - Início (HH:MM) *</Text>
              <TextInput
                style={styles.input}
                placeholder="Ex: 08:00"
                value={serviceStart}
                onChangeText={setServiceStart}
              />

              <Text style={styles.inputLabel}>Serviço - Fim (HH:MM) *</Text>
              <TextInput
                style={styles.input}
                placeholder="Ex: 17:00"
                value={serviceEnd}
                onChangeText={setServiceEnd}
              />

              <Text style={styles.inputLabel}>Viagem - Início (HH:MM)</Text>
              <TextInput
                style={styles.input}
                placeholder="Ex: 07:00"
                value={travelStart}
                onChangeText={setTravelStart}
              />

              <Text style={styles.inputLabel}>Viagem - Fim (HH:MM)</Text>
              <TextInput
                style={styles.input}
                placeholder="Ex: 18:00"
                value={travelEnd}
                onChangeText={setTravelEnd}
              />

              <View style={styles.modalButtons}>
                <TouchableOpacity
                  style={[styles.modalButton, styles.cancelButton]}
                  onPress={() => setEmployeeModalVisible(false)}
                >
                  <Text style={styles.cancelButtonText}>Cancelar</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.modalButton, styles.confirmButton]}
                  onPress={handleAddEntry}
                >
                  <Text style={styles.confirmButtonText}>
                    {editingEntryIndex !== null ? 'Atualizar' : 'Adicionar'}
                  </Text>
                </TouchableOpacity>
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* Employee Picker Modal */}
      <Modal
        visible={employeePickerVisible}
        animationType="slide"
        transparent
        onRequestClose={() => setEmployeePickerVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Selecionar Funcionário</Text>
            <ScrollView style={styles.modalList}>
              {employees.length === 0 ? (
                <View style={styles.emptyContainer}>
                  <Ionicons name="people-outline" size={48} color="#ccc" />
                  <Text style={styles.emptyText}>
                    Nenhum funcionário cadastrado.{'\n'}
                    Peça ao administrador para cadastrar funcionários.
                  </Text>
                </View>
              ) : (
                employees.map((emp) => (
                  <TouchableOpacity
                    key={emp.id}
                    style={styles.modalItem}
                    onPress={() => {
                      setSelectedEmployee(emp);
                      setEmployeePickerVisible(false);
                    }}
                  >
                    <View style={styles.employeeItemBadge}>
                      <Text style={styles.employeeItemBadgeText}>{emp.function}</Text>
                    </View>
                    <View style={styles.employeeItemInfo}>
                      <Text style={styles.modalItemTitle}>{emp.name}</Text>
                      <Text style={styles.modalItemSubtitle}>
                        {emp.function === 'E' && 'Engenheiro / Engineer'}
                        {emp.function === 'SE' && 'Especialista / Specialist'}
                        {emp.function === 'T' && 'Técnico / Technician'}
                        {emp.function === 'M' && 'Mecânico / Mechanic'}
                        {emp.function === 'W' && 'Soldador / Welder'}
                        {emp.function === 'TK' && 'Almoxarife / Tool Keeper'}
                      </Text>
                    </View>
                  </TouchableOpacity>
                ))
              )}
            </ScrollView>
            <TouchableOpacity
              style={styles.modalCloseButton}
              onPress={() => setEmployeePickerVisible(false)}
            >
              <Text style={styles.modalCloseButtonText}>Fechar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  flex: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  backButton: {
    padding: 8,
  },
  title: {
    fontSize: 20,
    fontWeight: '600',
    color: '#1a237e',
  },
  scrollContent: {
    padding: 16,
  },
  section: {
    marginBottom: 24,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
    color: '#212121',
    marginBottom: 8,
  },
  selectButton: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  selectButtonText: {
    fontSize: 16,
    color: '#999',
  },
  selectButtonTextSelected: {
    fontSize: 16,
    color: '#212121',
  },
  addEntryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  addEntryText: {
    fontSize: 16,
    color: '#1a237e',
    fontWeight: '600',
  },
  entryCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  entryCardContent: {
    flexDirection: 'row',
    flex: 1,
  },
  entryBadge: {
    backgroundColor: '#e3f2fd',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
    marginRight: 12,
  },
  entryBadgeText: {
    color: '#1a237e',
    fontWeight: '600',
    fontSize: 12,
  },
  entryInfo: {
    flex: 1,
  },
  entryName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#212121',
  },
  entryDetail: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  entryActions: {
    flexDirection: 'row',
    gap: 12,
  },
  emptyEntries: {
    alignItems: 'center',
    paddingVertical: 48,
  },
  emptyText: {
    fontSize: 14,
    color: '#999',
    marginTop: 12,
  },
  input: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 16,
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  textArea: {
    minHeight: 100,
    textAlignVertical: 'top',
  },
  saveButton: {
    backgroundColor: '#1a237e',
    height: 56,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 16,
  },
  saveButtonDisabled: {
    opacity: 0.6,
  },
  saveButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    padding: 16,
  },
  modalContent: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
    maxHeight: '80%',
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#1a237e',
    marginBottom: 16,
  },
  modalList: {
    maxHeight: 400,
  },
  modalItem: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  modalItemTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#212121',
  },
  modalItemSubtitle: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  modalItemDetail: {
    fontSize: 12,
    color: '#999',
    marginTop: 2,
  },
  modalCloseButton: {
    backgroundColor: '#f5f5f5',
    height: 48,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 16,
  },
  modalCloseButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#666',
  },
  inputLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#212121',
    marginBottom: 8,
    marginTop: 12,
  },
  modalButtons: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 24,
  },
  modalButton: {
    flex: 1,
    height: 48,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  cancelButton: {
    backgroundColor: '#f5f5f5',
  },
  cancelButtonText: {
    color: '#666',
    fontSize: 16,
    fontWeight: '600',
  },
  confirmButton: {
    backgroundColor: '#1a237e',
  },
  confirmButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  employeeItemBadge: {
    backgroundColor: '#e3f2fd',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
    marginRight: 12,
  },
  employeeItemBadgeText: {
    color: '#1a237e',
    fontWeight: '600',
    fontSize: 12,
  },
  employeeItemInfo: {
    flex: 1,
  },
});
