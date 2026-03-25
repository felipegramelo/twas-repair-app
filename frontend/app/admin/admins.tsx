import React, { useState, useEffect } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, FlatList, Alert, TextInput, Modal,
  ActivityIndicator, ScrollView, KeyboardAvoidingView, Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { adminAPI, bmAPI } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import { User } from '../../types';

export default function AdminsScreen() {
  const router = useRouter();
  const { user: currentUser } = useAuth();
  const [admins, setAdmins] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingAdmin, setEditingAdmin] = useState<User | null>(null);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => { loadAdmins(); }, []);

  const loadAdmins = async () => {
    try {
      const data = await adminAPI.getAll();
      setAdmins(data);
    } catch {
      if (Platform.OS === 'web') window.alert('Erro ao carregar administradores');
      else Alert.alert('Erro', 'Erro ao carregar administradores');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setName(''); setEmail(''); setPassword(''); setEditingAdmin(null); setShowPassword(false);
  };

  const openAddModal = () => { resetForm(); setModalVisible(true); };

  const handleEdit = (admin: User) => {
    setEditingAdmin(admin); setName(admin.name); setEmail(admin.email); setPassword('');
    setModalVisible(true);
  };

  const handleSave = async () => {
    if (!name.trim() || !email.trim()) {
      if (Platform.OS === 'web') window.alert('Preencha nome e email');
      else Alert.alert('Erro', 'Preencha nome e email');
      return;
    }
    if (!editingAdmin && !password.trim()) {
      if (Platform.OS === 'web') window.alert('Defina uma senha');
      else Alert.alert('Erro', 'Defina uma senha');
      return;
    }
    if (password && password.length < 6) {
      if (Platform.OS === 'web') window.alert('A senha deve ter no mínimo 6 caracteres');
      else Alert.alert('Erro', 'A senha deve ter no mínimo 6 caracteres');
      return;
    }
    try {
      if (editingAdmin) {
        await adminAPI.update(editingAdmin.id, email, name, password || undefined);
      } else {
        await adminAPI.create(email, name, password);
      }
      setModalVisible(false); resetForm(); loadAdmins();
      const msg = editingAdmin ? 'Administrador atualizado' : 'Administrador cadastrado';
      if (Platform.OS === 'web') window.alert(msg);
      else Alert.alert('Sucesso', msg);
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || 'Erro ao salvar';
      if (Platform.OS === 'web') window.alert(errorMsg);
      else Alert.alert('Erro', errorMsg);
    }
  };

  const handleDelete = (admin: User) => {
    if (admin.id === currentUser?.id) {
      if (Platform.OS === 'web') window.alert('Você não pode excluir sua própria conta');
      else Alert.alert('Erro', 'Você não pode excluir sua própria conta');
      return;
    }
    if (Platform.OS === 'web') {
      if (window.confirm(`Excluir o administrador ${admin.name}?`)) performDelete(admin);
    } else {
      Alert.alert('Confirmar', `Excluir o administrador ${admin.name}?`, [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Excluir', style: 'destructive', onPress: () => performDelete(admin) },
      ]);
    }
  };

  const performDelete = async (admin: User) => {
    try {
      await adminAPI.delete(admin.id);
      loadAdmins();
    } catch (error: any) {
      const msg = error.response?.data?.detail || 'Erro ao excluir';
      if (Platform.OS === 'web') window.alert(msg);
      else Alert.alert('Erro', msg);
    }
  };

  const toggleBMAccess = async (admin: User) => {
    try {
      await bmAPI.toggleBMAccess(admin.id);
      loadAdmins();
    } catch { if (Platform.OS === 'web') window.alert('Erro ao alterar acesso'); }
  };

  const toggleOSArchiveAccess = async (admin: User) => {
    try {
      const response = await import('../../services/api').then(m => m.default.put(`/users/admins/${admin.id}/os-archive-access`));
      loadAdmins();
    } catch { if (Platform.OS === 'web') window.alert('Erro ao alterar acesso'); }
  };

  const renderAdmin = ({ item }: { item: User }) => (
    <View style={s.card} data-testid={`admin-card-${item.id}`}>
      <View style={s.cardContent}>
        <Ionicons name="shield-checkmark" size={40} color="#1a237e" style={{ marginRight: 12 }} />
        <View style={{ flex: 1 }}>
          <Text style={s.cardTitle}>{item.name}</Text>
          <Text style={s.cardSub}>{item.email}</Text>
          {item.id === currentUser?.id && <Text style={s.youBadge}>Você</Text>}
        </View>
      </View>
      <View style={s.permRow}>
        <TouchableOpacity style={[s.permBadge, item.bm_access && s.permActive]} onPress={() => toggleBMAccess(item)} data-testid={`toggle-bm-${item.id}`}>
          <Ionicons name="calculator" size={14} color={item.bm_access ? '#fff' : '#999'} />
          <Text style={[s.permText, item.bm_access && s.permTextActive]}>BM</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[s.permBadge, item.os_archive_access && s.permActive]} onPress={() => toggleOSArchiveAccess(item)} data-testid={`toggle-os-archive-${item.id}`}>
          <Ionicons name="folder-open" size={14} color={item.os_archive_access ? '#fff' : '#999'} />
          <Text style={[s.permText, item.os_archive_access && s.permTextActive]}>Arquivo O.S.</Text>
        </TouchableOpacity>
      </View>
      <View style={s.cardActions}>
        <TouchableOpacity onPress={() => handleEdit(item)} style={s.actionBtn} data-testid={`edit-admin-${item.id}`}>
          <Ionicons name="pencil" size={20} color="#1a237e" />
        </TouchableOpacity>
        {item.id !== currentUser?.id && (
          <TouchableOpacity onPress={() => handleDelete(item)} style={s.actionBtn} data-testid={`delete-admin-${item.id}`}>
            <Ionicons name="trash" size={20} color="#d32f2f" />
          </TouchableOpacity>
        )}
      </View>
    </View>
  );

  if (loading) return <View style={s.center}><ActivityIndicator size="large" color="#1a237e" /></View>;

  return (
    <SafeAreaView style={s.container}>
      <View style={s.header}>
        <TouchableOpacity onPress={() => router.back()} style={s.backBtn}>
          <Ionicons name="arrow-back" size={24} color="#1a237e" />
        </TouchableOpacity>
        <Text style={s.title}>Administradores</Text>
        <TouchableOpacity onPress={openAddModal} style={s.addBtn} data-testid="add-admin-btn">
          <Ionicons name="add" size={24} color="#fff" />
        </TouchableOpacity>
      </View>

      <FlatList
        data={admins}
        renderItem={renderAdmin}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ padding: 16 }}
        ListEmptyComponent={
          <View style={s.empty}>
            <Ionicons name="shield-outline" size={64} color="#ccc" />
            <Text style={s.emptyText}>Nenhum administrador cadastrado</Text>
          </View>
        }
      />

      <Modal visible={modalVisible} animationType="slide" transparent onRequestClose={() => setModalVisible(false)}>
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={s.modalOverlay}>
          <View style={s.modalContent}>
            <ScrollView showsVerticalScrollIndicator={false}>
              <Text style={s.modalTitle}>{editingAdmin ? 'Editar Administrador' : 'Novo Administrador'}</Text>

              <Text style={s.label}>Nome Completo *</Text>
              <TextInput style={s.input} placeholder="Ex: Maria Santos" value={name} onChangeText={setName} autoCapitalize="words" data-testid="admin-name-input" />

              <Text style={s.label}>Email *</Text>
              <TextInput style={s.input} placeholder="Ex: maria@twasrepair.com" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" data-testid="admin-email-input" />

              <Text style={s.label}>Senha {editingAdmin ? '(deixe em branco para não alterar)' : '*'}</Text>
              <View style={s.passRow}>
                <TextInput
                  style={s.passInput}
                  placeholder={editingAdmin ? 'Nova senha (opcional)' : 'Mínimo 6 caracteres'}
                  value={password} onChangeText={setPassword}
                  secureTextEntry={!showPassword} autoCapitalize="none"
                  data-testid="admin-password-input"
                />
                <TouchableOpacity onPress={() => setShowPassword(!showPassword)} style={s.eyeBtn}>
                  <Ionicons name={showPassword ? 'eye-off' : 'eye'} size={20} color="#666" />
                </TouchableOpacity>
              </View>
              {editingAdmin && <Text style={s.helpText}>Deixe a senha em branco se não quiser alterá-la</Text>}

              <View style={s.modalBtns}>
                <TouchableOpacity style={[s.modalBtn, s.cancelBtn]} onPress={() => { setModalVisible(false); resetForm(); }}>
                  <Text style={s.cancelText}>Cancelar</Text>
                </TouchableOpacity>
                <TouchableOpacity style={[s.modalBtn, s.saveBtn]} onPress={handleSave} data-testid="save-admin-btn">
                  <Text style={s.saveText}>Salvar</Text>
                </TouchableOpacity>
              </View>
            </ScrollView>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 12, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#e0e0e0' },
  backBtn: { padding: 8 },
  title: { fontSize: 20, fontWeight: '600', color: '#1a237e' },
  addBtn: { backgroundColor: '#1a237e', width: 40, height: 40, borderRadius: 20, justifyContent: 'center', alignItems: 'center' },
  card: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.1, shadowRadius: 2, elevation: 2 },
  cardContent: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  cardTitle: { fontSize: 16, fontWeight: '600', color: '#212121' },
  cardSub: { fontSize: 14, color: '#666', marginTop: 4 },
  youBadge: { fontSize: 11, color: '#1a237e', fontWeight: '700', marginTop: 4 },
  permRow: { flexDirection: 'row', gap: 8, marginTop: 8, marginBottom: 8 },
  permBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 10, paddingVertical: 5, borderRadius: 16, backgroundColor: '#f0f0f0', borderWidth: 1, borderColor: '#ddd' },
  permActive: { backgroundColor: '#1a237e', borderColor: '#1a237e' },
  permText: { fontSize: 12, color: '#999', fontWeight: '600' },
  permTextActive: { color: '#fff' },
  cardActions: { flexDirection: 'row', gap: 8 },
  actionBtn: { padding: 8 },
  empty: { alignItems: 'center', paddingVertical: 64 },
  emptyText: { fontSize: 16, color: '#999', marginTop: 16 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modalContent: { backgroundColor: '#fff', borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 24, maxHeight: '90%' },
  modalTitle: { fontSize: 20, fontWeight: '600', color: '#1a237e', marginBottom: 24 },
  label: { fontSize: 14, fontWeight: '600', color: '#212121', marginBottom: 8, marginTop: 12 },
  input: { backgroundColor: '#f5f5f5', borderRadius: 8, padding: 16, fontSize: 16, borderWidth: 1, borderColor: '#e0e0e0' },
  passRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#f5f5f5', borderRadius: 8, borderWidth: 1, borderColor: '#e0e0e0' },
  passInput: { flex: 1, padding: 16, fontSize: 16 },
  eyeBtn: { padding: 16 },
  helpText: { fontSize: 12, color: '#666', marginTop: 8, fontStyle: 'italic' },
  modalBtns: { flexDirection: 'row', gap: 12, marginTop: 24 },
  modalBtn: { flex: 1, height: 48, borderRadius: 8, justifyContent: 'center', alignItems: 'center' },
  cancelBtn: { backgroundColor: '#f5f5f5' },
  cancelText: { color: '#666', fontSize: 16, fontWeight: '600' },
  saveBtn: { backgroundColor: '#1a237e' },
  saveText: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
