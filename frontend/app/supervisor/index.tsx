import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, FlatList, Alert, ActivityIndicator, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { timesheetAPI } from '../../services/api';
import { Timesheet } from '../../types';

export default function SupervisorDashboard() {
  const { user, signOut } = useAuth();
  const router = useRouter();
  const [timesheets, setTimesheets] = useState<Timesheet[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTimesheets();
  }, []);

  const loadTimesheets = async () => {
    try {
      const data = await timesheetAPI.getAll();
      setTimesheets(data);
    } catch (error: any) {
      Alert.alert('Erro', 'Erro ao carregar timesheets');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await signOut();
    router.replace('/');
  };

  const handleOpenPDF = (timesheet: Timesheet) => {
    const url = `${api.defaults.baseURL}/timesheets/${timesheet.id}/pdf?t=${Date.now()}`;
    if (Platform.OS === 'web') {
      window.open(url, '_blank');
    }
  };

  const handleDownloadPDF = async (timesheet: Timesheet) => {
    try {
      const blob = await timesheetAPI.downloadPDF(timesheet.id);
      
      if (Platform.OS === 'web') {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `timesheet_${timesheet.os_number}_${timesheet.client.replace(/[^a-zA-Z0-9]/g, '_')}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        Alert.alert('Sucesso', 'PDF baixado com sucesso!');
      } else {
        const fileReaderInstance = new FileReader();
        fileReaderInstance.readAsDataURL(blob);
        fileReaderInstance.onload = () => {
          Alert.alert('PDF', 'PDF gerado com sucesso!');
        };
      }
    } catch (error: any) {
      console.error('Erro ao baixar PDF:', error);
      Alert.alert('Erro', 'Erro ao baixar PDF');
    }
  };

  const handleDelete = (timesheet: Timesheet) => {
    if (Platform.OS === 'web') {
      if (window.confirm(`Excluir timesheet ${timesheet.os_number} - ${timesheet.client}?`)) {
        deleteTimesheet(timesheet.id);
      }
    } else {
      Alert.alert(
        'Confirmar Exclusão',
        `Excluir timesheet ${timesheet.os_number} - ${timesheet.client}?`,
        [
          { text: 'Cancelar', style: 'cancel' },
          { text: 'Excluir', style: 'destructive', onPress: () => deleteTimesheet(timesheet.id) },
        ]
      );
    }
  };

  const deleteTimesheet = async (id: string) => {
    try {
      await timesheetAPI.delete(id);
      setTimesheets(prev => prev.filter(t => t.id !== id));
      Alert.alert('Sucesso', 'Timesheet excluído com sucesso!');
    } catch (error: any) {
      console.error('Erro ao excluir:', error);
      Alert.alert('Erro', 'Erro ao excluir timesheet');
    }
  };

  const renderTimesheet = ({ item }: { item: Timesheet }) => (
    <View style={styles.tsCard} data-testid={`timesheet-card-${item.id}`}>
      <TouchableOpacity 
        style={styles.tsCardContent}
        onPress={() => router.push(`/supervisor/edit-timesheet?id=${item.id}`)}
      >
        <View style={styles.tsBadge}>
          <Text style={styles.tsBadgeText}>{item.os_number}</Text>
        </View>
        <View style={styles.tsCardInfo}>
          <Text style={styles.tsCardTitle}>{item.client}</Text>
          <Text style={styles.tsCardSubtitle}>{item.location}</Text>
          <Text style={styles.tsCardMeta}>{item.entries.length} entrada(s)</Text>
        </View>
      </TouchableOpacity>
      <View style={styles.tsActions}>
        <TouchableOpacity 
          onPress={() => router.push(`/supervisor/edit-timesheet?id=${item.id}`)}
          style={styles.tsActionButton}
          data-testid={`edit-btn-${item.id}`}
        >
          <Ionicons name="pencil" size={20} color="#1a237e" />
        </TouchableOpacity>
        <TouchableOpacity 
          onPress={() => handleDownloadPDF(item)}
          style={styles.tsActionButton}
          data-testid={`download-pdf-btn-${item.id}`}
        >
          <Ionicons name="download-outline" size={20} color="#1a237e" />
        </TouchableOpacity>
        <TouchableOpacity 
          onPress={() => handleDelete(item)}
          style={styles.tsActionButton}
          data-testid={`delete-btn-${item.id}`}
        >
          <Ionicons name="trash-outline" size={20} color="#d32f2f" />
        </TouchableOpacity>
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.header}>
          <View>
            <Text style={styles.title}>Timesheet</Text>
            <Text style={styles.subtitle}>Bem-vindo, {user?.name}</Text>
          </View>
          <TouchableOpacity onPress={handleLogout} style={styles.logoutButton}>
            <Ionicons name="log-out-outline" size={24} color="#d32f2f" />
          </TouchableOpacity>
        </View>

        <TouchableOpacity
          style={styles.createButton}
          onPress={() => router.push('/supervisor/create-timesheet')}
        >
          <Ionicons name="add-circle" size={24} color="#fff" />
          <Text style={styles.createButtonText}>Criar Novo Timesheet</Text>
        </TouchableOpacity>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Meus Timesheets</Text>
          {loading ? (
            <ActivityIndicator size="large" color="#1a237e" style={{ marginTop: 24 }} />
          ) : timesheets.length > 0 ? (
            <FlatList
              data={timesheets}
              renderItem={renderTimesheet}
              keyExtractor={(item) => item.id}
              scrollEnabled={false}
            />
          ) : (
            <View style={styles.emptyContainer}>
              <Ionicons name="time-outline" size={48} color="#ccc" />
              <Text style={styles.emptyText}>Nenhum timesheet criado ainda</Text>
            </View>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  scrollContent: {
    padding: 16,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 24,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#1a237e',
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
    marginTop: 4,
  },
  logoutButton: {
    padding: 8,
  },
  createButton: {
    backgroundColor: '#1a237e',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 12,
    marginBottom: 24,
  },
  createButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
    marginLeft: 8,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#212121',
    marginBottom: 16,
  },
  tsCard: {
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
  tsCardContent: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    flex: 1,
  },
  tsActions: {
    flexDirection: 'row',
    gap: 4,
  },
  tsActionButton: {
    padding: 8,
  },
  tsBadge: {
    backgroundColor: '#e3f2fd',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    marginRight: 12,
  },
  tsBadgeText: {
    color: '#1a237e',
    fontWeight: '600',
    fontSize: 12,
  },
  tsCardInfo: {
    flex: 1,
  },
  tsCardTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#212121',
  },
  tsCardSubtitle: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  tsCardMeta: {
    fontSize: 12,
    color: '#999',
    marginTop: 4,
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 48,
  },
  emptyText: {
    fontSize: 14,
    color: '#999',
    marginTop: 12,
  },
});
