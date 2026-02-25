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
  Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { employeeAPI } from '../../services/api';
import { Employee } from '../../types';

const FUNCTIONS = [
  { code: 'E', name: 'Engenheiro / Engineer' },
  { code: 'SE', name: 'Especialista / Specialist' },
  { code: 'T', name: 'Técnico / Technician' },
  { code: 'M', name: 'Mecânico / Mechanic' },
  { code: 'W', name: 'Soldador / Welder' },
  { code: 'TK', name: 'Almoxarife / Tool Keeper' },
];

export default function EmployeesScreen() {
  const router = useRouter();
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [name, setName] = useState('');
  const [selectedFunction, setSelectedFunction] = useState('E');

  useEffect(() => {
    loadEmployees();
  }, []);

  const loadEmployees = async () => {
    try {
      const data = await employeeAPI.getAll();
      setEmployees(data);
    } catch (error: any) {
      Alert.alert('Erro', 'Erro ao carregar funcionários');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!name.trim()) {
      Alert.alert('Erro', 'Por favor, preencha o nome');
      return;
    }

    try {
      if (editingEmployee) {
        await employeeAPI.update(editingEmployee.id, name, selectedFunction);
      } else {
        await employeeAPI.create(name, selectedFunction);
      }
      setModalVisible(false);
      setName('');
      setSelectedFunction('E');
      setEditingEmployee(null);
      loadEmployees();
    } catch (error: any) {
      Alert.alert('Erro', 'Erro ao salvar funcionário');
    }
  };

  const handleEdit = (employee: Employee) => {
    setEditingEmployee(employee);
    setName(employee.name);
    setSelectedFunction(employee.function);
    setModalVisible(true);
  };

  const handleDelete = (employee: Employee) => {
    if (Platform.OS === 'web') {
      if (window.confirm(`Deseja excluir ${employee.name}?`)) {
        performDeleteEmployee(employee);
      }
    } else {
      Alert.alert(
        'Confirmar exclusão',
        `Deseja excluir ${employee.name}?`,
        [
          { text: 'Cancelar', style: 'cancel' },
          { text: 'Excluir', style: 'destructive', onPress: () => performDeleteEmployee(employee) },
        ]
      );
    }
  };

  const performDeleteEmployee = async (employee: Employee) => {
    try {
      await employeeAPI.delete(employee.id);
      loadEmployees();
    } catch (error: any) {
      Alert.alert('Erro', 'Erro ao excluir funcionário');
    }
  };

  const openAddModal = () => {
    setEditingEmployee(null);
    setName('');
    setSelectedFunction('E');
    setModalVisible(true);
  };

  const renderEmployee = ({ item }: { item: Employee }) => (
    <View style={styles.card}>
      <View style={styles.cardContent}>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{item.function}</Text>
        </View>
        <View style={styles.cardInfo}>
          <Text style={styles.cardTitle}>{item.name}</Text>
          <Text style={styles.cardSubtitle}>
            {FUNCTIONS.find((f) => f.code === item.function)?.name}
          </Text>
        </View>
      </View>
      <View style={styles.cardActions}>
        <TouchableOpacity onPress={() => handleEdit(item)} style={styles.actionButton}>
          <Ionicons name="pencil" size={20} color="#1a237e" />
        </TouchableOpacity>
        <TouchableOpacity onPress={() => handleDelete(item)} style={styles.actionButton}>
          <Ionicons name="trash" size={20} color="#d32f2f" />
        </TouchableOpacity>
      </View>
    </View>
  );

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
        <Text style={styles.title}>Funcionários</Text>
        <TouchableOpacity onPress={openAddModal} style={styles.addButton}>
          <Ionicons name="add" size={24} color="#fff" />
        </TouchableOpacity>
      </View>

      <FlatList
        data={employees}
        renderItem={renderEmployee}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Ionicons name="people-outline" size={64} color="#ccc" />
            <Text style={styles.emptyText}>Nenhum funcionário cadastrado</Text>
          </View>
        }
      />

      <Modal
        visible={modalVisible}
        animationType="slide"
        transparent
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>
              {editingEmployee ? 'Editar Funcionário' : 'Novo Funcionário'}
            </Text>

            <TextInput
              style={styles.input}
              placeholder="Nome"
              value={name}
              onChangeText={setName}
            />

            <Text style={styles.label}>Função:</Text>
            <View style={styles.functionsContainer}>
              {FUNCTIONS.map((func) => (
                <TouchableOpacity
                  key={func.code}
                  style={[
                    styles.functionChip,
                    selectedFunction === func.code && styles.functionChipSelected,
                  ]}
                  onPress={() => setSelectedFunction(func.code)}
                >
                  <Text
                    style={[
                      styles.functionChipText,
                      selectedFunction === func.code && styles.functionChipTextSelected,
                    ]}
                  >
                    {func.code} - {func.name.split('/')[0].trim()}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={[styles.modalButton, styles.cancelButton]}
                onPress={() => setModalVisible(false)}
              >
                <Text style={styles.cancelButtonText}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modalButton, styles.saveButton]}
                onPress={handleSave}
              >
                <Text style={styles.saveButtonText}>Salvar</Text>
              </TouchableOpacity>
            </View>
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
  addButton: {
    backgroundColor: '#1a237e',
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  listContent: {
    padding: 16,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  cardContent: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  badge: {
    backgroundColor: '#e3f2fd',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    marginRight: 12,
  },
  badgeText: {
    color: '#1a237e',
    fontWeight: '600',
    fontSize: 14,
  },
  cardInfo: {
    flex: 1,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#212121',
  },
  cardSubtitle: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  cardActions: {
    flexDirection: 'row',
    gap: 8,
  },
  actionButton: {
    padding: 8,
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 64,
  },
  emptyText: {
    fontSize: 16,
    color: '#999',
    marginTop: 16,
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
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#1a237e',
    marginBottom: 24,
  },
  input: {
    backgroundColor: '#f5f5f5',
    borderRadius: 8,
    padding: 16,
    fontSize: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
    color: '#212121',
    marginBottom: 12,
  },
  functionsContainer: {
    gap: 8,
    marginBottom: 24,
  },
  functionChip: {
    backgroundColor: '#f5f5f5',
    borderRadius: 8,
    padding: 12,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  functionChipSelected: {
    backgroundColor: '#e3f2fd',
    borderColor: '#1a237e',
  },
  functionChipText: {
    fontSize: 14,
    color: '#666',
  },
  functionChipTextSelected: {
    color: '#1a237e',
    fontWeight: '600',
  },
  modalButtons: {
    flexDirection: 'row',
    gap: 12,
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
  saveButton: {
    backgroundColor: '#1a237e',
  },
  saveButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
