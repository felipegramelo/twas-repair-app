import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';

export default function AdminDashboard() {
  const { user, signOut } = useAuth();
  const router = useRouter();

  const handleLogout = async () => {
    await signOut();
    router.replace('/');
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <View>
            <Text style={styles.title}>TWAS REPAIR</Text>
            <Text style={styles.subtitle}>Bem-vindo, {user?.name}</Text>
          </View>
          <TouchableOpacity onPress={handleLogout} style={styles.logoutButton} data-testid="admin-logout-btn">
            <Ionicons name="log-out-outline" size={24} color="#d32f2f" />
          </TouchableOpacity>
        </View>

        <View style={styles.cardsContainer}>
          <TouchableOpacity
            style={styles.card}
            onPress={() => router.push('/admin/supervisors')}
            data-testid="admin-supervisors-card"
          >
            <Ionicons name="person-circle" size={40} color="#1a237e" />
            <Text style={styles.cardTitle}>Supervisores</Text>
            <Text style={styles.cardDescription}>Gerenciar supervisores</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.card}
            onPress={() => router.push('/admin/employees')}
            data-testid="admin-employees-card"
          >
            <Ionicons name="people" size={40} color="#1a237e" />
            <Text style={styles.cardTitle}>Funcionários</Text>
            <Text style={styles.cardDescription}>Gerenciar funcionários</Text>
          </TouchableOpacity>

          {user?.os_archive_access && (
            <TouchableOpacity
              style={[styles.card, { borderWidth: 2, borderColor: '#1a237e' }]}
              onPress={() => router.push('/admin/os-archive')}
              data-testid="admin-os-archive-card"
            >
              <Ionicons name="folder-open" size={40} color="#1a237e" />
              <Text style={styles.cardTitle}>Arquivo por O.S.</Text>
              <Text style={styles.cardDescription}>Todos os documentos por Ordem de Serviço</Text>
            </TouchableOpacity>
          )}

          {user?.bm_access && (
            <TouchableOpacity
              style={[styles.card, { borderWidth: 2, borderColor: '#ff6f00' }]}
              onPress={() => router.push('/admin/boletim-medicao')}
              data-testid="admin-bm-card"
            >
              <Ionicons name="calculator" size={40} color="#ff6f00" />
              <Text style={styles.cardTitle}>Boletim de Medição</Text>
              <Text style={styles.cardDescription}>Gerar e gerenciar BMs</Text>
            </TouchableOpacity>
          )}

          <TouchableOpacity
            style={styles.card}
            onPress={() => router.push('/admin/service-orders')}
            data-testid="admin-service-orders-card"
          >
            <Ionicons name="document-text" size={40} color="#1a237e" />
            <Text style={styles.cardTitle}>Ordens de Serviço</Text>
            <Text style={styles.cardDescription}>Gerenciar O.S.</Text>
          </TouchableOpacity>


          <TouchableOpacity
            style={styles.card}
            onPress={() => router.push('/admin/admins')}
            data-testid="admin-admins-card"
          >
            <Ionicons name="shield-checkmark" size={40} color="#1a237e" />
            <Text style={styles.cardTitle}>Administradores</Text>
            <Text style={styles.cardDescription}>Gerenciar administradores</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.card}
            onPress={() => router.push('/admin/change-password')}
            data-testid="admin-change-password-card"
          >
            <Ionicons name="key" size={40} color="#1a237e" />
            <Text style={styles.cardTitle}>Alterar Senha</Text>
            <Text style={styles.cardDescription}>Alterar sua senha de acesso</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  scrollContent: { padding: 16 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 },
  title: { fontSize: 28, fontWeight: 'bold', color: '#1a237e' },
  subtitle: { fontSize: 16, color: '#666', marginTop: 4 },
  logoutButton: { padding: 8 },
  cardsContainer: { gap: 16 },
  card: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardTitle: { fontSize: 20, fontWeight: '600', color: '#1a237e', marginTop: 12 },
  cardDescription: { fontSize: 14, color: '#666', marginTop: 4 },
});
