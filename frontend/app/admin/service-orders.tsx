import React, { useState, useEffect } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, FlatList, Alert, TextInput, Modal, ActivityIndicator, ScrollView, Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { serviceOrderAPI, employeeAPI } from '../../services/api';
import { ServiceOrder, Employee, SOEmployee } from '../../types';

const FUNCTIONS = ['E', 'EN', 'Sup', 'T', 'M', 'TS'];

export default function ServiceOrdersScreen() {
  const router = useRouter();
  const [serviceOrders, setServiceOrders] = useState<ServiceOrder[]>([]);
  const [allEmployees, setAllEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingSO, setEditingSO] = useState<ServiceOrder | null>(null);

  const [osNumber, setOsNumber] = useState('');
  const [client, setClient] = useState('');
  const [location, setLocation] = useState('');
  const [service, setService] = useState('');
  const [soEmployees, setSOEmployees] = useState<SOEmployee[]>([]);
  const [employeePickerVisible, setEmployeePickerVisible] = useState(false);
  const [funcPickerVisible, setFuncPickerVisible] = useState(false);
  const [editingEmpIndex, setEditingEmpIndex] = useState<number | null>(null);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [soData, empData] = await Promise.all([serviceOrderAPI.getAll(), employeeAPI.getAll()]);
      setServiceOrders(soData);
      setAllEmployees(empData);
    } catch { Alert.alert('Erro', 'Erro ao carregar dados'); }
    finally { setLoading(false); }
  };

  const loadServiceOrders = async () => {
    try { setServiceOrders(await serviceOrderAPI.getAll()); } catch {}
  };

  const openAdd = () => {
    setEditingSO(null); setOsNumber(''); setClient(''); setLocation(''); setService(''); setSOEmployees([]);
    setModalVisible(true);
  };

  const openEdit = (so: ServiceOrder) => {
    setEditingSO(so); setOsNumber(so.os_number); setClient(so.client); setLocation(so.location); setService(so.service);
    setSOEmployees(so.employees || []);
    setModalVisible(true);
  };

  const handleSave = async () => {
    if (!osNumber || !client || !location || !service) { Alert.alert('Erro', 'Preencha todos os campos'); return; }
    try {
      if (editingSO) await serviceOrderAPI.update(editingSO.id, osNumber, client, location, service, soEmployees);
      else await serviceOrderAPI.create(osNumber, client, location, service, soEmployees);
      setModalVisible(false); loadServiceOrders();
    } catch { Alert.alert('Erro', 'Erro ao salvar'); }
  };

  const handleDelete = (so: ServiceOrder) => {
    if (Platform.OS === 'web') { if (window.confirm(`Excluir O.S. ${so.os_number}?`)) performDelete(so); }
    else { Alert.alert('Confirmar', `Excluir O.S. ${so.os_number}?`, [{ text: 'Cancelar', style: 'cancel' }, { text: 'Excluir', style: 'destructive', onPress: () => performDelete(so) }]); }
  };

  const performDelete = async (so: ServiceOrder) => {
    try { await serviceOrderAPI.delete(so.id); loadServiceOrders(); } catch { Alert.alert('Erro', 'Erro ao excluir'); }
  };

  const addEmployee = (emp: Employee) => {
    if (soEmployees.find(e => e.employee_id === emp.id)) return;
    setSOEmployees([...soEmployees, { employee_id: emp.id, function: 'T' }]);
    setEmployeePickerVisible(false);
  };

  const removeEmployee = (index: number) => {
    setSOEmployees(soEmployees.filter((_, i) => i !== index));
  };

  const openFuncPicker = (index: number) => { setEditingEmpIndex(index); setFuncPickerVisible(true); };

  const setEmployeeFunc = (func: string) => {
    if (editingEmpIndex === null) return;
    const updated = [...soEmployees];
    updated[editingEmpIndex] = { ...updated[editingEmpIndex], function: func };
    setSOEmployees(updated);
    setFuncPickerVisible(false);
  };

  const getEmpName = (empId: string) => allEmployees.find(e => e.id === empId)?.name || 'Desconhecido';

  const getEmpSummary = (emps: SOEmployee[]) => {
    if (!emps || emps.length === 0) return 'Nenhum funcionário';
    return emps.map(e => `${getEmpName(e.employee_id)} (${e.function})`).join(', ');
  };

  if (loading) return <View style={s.center}><ActivityIndicator size="large" color="#1a237e" /></View>;

  return (
    <SafeAreaView style={s.container}>
      <View style={s.header}>
        <TouchableOpacity onPress={() => router.back()} style={s.btn}><Ionicons name="arrow-back" size={24} color="#1a237e" /></TouchableOpacity>
        <Text style={s.title}>Ordens de Serviço</Text>
        <TouchableOpacity onPress={openAdd} style={s.btn}><Ionicons name="add" size={28} color="#1a237e" /></TouchableOpacity>
      </View>
      <FlatList
        data={serviceOrders} keyExtractor={i => i.id} contentContainerStyle={{ padding: 16 }}
        renderItem={({ item }) => (
          <View style={s.card}>
            <TouchableOpacity style={s.cardContent} onPress={() => openEdit(item)}>
              <View style={s.badge}><Text style={s.badgeText}>{item.os_number}</Text></View>
              <View style={{ flex: 1 }}>
                <Text style={s.cardTitle}>{item.client}</Text>
                <Text style={s.cardSub}>{item.location}</Text>
                <Text style={s.cardMeta}>{item.service}</Text>
                <Text style={s.cardEmps} numberOfLines={2}>{getEmpSummary(item.employees || [])}</Text>
              </View>
            </TouchableOpacity>
            <View style={s.actions}>
              <TouchableOpacity onPress={() => openEdit(item)} style={s.actionBtn}><Ionicons name="pencil" size={20} color="#1a237e" /></TouchableOpacity>
              <TouchableOpacity onPress={() => handleDelete(item)} style={s.actionBtn}><Ionicons name="trash-outline" size={20} color="#d32f2f" /></TouchableOpacity>
            </View>
          </View>
        )}
        ListEmptyComponent={<View style={s.empty}><Ionicons name="document-text-outline" size={64} color="#ccc" /><Text style={s.emptyText}>Nenhuma O.S.</Text></View>}
      />

      {/* Create/Edit Modal */}
      <Modal visible={modalVisible} animationType="slide" transparent onRequestClose={() => setModalVisible(false)}>
        <View style={s.modalOverlay}><View style={s.modalContent}><ScrollView>
          <Text style={s.modalTitle}>{editingSO ? 'Editar O.S.' : 'Nova O.S.'}</Text>
          <Text style={s.label}>Número da O.S. *</Text>
          <TextInput style={s.input} value={osNumber} onChangeText={setOsNumber} placeholder="Ex: 2602-14" />
          <Text style={s.label}>Cliente *</Text>
          <TextInput style={s.input} value={client} onChangeText={setClient} placeholder="Nome do cliente" />
          <Text style={s.label}>Localização *</Text>
          <TextInput style={s.input} value={location} onChangeText={setLocation} placeholder="Local do serviço" />
          <Text style={s.label}>Serviço *</Text>
          <TextInput style={s.input} value={service} onChangeText={setService} placeholder="Descrição" />

          <View style={s.sectionHeader}>
            <Text style={s.label}>Funcionários ({soEmployees.length})</Text>
            <TouchableOpacity onPress={() => setEmployeePickerVisible(true)} style={s.addEmpBtn}>
              <Ionicons name="add" size={18} color="#1a237e" /><Text style={s.addEmpText}>Adicionar</Text>
            </TouchableOpacity>
          </View>

          {soEmployees.map((soEmp, idx) => (
            <View key={idx} style={s.empRow}>
              <Text style={s.empName} numberOfLines={1}>{getEmpName(soEmp.employee_id)}</Text>
              <TouchableOpacity style={s.funcBadge} onPress={() => openFuncPicker(idx)}>
                <Text style={s.funcBadgeText}>{soEmp.function}</Text>
                <Ionicons name="chevron-down" size={14} color="#1a237e" />
              </TouchableOpacity>
              <TouchableOpacity onPress={() => removeEmployee(idx)} style={s.removeBtn}>
                <Ionicons name="close-circle" size={22} color="#d32f2f" />
              </TouchableOpacity>
            </View>
          ))}

          <View style={s.modalBtns}>
            <TouchableOpacity style={[s.modalBtn, s.cancelBtn]} onPress={() => setModalVisible(false)}><Text style={s.cancelText}>Cancelar</Text></TouchableOpacity>
            <TouchableOpacity style={[s.modalBtn, s.saveBtn]} onPress={handleSave}><Text style={s.saveText}>Salvar</Text></TouchableOpacity>
          </View>
        </ScrollView></View></View>
      </Modal>

      {/* Employee Picker */}
      <Modal visible={employeePickerVisible} animationType="slide" transparent onRequestClose={() => setEmployeePickerVisible(false)}>
        <View style={s.modalOverlay}><View style={s.modalContent}>
          <Text style={s.modalTitle}>Adicionar Funcionário</Text>
          <ScrollView style={{ maxHeight: 400 }}>
            {allEmployees.filter(e => !soEmployees.find(se => se.employee_id === e.id)).map(emp => (
              <TouchableOpacity key={emp.id} style={s.pickerItem} onPress={() => addEmployee(emp)}>
                <Text style={s.pickerItemText}>{emp.name}</Text>
                <Ionicons name="add-circle" size={24} color="#1a237e" />
              </TouchableOpacity>
            ))}
            {allEmployees.filter(e => !soEmployees.find(se => se.employee_id === e.id)).length === 0 && (
              <Text style={s.emptyText}>Todos os funcionários já foram adicionados</Text>
            )}
          </ScrollView>
          <TouchableOpacity style={s.closeBtn} onPress={() => setEmployeePickerVisible(false)}><Text style={s.closeBtnText}>Fechar</Text></TouchableOpacity>
        </View></View>
      </Modal>

      {/* Function Picker */}
      <Modal visible={funcPickerVisible} animationType="fade" transparent onRequestClose={() => setFuncPickerVisible(false)}>
        <View style={s.modalOverlay}><View style={[s.modalContent, { maxWidth: 300, alignSelf: 'center' }]}>
          <Text style={s.modalTitle}>Selecionar Função</Text>
          {FUNCTIONS.map(f => (
            <TouchableOpacity key={f} style={s.funcItem} onPress={() => setEmployeeFunc(f)}>
              <Text style={s.funcItemText}>{f}</Text>
              <Text style={s.funcItemDesc}>
                {f === 'E' ? 'Engenheiro' : f === 'EN' ? 'Encarregado' : f === 'Sup' ? 'Supervisor' : f === 'T' ? 'Técnico' : f === 'M' ? 'Mecânico' : 'Téc. Segurança'}
              </Text>
            </TouchableOpacity>
          ))}
        </View></View>
      </Modal>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 12, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#e0e0e0' },
  btn: { padding: 8 },
  title: { fontSize: 20, fontWeight: '600', color: '#1a237e' },
  card: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 12, flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', elevation: 2 },
  cardContent: { flexDirection: 'row', flex: 1 },
  badge: { backgroundColor: '#e3f2fd', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8, marginRight: 12 },
  badgeText: { color: '#1a237e', fontWeight: '600', fontSize: 12 },
  cardTitle: { fontSize: 16, fontWeight: '600', color: '#212121' },
  cardSub: { fontSize: 14, color: '#666', marginTop: 4 },
  cardMeta: { fontSize: 12, color: '#999', marginTop: 4 },
  cardEmps: { fontSize: 11, color: '#1a237e', marginTop: 6, fontStyle: 'italic' },
  actions: { flexDirection: 'row', gap: 4 },
  actionBtn: { padding: 8 },
  empty: { alignItems: 'center', paddingVertical: 64 },
  emptyText: { fontSize: 16, color: '#999', marginTop: 16, textAlign: 'center' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', padding: 16 },
  modalContent: { backgroundColor: '#fff', borderRadius: 16, padding: 24, maxHeight: '85%' },
  modalTitle: { fontSize: 20, fontWeight: '600', color: '#1a237e', marginBottom: 16 },
  label: { fontSize: 14, fontWeight: '600', color: '#212121', marginBottom: 8, marginTop: 12 },
  input: { backgroundColor: '#fff', borderRadius: 8, padding: 14, fontSize: 16, borderWidth: 1, borderColor: '#e0e0e0' },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 16, marginBottom: 8 },
  addEmpBtn: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  addEmpText: { fontSize: 14, color: '#1a237e', fontWeight: '600' },
  empRow: { flexDirection: 'row', alignItems: 'center', padding: 10, backgroundColor: '#f5f5f5', borderRadius: 8, marginBottom: 8 },
  empName: { flex: 1, fontSize: 14, color: '#212121' },
  funcBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#e3f2fd', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 6, marginHorizontal: 8, gap: 4 },
  funcBadgeText: { color: '#1a237e', fontWeight: '600', fontSize: 13 },
  removeBtn: { padding: 4 },
  modalBtns: { flexDirection: 'row', gap: 12, marginTop: 24 },
  modalBtn: { flex: 1, height: 48, borderRadius: 8, justifyContent: 'center', alignItems: 'center' },
  cancelBtn: { backgroundColor: '#f5f5f5' },
  cancelText: { color: '#666', fontSize: 16, fontWeight: '600' },
  saveBtn: { backgroundColor: '#1a237e' },
  saveText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  pickerItem: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 14, borderBottomWidth: 1, borderBottomColor: '#f0f0f0' },
  pickerItemText: { fontSize: 16, color: '#212121' },
  closeBtn: { backgroundColor: '#f5f5f5', height: 48, borderRadius: 8, justifyContent: 'center', alignItems: 'center', marginTop: 16 },
  closeBtnText: { fontSize: 16, fontWeight: '600', color: '#666' },
  funcItem: { flexDirection: 'row', alignItems: 'center', padding: 14, borderBottomWidth: 1, borderBottomColor: '#f0f0f0', gap: 12 },
  funcItemText: { fontSize: 18, fontWeight: '700', color: '#1a237e', width: 36 },
  funcItemDesc: { fontSize: 16, color: '#666' },
});
