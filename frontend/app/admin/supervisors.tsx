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
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { supervisorAPI, adminAPI } from '../../services/api';
import { User } from '../../types';

export default function SupervisorsScreen() {
  const router = useRouter();
  const [supervisors, setSupervisors] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingSupervisor, setEditingSupervisor] = useState<User | null>(null);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [resetModalVisible, setResetModalVisible] = useState(false);
  const [resetTarget, setResetTarget] = useState<User | null>(null);
  const [resetPassword, setResetPassword] = useState('');
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    loadSupervisors();
  }, []);

  const loadSupervisors = async () => {
    try {
      const data = await supervisorAPI.getAll();
      setSupervisors(data);
    } catch (error: any) {
      Alert.alert('Erro', 'Erro ao carregar supervisores');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!name.trim() || !email.trim()) {
      Alert.alert('Erro', 'Por favor, preencha nome e email');
      return;
    }

    if (!editingSupervisor && !password.trim()) {
      Alert.alert('Erro', 'Por favor, defina uma senha');
      return;
    }

    if (password && password.length < 6) {
      Alert.alert('Erro', 'A senha deve ter no mínimo 6 caracteres');
      return;
    }

    try {
      if (editingSupervisor) {
        await supervisorAPI.update(editingSupervisor.id, email, name, password || undefined);
      } else {
        await supervisorAPI.create(email, name, password);
      }
      setModalVisible(false);
      resetForm();
      loadSupervisors();
      Alert.alert('Sucesso', editingSupervisor ? 'Supervisor atualizado' : 'Supervisor cadastrado');
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || 'Erro ao salvar supervisor';
      Alert.alert('Erro', errorMsg);
    }
  };

  const resetForm = () => {
    setName('');
    setEmail('');
    setPassword('');
    setEditingSupervisor(null);
    setShowPassword(false);
  };

  const handleEdit = (supervisor: User) => {
    setEditingSupervisor(supervisor);
    setName(supervisor.name);
    setEmail(supervisor.email);
    setPassword('');
    setModalVisible(true);
  };

  const handleDelete = (supervisor: User) => {
    if (Platform.OS === 'web') {
      if (window.confirm(`Deseja excluir o supervisor ${supervisor.name}?`)) {
        performDeleteSupervisor(supervisor);
      }
    } else {
      Alert.alert(
        'Confirmar exclusão',
        `Deseja excluir o supervisor ${supervisor.name}?`,
        [
          { text: 'Cancelar', style: 'cancel' },
          { text: 'Excluir', style: 'destructive', onPress: () => performDeleteSupervisor(supervisor) },
        ]
      );
    }
  };

  const performDeleteSupervisor = async (supervisor: User) => {
    try {
      await supervisorAPI.delete(supervisor.id);
      loadSupervisors();
    } catch (error: any) {
      Alert.alert('Erro', 'Erro ao excluir supervisor');
    }
  };

  const openAddModal = () => {
    resetForm();
    setModalVisible(true);
  };

  const openResetPasswordModal = (supervisor: User) => {
    setResetTarget(supervisor);
    setResetPassword('');
    setShowResetPassword(false);
    setResetModalVisible(true);
  };

  const handleResetPassword = async () => {
    if (!resetTarget) return;
    if (!resetPassword.trim() || resetPassword.length < 6) {
      if (Platform.OS === 'web') window.alert('A senha deve ter no minimo 6 caracteres');
      else Alert.alert('Erro', 'A senha deve ter no minimo 6 caracteres');
      return;
    }
    setResetting(true);
    try {
      await adminAPI.resetUserPassword(resetTarget.id, resetPassword);
      setResetModalVisible(false);
      if (Platform.OS === 'web') window.alert(`Senha de ${resetTarget.name} redefinida com sucesso!`);
      else Alert.alert('Sucesso', `Senha de ${resetTarget.name} redefinida com sucesso!`);
    } catch (error: any) {
      const msg = error.response?.data?.detail || 'Erro ao redefinir senha';
      if (Platform.OS === 'web') window.alert(msg);
      else Alert.alert('Erro', msg);
    } finally {
      setResetting(false);
    }
  };

  const renderSupervisor = ({ item }: { item: User }) => (
    <View style={styles.card}>
      <View style={styles.cardContent}>
        <View style={styles.iconContainer}>
          <Ionicons name="person-circle" size={40} color="#1a237e" />
        </View>
        <View style={styles.cardInfo}>
          <Text style={styles.cardTitle}>{item.name}</Text>
          <Text style={styles.cardSubtitle}>{item.email}</Text>
        </View>
      </View>
      <View style={styles.cardActions}>
        <TouchableOpacity onPress={() => openResetPasswordModal(item)} style={styles.actionButton} data-testid={`reset-pwd-btn-${item.id}`}>
          <Ionicons name="key" size={20} color="#ff9800" />
        </TouchableOpacity>
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
        <Text style={styles.title}>Supervisores</Text>
        <TouchableOpacity onPress={openAddModal} style={styles.addButton}>
          <Ionicons name="add" size={24} color="#fff" />
        </TouchableOpacity>
      </View>

      <FlatList
        data={supervisors}
        renderItem={renderSupervisor}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Ionicons name="people-outline" size={64} color="#ccc" />
            <Text style={styles.emptyText}>Nenhum supervisor cadastrado</Text>
            <Text style={styles.emptySubtext}>Clique no + para adicionar</Text>
          </View>
        }
      />

      <Modal
        visible={modalVisible}
        animationType="slide"
        transparent
        onRequestClose={() => setModalVisible(false)}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={styles.modalOverlay}
        >
          <View style={styles.modalContent}>
            <ScrollView showsVerticalScrollIndicator={false}>
              <Text style={styles.modalTitle}>
                {editingSupervisor ? 'Editar Supervisor' : 'Novo Supervisor'}
              </Text>

              <Text style={styles.inputLabel}>Nome Completo *</Text>
              <TextInput
                style={styles.input}
                placeholder="Ex: João Silva"
                value={name}
                onChangeText={setName}
                autoCapitalize="words"
              />

              <Text style={styles.inputLabel}>Email Corporativo *</Text>
              <TextInput
                style={styles.input}
                placeholder="Ex: joao@twasrepair.com"
                value={email}
                onChangeText={setEmail}
                keyboardType="email-address"
                autoCapitalize="none"
                autoComplete="email"
              />

              <Text style={styles.inputLabel}>
                Senha {editingSupervisor ? '(deixe em branco para não alterar)' : '*'}
              </Text>
              <View style={styles.passwordContainer}>
                <TextInput
                  style={styles.passwordInput}
                  placeholder={editingSupervisor ? 'Nova senha (opcional)' : 'Mínimo 6 caracteres'}
                  value={password}
                  onChangeText={setPassword}
                  secureTextEntry={!showPassword}
                  autoCapitalize="none"
                />
                <TouchableOpacity
                  onPress={() => setShowPassword(!showPassword)}
                  style={styles.eyeButton}
                >
                  <Ionicons
                    name={showPassword ? 'eye-off' : 'eye'}
                    size={20}
                    color="#666"
                  />
                </TouchableOpacity>
              </View>

              {editingSupervisor && (
                <Text style={styles.helpText}>
                  Deixe a senha em branco se não quiser alterá-la
                </Text>
              )}

              <View style={styles.modalButtons}>
                <TouchableOpacity
                  style={[styles.modalButton, styles.cancelButton]}
                  onPress={() => {
                    setModalVisible(false);
                    resetForm();
                  }}
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
        </KeyboardAvoidingView>
      </Modal>

      {/* Reset Password Modal */}
      <Modal
        visible={resetModalVisible}
        animationType="slide"
        transparent
        onRequestClose={() => setResetModalVisible(false)}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={styles.modalOverlay}
        >
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Redefinir Senha</Text>
            {resetTarget && (
              <Text style={{ fontSize: 14, color: '#666', marginBottom: 16, textAlign: 'center' }}>
                Supervisor: {resetTarget.name}
              </Text>
            )}

            <Text style={styles.inputLabel}>Nova Senha *</Text>
            <View style={styles.passwordContainer}>
              <TextInput
                style={styles.passwordInput}
                placeholder="Minimo 6 caracteres"
                value={resetPassword}
                onChangeText={setResetPassword}
                secureTextEntry={!showResetPassword}
                autoCapitalize="none"
                data-testid="reset-password-input"
              />
              <TouchableOpacity
                onPress={() => setShowResetPassword(!showResetPassword)}
                style={styles.eyeButton}
              >
                <Ionicons
                  name={showResetPassword ? 'eye-off' : 'eye'}
                  size={20}
                  color="#666"
                />
              </TouchableOpacity>
            </View>

            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={[styles.modalButton, styles.cancelButton]}
                onPress={() => setResetModalVisible(false)}
              >
                <Text style={styles.cancelButtonText}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modalButton, styles.saveButton, resetting && { opacity: 0.6 }]}
                onPress={handleResetPassword}
                disabled={resetting}
                data-testid="confirm-reset-password-btn"
              >
                {resetting ? (
                  <ActivityIndicator color="#fff" size="small" />
                ) : (
                  <Text style={styles.saveButtonText}>Redefinir</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
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
  iconContainer: {
    marginRight: 12,
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
  emptySubtext: {
    fontSize: 14,
    color: '#ccc',
    marginTop: 8,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 24,
    maxHeight: '90%',
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#1a237e',
    marginBottom: 24,
  },
  inputLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#212121',
    marginBottom: 8,
    marginTop: 12,
  },
  input: {
    backgroundColor: '#f5f5f5',
    borderRadius: 8,
    padding: 16,
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  passwordContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  passwordInput: {
    flex: 1,
    padding: 16,
    fontSize: 16,
  },
  eyeButton: {
    padding: 16,
  },
  helpText: {
    fontSize: 12,
    color: '#666',
    marginTop: 8,
    fontStyle: 'italic',
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
  saveButton: {
    backgroundColor: '#1a237e',
  },
  saveButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
