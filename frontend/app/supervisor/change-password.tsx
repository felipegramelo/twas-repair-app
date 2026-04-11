import React, { useState } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, TextInput, Alert, Platform, ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { adminAPI } from '../../services/api';

export default function SupervisorChangePasswordScreen() {
  const router = useRouter();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleChangePassword = async () => {
    if (!currentPassword || !newPassword || !confirmPassword) {
      if (Platform.OS === 'web') window.alert('Preencha todos os campos');
      else Alert.alert('Erro', 'Preencha todos os campos');
      return;
    }
    if (newPassword.length < 6) {
      if (Platform.OS === 'web') window.alert('A nova senha deve ter no minimo 6 caracteres');
      else Alert.alert('Erro', 'A nova senha deve ter no minimo 6 caracteres');
      return;
    }
    if (newPassword !== confirmPassword) {
      if (Platform.OS === 'web') window.alert('As senhas nao coincidem');
      else Alert.alert('Erro', 'As senhas nao coincidem');
      return;
    }
    setLoading(true);
    try {
      await adminAPI.changePassword(currentPassword, newPassword);
      if (Platform.OS === 'web') window.alert('Senha alterada com sucesso!');
      else Alert.alert('Sucesso', 'Senha alterada com sucesso!');
      router.back();
    } catch (error: any) {
      const msg = error.response?.data?.detail || 'Erro ao alterar senha';
      if (Platform.OS === 'web') window.alert(msg);
      else Alert.alert('Erro', msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={s.container}>
      <View style={s.header}>
        <TouchableOpacity onPress={() => router.back()} style={s.backBtn}>
          <Ionicons name="arrow-back" size={24} color="#000000" />
        </TouchableOpacity>
        <Text style={s.title}>Alterar Senha</Text>
        <View style={{ width: 40 }} />
      </View>

      <View style={s.form}>
        <Text style={s.label}>Senha Atual *</Text>
        <View style={s.passRow}>
          <TextInput
            style={s.passInput}
            placeholder="Digite sua senha atual"
            value={currentPassword}
            onChangeText={setCurrentPassword}
            secureTextEntry={!showCurrent}
            autoCapitalize="none"
            data-testid="sup-current-password-input"
          />
          <TouchableOpacity onPress={() => setShowCurrent(!showCurrent)} style={s.eyeBtn}>
            <Ionicons name={showCurrent ? 'eye-off' : 'eye'} size={20} color="#666" />
          </TouchableOpacity>
        </View>

        <Text style={s.label}>Nova Senha *</Text>
        <View style={s.passRow}>
          <TextInput
            style={s.passInput}
            placeholder="Minimo 6 caracteres"
            value={newPassword}
            onChangeText={setNewPassword}
            secureTextEntry={!showNew}
            autoCapitalize="none"
            data-testid="sup-new-password-input"
          />
          <TouchableOpacity onPress={() => setShowNew(!showNew)} style={s.eyeBtn}>
            <Ionicons name={showNew ? 'eye-off' : 'eye'} size={20} color="#666" />
          </TouchableOpacity>
        </View>

        <Text style={s.label}>Confirmar Nova Senha *</Text>
        <TextInput
          style={s.input}
          placeholder="Repita a nova senha"
          value={confirmPassword}
          onChangeText={setConfirmPassword}
          secureTextEntry={!showNew}
          autoCapitalize="none"
          data-testid="sup-confirm-password-input"
        />

        <TouchableOpacity
          style={[s.saveBtn, loading && { opacity: 0.6 }]}
          onPress={handleChangePassword}
          disabled={loading}
          data-testid="sup-change-password-btn"
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={s.saveBtnText}>Alterar Senha</Text>
          )}
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 12, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#e0e0e0' },
  backBtn: { padding: 8 },
  title: { fontSize: 20, fontWeight: '600', color: '#000000' },
  form: { padding: 24 },
  label: { fontSize: 14, fontWeight: '600', color: '#212121', marginBottom: 8, marginTop: 16 },
  input: { backgroundColor: '#fff', borderRadius: 8, padding: 16, fontSize: 16, borderWidth: 1, borderColor: '#e0e0e0' },
  passRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', borderRadius: 8, borderWidth: 1, borderColor: '#e0e0e0' },
  passInput: { flex: 1, padding: 16, fontSize: 16 },
  eyeBtn: { padding: 16 },
  saveBtn: { backgroundColor: '#000000', height: 52, borderRadius: 12, justifyContent: 'center', alignItems: 'center', marginTop: 32 },
  saveBtnText: { color: '#fff', fontSize: 18, fontWeight: '600' },
});
