import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  FlatList,
  Alert,
  TextInput,
  Modal,
  ActivityIndicator,
  ScrollView,
  Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { serviceOrderAPI, employeeAPI } from '../../services/api';
import { ServiceOrder, Employee } from '../../types';

export default function ServiceOrdersScreen() {
  const router = useRouter();
  const [serviceOrders, setServiceOrders] = useState<ServiceOrder[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingSO, setEditingSO] = useState<ServiceOrder | null>(null);

  const [osNumber, setOsNumber] = useState('');
  const [client, setClient] = useState('');
  const [location, setLocation] = useState('');
  const [service, setService] = useState('');
  const [selectedEmployeeIds, setSelectedEmployeeIds] = useState<string[]>([]);
  const [employeePickerVisible, setEmployeePickerVisible] = useState(false);

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

  const loadServiceOrders = async () => {
    try {
      const data = await serviceOrderAPI.getAll();
      setServiceOrders(data);
    } catch (error: any) {
      Alert.alert('Erro', 'Erro ao carregar ordens de serviço');
    }
  };

  const openAddModal = () => {
    setEditingSO(null);
    setOsNumber('');
    setClient('');
    setLocation('');
    setService('');
    setSelectedEmployeeIds([]);
    setModalVisible(true);
  };

  const openEditModal = (so: ServiceOrder) => {
    setEditingSO(so);
    setOsNumber(so.os_number);
    setClient(so.client);
    setLocation(so.location);
    setService(so.service);
    setSelectedEmployeeIds(so.employee_ids || []);
    setModalVisible(true);
  };

  const handleSave = async () => {
    if (!osNumber || !client || !location || !service) {
      Alert.alert('Erro', 'Preencha todos os campos obrigatórios');
      return;
    }
    try {
      if (editingSO) {
        await serviceOrderAPI.update(editingSO.id, osNumber, client, location, service, selectedEmployeeIds);
      } else {
        await serviceOrderAPI.create(osNumber, client, location, service, selectedEmployeeIds);
      }
      setModalVisible(false);
      loadServiceOrders();
    } catch (error: any) {
      Alert.alert('Erro', 'Erro ao salvar ordem de serviço');
    }
  };

  const handleDelete = (so: ServiceOrder) => {
    if (Platform.OS === 'web') {
      if (window.confirm(`Deseja excluir a O.S. ${so.os_number}?`)) {
        performDelete(so);
      }
    } else {
      Alert.alert('Confirmar exclusão', `Deseja excluir a O.S. ${so.os_number}?`, [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Excluir', style: 'destructive', onPress: () => performDelete(so) },
      ]);
    }
  };

  const performDelete = async (so: ServiceOrder) => {
    try {
      await serviceOrderAPI.delete(so.id);
      loadServiceOrders();
    } catch (error: any) {
      Alert.alert('Erro', 'Erro ao excluir ordem de serviço');
    }
  };

  const toggleEmployee = (empId: string) => {
    setSelectedEmployeeIds(prev =>
      prev.includes(empId) ? prev.filter(id => id !== empId) : [...prev, empId]
    );
  };

  const getEmployeeNames = (ids: string[]) => {
    if (!ids || ids.length === 0) return 'Nenhum funcionário';
    return ids
      .map(id => employees.find(e => e.id === id))
      .filter(Boolean)
      .map(e => e!.name)
      .join(', ');
  };

  const renderServiceOrder = ({ item }: { item: ServiceOrder }) => (
    <View style={styles.card} data-testid={`so-card-${item.id}`}>
      <TouchableOpacity style={styles.cardContent} onPress={() => openEditModal(item)}>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{item.os_number}</Text>
        </View>
        <View style={styles.cardInfo}>
          <Text style={styles.cardTitle}>{item.client}</Text>
          <Text style={styles.cardSubtitle}>{item.location}</Text>
          <Text style={styles.cardMeta}>{item.service}</Text>
          <Text style={styles.cardEmployees} numberOfLines={2}>
            Funcionários: {getEmployeeNames(item.employee_ids || [])}
          </Text>
        </View>
      </TouchableOpacity>
      <View style={styles.actions}>
        <TouchableOpacity onPress={() => openEditModal(item)} style={styles.actionButton}>
          <Ionicons name="pencil" size={20} color="#1a237e" />
        </TouchableOpacity>
        <TouchableOpacity onPress={() => handleDelete(item)} style={styles.actionButton} data-testid={`delete-so-${item.id}`}>
          <Ionicons name="trash-outline" size={20} color="#d32f2f" />
        </TouchableOpacity>
      </View>
    </View>
  );

  if (loading) {
    return <View style={styles.loadingContainer}><ActivityIndicator size="large" color="#1a237e" /></View>;
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#1a237e" />
        </TouchableOpacity>
        <Text style={styles.title}>Ordens de Serviço</Text>
        <TouchableOpacity onPress={openAddModal} style={styles.addButton}>
          <Ionicons name="add" size={28} color="#1a237e" />
        </TouchableOpacity>
      </View>

      <FlatList
        data={serviceOrders}
        renderItem={renderServiceOrder}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Ionicons name="document-text-outline" size={64} color="#ccc" />
            <Text style={styles.emptyText}>Nenhuma ordem de serviço</Text>
          </View>
        }
      />

      {/* Create/Edit Modal */}
      <Modal visible={modalVisible} animationType="slide" transparent onRequestClose={() => setModalVisible(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <ScrollView>
              <Text style={styles.modalTitle}>{editingSO ? 'Editar O.S.' : 'Nova Ordem de Serviço'}</Text>

              <Text style={styles.inputLabel}>Número da O.S. *</Text>
              <TextInput style={styles.input} value={osNumber} onChangeText={setOsNumber} placeholder="Ex: 2602-14" />

              <Text style={styles.inputLabel}>Cliente *</Text>
              <TextInput style={styles.input} value={client} onChangeText={setClient} placeholder="Nome do cliente" />

              <Text style={styles.inputLabel}>Localização *</Text>
              <TextInput style={styles.input} value={location} onChangeText={setLocation} placeholder="Local do serviço" />

              <Text style={styles.inputLabel}>Serviço *</Text>
              <TextInput style={styles.input} value={service} onChangeText={setService} placeholder="Descrição do serviço" />

              <Text style={styles.inputLabel}>Funcionários ({selectedEmployeeIds.length} selecionados)</Text>
              <TouchableOpacity style={styles.selectButton} onPress={() => setEmployeePickerVisible(true)}>
                <Text style={selectedEmployeeIds.length > 0 ? styles.selectTextSelected : styles.selectText} numberOfLines={2}>
                  {selectedEmployeeIds.length > 0
                    ? getEmployeeNames(selectedEmployeeIds)
                    : 'Selecionar funcionários'}
                </Text>
                <Ionicons name="people" size={20} color="#666" />
              </TouchableOpacity>

              <View style={styles.modalButtons}>
                <TouchableOpacity style={[styles.modalButton, styles.cancelBtn]} onPress={() => setModalVisible(false)}>
                  <Text style={styles.cancelBtnText}>Cancelar</Text>
                </TouchableOpacity>
                <TouchableOpacity style={[styles.modalButton, styles.saveBtn]} onPress={handleSave}>
                  <Text style={styles.saveBtnText}>Salvar</Text>
                </TouchableOpacity>
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* Employee Multi-Select Modal */}
      <Modal visible={employeePickerVisible} animationType="slide" transparent onRequestClose={() => setEmployeePickerVisible(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Selecionar Funcionários</Text>
            <ScrollView style={styles.employeeList}>
              {employees.length === 0 ? (
                <Text style={styles.emptyText}>Nenhum funcionário cadastrado</Text>
              ) : (
                employees.map(emp => (
                  <TouchableOpacity
                    key={emp.id}
                    style={[styles.employeeItem, selectedEmployeeIds.includes(emp.id) && styles.employeeItemSelected]}
                    onPress={() => toggleEmployee(emp.id)}
                  >
                    <View style={styles.employeeItemContent}>
                      <View style={[styles.empBadge, selectedEmployeeIds.includes(emp.id) && styles.empBadgeSelected]}>
                        <Text style={[styles.empBadgeText, selectedEmployeeIds.includes(emp.id) && styles.empBadgeTextSelected]}>
                          {emp.function}
                        </Text>
                      </View>
                      <Text style={styles.employeeName}>{emp.name}</Text>
                    </View>
                    <Ionicons
                      name={selectedEmployeeIds.includes(emp.id) ? 'checkbox' : 'square-outline'}
                      size={24}
                      color={selectedEmployeeIds.includes(emp.id) ? '#1a237e' : '#ccc'}
                    />
                  </TouchableOpacity>
                ))
              )}
            </ScrollView>
            <TouchableOpacity style={styles.doneButton} onPress={() => setEmployeePickerVisible(false)}>
              <Text style={styles.doneButtonText}>Concluído ({selectedEmployeeIds.length})</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 12, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#e0e0e0' },
  backButton: { padding: 8 },
  title: { fontSize: 20, fontWeight: '600', color: '#1a237e' },
  addButton: { padding: 8 },
  listContent: { padding: 16 },
  card: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 12, flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', elevation: 2, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.1, shadowRadius: 2 },
  cardContent: { flexDirection: 'row', flex: 1 },
  badge: { backgroundColor: '#e3f2fd', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8, marginRight: 12 },
  badgeText: { color: '#1a237e', fontWeight: '600', fontSize: 12 },
  cardInfo: { flex: 1 },
  cardTitle: { fontSize: 16, fontWeight: '600', color: '#212121' },
  cardSubtitle: { fontSize: 14, color: '#666', marginTop: 4 },
  cardMeta: { fontSize: 12, color: '#999', marginTop: 4 },
  cardEmployees: { fontSize: 11, color: '#1a237e', marginTop: 6, fontStyle: 'italic' },
  actions: { flexDirection: 'row', gap: 4 },
  actionButton: { padding: 8 },
  emptyContainer: { alignItems: 'center', paddingVertical: 64 },
  emptyText: { fontSize: 16, color: '#999', marginTop: 16, textAlign: 'center' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', padding: 16 },
  modalContent: { backgroundColor: '#fff', borderRadius: 16, padding: 24, maxHeight: '85%' },
  modalTitle: { fontSize: 20, fontWeight: '600', color: '#1a237e', marginBottom: 16 },
  inputLabel: { fontSize: 14, fontWeight: '600', color: '#212121', marginBottom: 8, marginTop: 12 },
  input: { backgroundColor: '#fff', borderRadius: 8, padding: 14, fontSize: 16, borderWidth: 1, borderColor: '#e0e0e0' },
  selectButton: { backgroundColor: '#fff', borderRadius: 8, padding: 14, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderWidth: 1, borderColor: '#e0e0e0' },
  selectText: { fontSize: 16, color: '#999', flex: 1 },
  selectTextSelected: { fontSize: 16, color: '#212121', flex: 1 },
  modalButtons: { flexDirection: 'row', gap: 12, marginTop: 24 },
  modalButton: { flex: 1, height: 48, borderRadius: 8, justifyContent: 'center', alignItems: 'center' },
  cancelBtn: { backgroundColor: '#f5f5f5' },
  cancelBtnText: { color: '#666', fontSize: 16, fontWeight: '600' },
  saveBtn: { backgroundColor: '#1a237e' },
  saveBtnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  employeeList: { maxHeight: 400 },
  employeeItem: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: 14, borderBottomWidth: 1, borderBottomColor: '#f0f0f0', borderRadius: 8 },
  employeeItemSelected: { backgroundColor: '#e8eaf6' },
  employeeItemContent: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  empBadge: { backgroundColor: '#e3f2fd', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 6, marginRight: 12 },
  empBadgeSelected: { backgroundColor: '#1a237e' },
  empBadgeText: { color: '#1a237e', fontWeight: '600', fontSize: 12 },
  empBadgeTextSelected: { color: '#fff' },
  employeeName: { fontSize: 16, color: '#212121' },
  doneButton: { backgroundColor: '#1a237e', height: 48, borderRadius: 8, justifyContent: 'center', alignItems: 'center', marginTop: 16 },
  doneButtonText: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
