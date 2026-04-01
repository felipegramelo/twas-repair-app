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
const FUNC_LABELS: Record<string, string> = { 'E': 'Engenheiro', 'EN': 'Encarregado', 'Sup': 'Supervisor', 'T': 'Técnico', 'M': 'Mecânico', 'TS': 'Téc. Segurança' };

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
  const [embarcacao, setEmbarcacao] = useState('');
  const [service, setService] = useState('');
  const [soEmployees, setSOEmployees] = useState<SOEmployee[]>([]);
  const [employeePickerVisible, setEmployeePickerVisible] = useState(false);
  const [funcPickerVisible, setFuncPickerVisible] = useState(false);
  const [editingEmpIndex, setEditingEmpIndex] = useState<number | null>(null);

  // Multi-select state
  const [selectedNewEmps, setSelectedNewEmps] = useState<string[]>([]);
  const [bulkFuncPickerVisible, setBulkFuncPickerVisible] = useState(false);

  // Filters
  const now = new Date();
  const [filterMonth, setFilterMonth] = useState(now.getMonth() + 1);
  const [filterYear, setFilterYear] = useState(now.getFullYear());
  const [filterPickerVisible, setFilterPickerVisible] = useState(false);

  useEffect(() => { loadData(); }, [filterMonth, filterYear]);

  const loadData = async () => {
    try {
      const m = filterMonth === 0 ? undefined : filterMonth;
      const [soData, empData] = await Promise.all([serviceOrderAPI.getAll(m, filterYear), employeeAPI.getAll()]);
      setServiceOrders(soData); setAllEmployees(empData);
    } catch { if (Platform.OS === 'web') window.alert('Erro ao carregar dados'); else Alert.alert('Erro', 'Erro ao carregar dados'); }
    finally { setLoading(false); }
  };

  const loadServiceOrders = async () => {
    try {
      const m = filterMonth === 0 ? undefined : filterMonth;
      setServiceOrders(await serviceOrderAPI.getAll(m, filterYear));
    } catch {}
  };

  const openAdd = () => {
    setEditingSO(null); setOsNumber(''); setClient(''); setLocation(''); setEmbarcacao(''); setService(''); setSOEmployees([]);
    setModalVisible(true);
  };

  const openEdit = (so: ServiceOrder) => {
    setEditingSO(so); setOsNumber(so.os_number); setClient(so.client); setLocation(so.location); setEmbarcacao(so.embarcacao || ''); setService(so.service);
    setSOEmployees(so.employees || []);
    setModalVisible(true);
  };

  const handleSave = async () => {
    if (!osNumber || !client || !service) {
      if (Platform.OS === 'web') window.alert('Preencha todos os campos obrigatorios');
      else Alert.alert('Erro', 'Preencha todos os campos obrigatorios');
      return;
    }
    try {
      if (editingSO) await serviceOrderAPI.update(editingSO.id, osNumber, client, location, service, soEmployees, embarcacao);
      else await serviceOrderAPI.create(osNumber, client, location, service, soEmployees, embarcacao);
      setModalVisible(false); loadServiceOrders();
    } catch {
      if (Platform.OS === 'web') window.alert('Erro ao salvar');
      else Alert.alert('Erro', 'Erro ao salvar');
    }
  };

  const handleDelete = (so: ServiceOrder) => {
    if (Platform.OS === 'web') { if (window.confirm(`Excluir O.S. ${so.os_number}?`)) performDelete(so); }
    else { Alert.alert('Confirmar', `Excluir O.S. ${so.os_number}?`, [{ text: 'Cancelar', style: 'cancel' }, { text: 'Excluir', style: 'destructive', onPress: () => performDelete(so) }]); }
  };

  const performDelete = async (so: ServiceOrder) => {
    try { await serviceOrderAPI.delete(so.id); loadServiceOrders(); } catch {
      if (Platform.OS === 'web') window.alert('Erro ao excluir');
      else Alert.alert('Erro', 'Erro ao excluir');
    }
  };

  // Toggle single employee selection in picker
  const toggleEmpSelection = (empId: string) => {
    setSelectedNewEmps(prev =>
      prev.includes(empId) ? prev.filter(id => id !== empId) : [...prev, empId]
    );
  };

  // Select all available employees
  const selectAllEmployees = () => {
    const available = allEmployees.filter(e => !soEmployees.find(se => se.employee_id === e.id)).map(e => e.id);
    if (selectedNewEmps.length === available.length) {
      setSelectedNewEmps([]);
    } else {
      setSelectedNewEmps(available);
    }
  };

  // Add selected employees and open bulk function picker
  const confirmAddEmployees = () => {
    if (selectedNewEmps.length === 0) return;
    setBulkFuncPickerVisible(true);
  };

  // Set function for all newly selected employees and add them
  const addSelectedWithFunction = (func: string) => {
    const newEmps: SOEmployee[] = selectedNewEmps.map(empId => ({ employee_id: empId, function: func }));
    setSOEmployees([...soEmployees, ...newEmps]);
    setSelectedNewEmps([]);
    setBulkFuncPickerVisible(false);
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

  const availableEmployees = allEmployees.filter(e => !soEmployees.find(se => se.employee_id === e.id));
  const allSelected = availableEmployees.length > 0 && selectedNewEmps.length === availableEmployees.length;

  const MONTHS_SO = [
    { value: 0, label: 'Todos' }, { value: 1, label: 'Jan' }, { value: 2, label: 'Fev' }, { value: 3, label: 'Mar' },
    { value: 4, label: 'Abr' }, { value: 5, label: 'Mai' }, { value: 6, label: 'Jun' },
    { value: 7, label: 'Jul' }, { value: 8, label: 'Ago' }, { value: 9, label: 'Set' },
    { value: 10, label: 'Out' }, { value: 11, label: 'Nov' }, { value: 12, label: 'Dez' },
  ];
  const getFilterLabel = () => {
    const monthLabel = MONTHS_SO.find(m => m.value === filterMonth)?.label || 'Todos';
    return filterMonth === 0 ? `${filterYear}` : `${monthLabel}/${filterYear}`;
  };

  if (loading) return <View style={s.center}><ActivityIndicator size="large" color="#1a237e" /></View>;

  return (
    <SafeAreaView style={s.container}>
      <View style={s.header}>
        <TouchableOpacity onPress={() => router.back()} style={s.btn}><Ionicons name="arrow-back" size={24} color="#1a237e" /></TouchableOpacity>
        <Text style={s.title}>Ordens de Serviço</Text>
        <TouchableOpacity onPress={openAdd} style={s.btn}><Ionicons name="add" size={28} color="#1a237e" /></TouchableOpacity>
      </View>

      {/* Filter Bar */}
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 10, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#e8e8e8' }}>
        <TouchableOpacity style={{ flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: '#E8EAF6', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8 }} onPress={() => setFilterPickerVisible(true)} data-testid="so-filter-btn">
          <Ionicons name="calendar" size={18} color="#1a237e" />
          <Text style={{ fontSize: 14, fontWeight: '600', color: '#1a237e' }}>{getFilterLabel()}</Text>
          <Ionicons name="chevron-down" size={16} color="#1a237e" />
        </TouchableOpacity>
        <Text style={{ fontSize: 13, color: '#666' }}>{serviceOrders.length} O.S.</Text>
      </View>

      <FlatList
        data={serviceOrders} keyExtractor={i => i.id} contentContainerStyle={{ padding: 16 }}
        renderItem={({ item }) => (
          <View style={s.card}>
            <TouchableOpacity style={s.cardContent} onPress={() => openEdit(item)}>
              <View style={s.badge}><Text style={s.badgeText}>{item.os_number}</Text></View>
              <View style={{ flex: 1 }}>
                <Text style={s.cardTitle}>{item.client}</Text>
                {item.embarcacao ? <Text style={s.cardSub}>{item.embarcacao}</Text> : null}
                {item.location ? <Text style={s.cardSub}>{item.location}</Text> : null}
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
          <Text style={s.label}>Embarcacao</Text>
          <TextInput style={s.input} value={embarcacao} onChangeText={setEmbarcacao} placeholder="Ex: Plataforma P-71" />
          <Text style={s.label}>Local</Text>
          <TextInput style={s.input} value={location} onChangeText={setLocation} placeholder="Local do servico" />
          <Text style={s.label}>Serviço *</Text>
          <TextInput style={s.input} value={service} onChangeText={setService} placeholder="Descrição" />

          <View style={s.sectionHeader}>
            <Text style={s.label}>Funcionários ({soEmployees.length})</Text>
            <TouchableOpacity onPress={() => { setSelectedNewEmps([]); setEmployeePickerVisible(true); }} style={s.addEmpBtn}>
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

      {/* Employee Picker with Multi-select */}
      <Modal visible={employeePickerVisible} animationType="slide" transparent onRequestClose={() => setEmployeePickerVisible(false)}>
        <View style={s.modalOverlay}><View style={s.modalContent}>
          <Text style={s.modalTitle}>Selecionar Funcionários</Text>

          {availableEmployees.length > 0 && (
            <TouchableOpacity style={s.selectAllRow} onPress={selectAllEmployees}>
              <View style={[s.checkbox, allSelected && s.checkboxChecked]}>
                {allSelected && <Ionicons name="checkmark" size={16} color="#fff" />}
              </View>
              <Text style={s.selectAllText}>Selecionar Todos ({availableEmployees.length})</Text>
            </TouchableOpacity>
          )}

          <ScrollView style={{ maxHeight: 350 }}>
            {availableEmployees.map(emp => {
              const isSelected = selectedNewEmps.includes(emp.id);
              return (
                <TouchableOpacity key={emp.id} style={s.pickerItem} onPress={() => toggleEmpSelection(emp.id)}>
                  <View style={[s.checkbox, isSelected && s.checkboxChecked]}>
                    {isSelected && <Ionicons name="checkmark" size={16} color="#fff" />}
                  </View>
                  <Text style={[s.pickerItemText, isSelected && { color: '#1a237e', fontWeight: '600' }]}>{emp.name}</Text>
                </TouchableOpacity>
              );
            })}
            {availableEmployees.length === 0 && (
              <Text style={s.emptyText}>Todos os funcionários já foram adicionados</Text>
            )}
          </ScrollView>

          <View style={[s.modalBtns, { marginTop: 16 }]}>
            <TouchableOpacity style={[s.modalBtn, s.cancelBtn]} onPress={() => setEmployeePickerVisible(false)}>
              <Text style={s.cancelText}>Fechar</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[s.modalBtn, s.saveBtn, selectedNewEmps.length === 0 && { opacity: 0.4 }]}
              onPress={confirmAddEmployees}
              disabled={selectedNewEmps.length === 0}
            >
              <Text style={s.saveText}>Adicionar ({selectedNewEmps.length})</Text>
            </TouchableOpacity>
          </View>
        </View></View>
      </Modal>

      {/* Bulk Function Picker - after selecting employees */}
      <Modal visible={bulkFuncPickerVisible} animationType="fade" transparent onRequestClose={() => setBulkFuncPickerVisible(false)}>
        <View style={s.modalOverlay}><View style={[s.modalContent, { maxWidth: 320, alignSelf: 'center' }]}>
          <Text style={s.modalTitle}>Função para {selectedNewEmps.length} funcionário(s)</Text>
          <Text style={{ fontSize: 13, color: '#666', marginBottom: 12 }}>Selecione a função. Você pode alterar individualmente depois.</Text>
          {FUNCTIONS.map(f => (
            <TouchableOpacity key={f} style={s.funcItem} onPress={() => addSelectedWithFunction(f)}>
              <Text style={s.funcItemText}>{f}</Text>
              <Text style={s.funcItemDesc}>{FUNC_LABELS[f]}</Text>
            </TouchableOpacity>
          ))}
          <TouchableOpacity style={[s.closeBtn, { marginTop: 12 }]} onPress={() => setBulkFuncPickerVisible(false)}>
            <Text style={s.closeBtnText}>Cancelar</Text>
          </TouchableOpacity>
        </View></View>
      </Modal>

      {/* Individual Function Picker */}
      <Modal visible={funcPickerVisible} animationType="fade" transparent onRequestClose={() => setFuncPickerVisible(false)}>
        <View style={s.modalOverlay}><View style={[s.modalContent, { maxWidth: 300, alignSelf: 'center' }]}>
          <Text style={s.modalTitle}>Selecionar Funcao</Text>
          {FUNCTIONS.map(f => (
            <TouchableOpacity key={f} style={s.funcItem} onPress={() => setEmployeeFunc(f)}>
              <Text style={s.funcItemText}>{f}</Text>
              <Text style={s.funcItemDesc}>{FUNC_LABELS[f]}</Text>
            </TouchableOpacity>
          ))}
        </View></View>
      </Modal>

      {/* Filter Picker Modal */}
      <Modal visible={filterPickerVisible} animationType="fade" transparent onRequestClose={() => setFilterPickerVisible(false)}>
        <View style={s.modalOverlay}><View style={[s.modalContent, { maxWidth: 340, alignSelf: 'center' }]}>
          <Text style={s.modalTitle}>Filtrar por Periodo</Text>
          <Text style={s.label}>Ano</Text>
          <View style={{ flexDirection: 'row', gap: 8 }}>
            {[2025, 2026, 2027].map(y => (
              <TouchableOpacity key={y} style={{ flex: 1, paddingVertical: 10, borderRadius: 8, backgroundColor: filterYear === y ? '#1a237e' : '#f5f5f5', alignItems: 'center' }} onPress={() => setFilterYear(y)}>
                <Text style={{ fontSize: 15, fontWeight: '600', color: filterYear === y ? '#fff' : '#666' }}>{y}</Text>
              </TouchableOpacity>
            ))}
          </View>
          <Text style={[s.label, { marginTop: 12 }]}>Mes</Text>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
            {MONTHS_SO.map(m => (
              <TouchableOpacity key={m.value} style={{ width: '22%', paddingVertical: 8, borderRadius: 6, backgroundColor: filterMonth === m.value ? '#1a237e' : '#f5f5f5', alignItems: 'center' }} onPress={() => setFilterMonth(m.value)}>
                <Text style={{ fontSize: 13, fontWeight: '600', color: filterMonth === m.value ? '#fff' : '#666' }}>{m.label}</Text>
              </TouchableOpacity>
            ))}
          </View>
          <TouchableOpacity style={[s.modalBtn, s.saveBtn, { marginTop: 16 }]} onPress={() => setFilterPickerVisible(false)}>
            <Text style={s.saveText}>Aplicar</Text>
          </TouchableOpacity>
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
  selectAllRow: { flexDirection: 'row', alignItems: 'center', padding: 14, borderBottomWidth: 2, borderBottomColor: '#1a237e', marginBottom: 4, gap: 12 },
  selectAllText: { fontSize: 16, fontWeight: '700', color: '#1a237e' },
  checkbox: { width: 24, height: 24, borderRadius: 4, borderWidth: 2, borderColor: '#bdbdbd', justifyContent: 'center', alignItems: 'center' },
  checkboxChecked: { backgroundColor: '#1a237e', borderColor: '#1a237e' },
  pickerItem: { flexDirection: 'row', alignItems: 'center', padding: 14, borderBottomWidth: 1, borderBottomColor: '#f0f0f0', gap: 12 },
  pickerItemText: { fontSize: 16, color: '#212121' },
  closeBtn: { backgroundColor: '#f5f5f5', height: 48, borderRadius: 8, justifyContent: 'center', alignItems: 'center', marginTop: 16 },
  closeBtnText: { fontSize: 16, fontWeight: '600', color: '#666' },
  funcItem: { flexDirection: 'row', alignItems: 'center', padding: 14, borderBottomWidth: 1, borderBottomColor: '#f0f0f0', gap: 12 },
  funcItemText: { fontSize: 18, fontWeight: '700', color: '#1a237e', width: 36 },
  funcItemDesc: { fontSize: 16, color: '#666' },
});
