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
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { serviceOrderAPI } from '../../services/api';
import { ServiceOrder } from '../../types';

export default function ServiceOrdersScreen() {
  const router = useRouter();
  const [serviceOrders, setServiceOrders] = useState<ServiceOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingSO, setEditingSO] = useState<ServiceOrder | null>(null);
  const [osNumber, setOsNumber] = useState('');
  const [client, setClient] = useState('');
  const [location, setLocation] = useState('');
  const [service, setService] = useState('');

  useEffect(() => {
    loadServiceOrders();
  }, []);

  const loadServiceOrders = async () => {
    try {
      const data = await serviceOrderAPI.getAll();
      setServiceOrders(data);
    } catch (error: any) {
      Alert.alert('Erro', 'Erro ao carregar ordens de serviço');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!osNumber.trim() || !client.trim() || !location.trim() || !service.trim()) {
      Alert.alert('Erro', 'Por favor, preencha todos os campos');
      return;
    }

    try {
      if (editingSO) {
        await serviceOrderAPI.update(editingSO.id, osNumber, client, location, service);
      } else {
        await serviceOrderAPI.create(osNumber, client, location, service);
      }
      setModalVisible(false);
      resetForm();
      loadServiceOrders();
    } catch (error: any) {
      Alert.alert('Erro', 'Erro ao salvar ordem de serviço');
    }
  };

  const resetForm = () => {
    setOsNumber('');
    setClient('');
    setLocation('');
    setService('');
    setEditingSO(null);
  };

  const handleEdit = (so: ServiceOrder) => {
    setEditingSO(so);
    setOsNumber(so.os_number);
    setClient(so.client);
    setLocation(so.location);
    setService(so.service);
    setModalVisible(true);
  };

  const handleDelete = (so: ServiceOrder) => {
    if (Platform.OS === 'web') {
      if (window.confirm(`Deseja excluir a O.S. ${so.os_number}?`)) {
        performDelete(so);
      }
    } else {
      Alert.alert(
        'Confirmar exclusão',
        `Deseja excluir a O.S. ${so.os_number}?`,
        [
          { text: 'Cancelar', style: 'cancel' },
          { text: 'Excluir', style: 'destructive', onPress: () => performDelete(so) },
        ]
      );
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

  const openAddModal = () => {
    resetForm();
    setModalVisible(true);
  };

  const renderServiceOrder = ({ item }: { item: ServiceOrder }) => (
    <View style={styles.card}>
      <View style={styles.cardContent}>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{item.os_number}</Text>
        </View>
        <View style={styles.cardInfo}>
          <Text style={styles.cardTitle}>{item.client}</Text>
          <Text style={styles.cardSubtitle}>{item.location}</Text>
          <Text style={styles.cardService}>{item.service}</Text>
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
        <Text style={styles.title}>Ordens de Serviço</Text>
        <TouchableOpacity onPress={openAddModal} style={styles.addButton}>
          <Ionicons name="add" size={24} color="#fff" />
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
            <Text style={styles.emptyText}>Nenhuma O.S. cadastrada</Text>
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
            <ScrollView>
              <Text style={styles.modalTitle}>
                {editingSO ? 'Editar O.S.' : 'Nova O.S.'}
              </Text>

              <TextInput
                style={styles.input}
                placeholder="Número da O.S."
                value={osNumber}
                onChangeText={setOsNumber}
              />

              <TextInput
                style={styles.input}
                placeholder="Cliente"
                value={client}
                onChangeText={setClient}
              />

              <TextInput
                style={styles.input}
                placeholder="Local"
                value={location}
                onChangeText={setLocation}
              />

              <TextInput
                style={[styles.input, styles.textArea]}
                placeholder="Serviço"
                value={service}
                onChangeText={setService}
                multiline
                numberOfLines={4}
              />

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
            </ScrollView>
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
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  cardContent: {
    flexDirection: 'row',
    alignItems: 'flex-start',
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
    fontSize: 12,
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
  cardService: {
    fontSize: 14,
    color: '#999',
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
    maxHeight: '80%',
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
  textArea: {
    minHeight: 100,
    textAlignVertical: 'top',
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
