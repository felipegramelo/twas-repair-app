import React, { useState, useEffect } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, FlatList, Alert, TextInput, Modal, ActivityIndicator, Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { employeeAPI } from '../../services/api';
import { Employee } from '../../types';

export default function EmployeesScreen() {
  const router = useRouter();
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [name, setName] = useState('');

  useEffect(() => { loadEmployees(); }, []);

  const loadEmployees = async () => {
    try { setEmployees(await employeeAPI.getAll()); }
    catch { Alert.alert('Erro', 'Erro ao carregar funcionários'); }
    finally { setLoading(false); }
  };

  const handleSave = async () => {
    if (!name.trim()) { Alert.alert('Erro', 'Preencha o nome'); return; }
    try {
      if (editingEmployee) { await employeeAPI.update(editingEmployee.id, name); }
      else { await employeeAPI.create(name); }
      setModalVisible(false); setName(''); setEditingEmployee(null); loadEmployees();
    } catch { Alert.alert('Erro', 'Erro ao salvar funcionário'); }
  };

  const handleEdit = (emp: Employee) => { setEditingEmployee(emp); setName(emp.name); setModalVisible(true); };

  const handleDelete = (emp: Employee) => {
    if (Platform.OS === 'web') { if (window.confirm(`Excluir ${emp.name}?`)) performDelete(emp); }
    else { Alert.alert('Confirmar', `Excluir ${emp.name}?`, [{ text: 'Cancelar', style: 'cancel' }, { text: 'Excluir', style: 'destructive', onPress: () => performDelete(emp) }]); }
  };

  const performDelete = async (emp: Employee) => {
    try { await employeeAPI.delete(emp.id); loadEmployees(); }
    catch { Alert.alert('Erro', 'Erro ao excluir'); }
  };

  const openAdd = () => { setEditingEmployee(null); setName(''); setModalVisible(true); };

  if (loading) return <View style={s.center}><ActivityIndicator size="large" color="#1a237e" /></View>;

  return (
    <SafeAreaView style={s.container}>
      <View style={s.header}>
        <TouchableOpacity onPress={() => router.back()} style={s.btn}><Ionicons name="arrow-back" size={24} color="#1a237e" /></TouchableOpacity>
        <Text style={s.title}>Funcionários</Text>
        <TouchableOpacity onPress={openAdd} style={s.btn}><Ionicons name="add" size={28} color="#1a237e" /></TouchableOpacity>
      </View>
      <FlatList
        data={employees} keyExtractor={i => i.id} contentContainerStyle={{ padding: 16 }}
        renderItem={({ item }) => (
          <View style={s.card}>
            <TouchableOpacity style={s.cardContent} onPress={() => handleEdit(item)}>
              <Text style={s.cardTitle}>{item.name}</Text>
            </TouchableOpacity>
            <View style={s.actions}>
              <TouchableOpacity onPress={() => handleEdit(item)} style={s.actionBtn}><Ionicons name="pencil" size={20} color="#1a237e" /></TouchableOpacity>
              <TouchableOpacity onPress={() => handleDelete(item)} style={s.actionBtn}><Ionicons name="trash-outline" size={20} color="#d32f2f" /></TouchableOpacity>
            </View>
          </View>
        )}
        ListEmptyComponent={<View style={s.empty}><Ionicons name="people-outline" size={64} color="#ccc" /><Text style={s.emptyText}>Nenhum funcionário</Text></View>}
      />
      <Modal visible={modalVisible} animationType="slide" transparent onRequestClose={() => setModalVisible(false)}>
        <View style={s.modalOverlay}>
          <View style={s.modalContent}>
            <Text style={s.modalTitle}>{editingEmployee ? 'Editar' : 'Novo'} Funcionário</Text>
            <Text style={s.label}>Nome *</Text>
            <TextInput style={s.input} value={name} onChangeText={setName} placeholder="Nome completo" />
            <View style={s.modalBtns}>
              <TouchableOpacity style={[s.modalBtn, s.cancelBtn]} onPress={() => setModalVisible(false)}><Text style={s.cancelText}>Cancelar</Text></TouchableOpacity>
              <TouchableOpacity style={[s.modalBtn, s.saveBtn]} onPress={handleSave}><Text style={s.saveText}>Salvar</Text></TouchableOpacity>
            </View>
          </View>
        </View>
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
  card: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 12, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', elevation: 2 },
  cardContent: { flex: 1 },
  cardTitle: { fontSize: 16, fontWeight: '600', color: '#212121' },
  actions: { flexDirection: 'row', gap: 4 },
  actionBtn: { padding: 8 },
  empty: { alignItems: 'center', paddingVertical: 64 },
  emptyText: { fontSize: 16, color: '#999', marginTop: 16 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', padding: 16 },
  modalContent: { backgroundColor: '#fff', borderRadius: 16, padding: 24 },
  modalTitle: { fontSize: 20, fontWeight: '600', color: '#1a237e', marginBottom: 16 },
  label: { fontSize: 14, fontWeight: '600', color: '#212121', marginBottom: 8 },
  input: { backgroundColor: '#fff', borderRadius: 8, padding: 14, fontSize: 16, borderWidth: 1, borderColor: '#e0e0e0' },
  modalBtns: { flexDirection: 'row', gap: 12, marginTop: 24 },
  modalBtn: { flex: 1, height: 48, borderRadius: 8, justifyContent: 'center', alignItems: 'center' },
  cancelBtn: { backgroundColor: '#f5f5f5' },
  cancelText: { color: '#666', fontSize: 16, fontWeight: '600' },
  saveBtn: { backgroundColor: '#1a237e' },
  saveText: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
