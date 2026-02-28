import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  FlatList,
  ActivityIndicator,
  Alert,
  Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { timesheetAPI } from '../../services/api';
import { Timesheet } from '../../types';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as FileSystem from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';

function getDateRangeText(entries: Timesheet['entries']): string {
  if (!entries || entries.length === 0) return '';
  const dates = entries
    .map(e => e.date)
    .filter(Boolean)
    .map(d => {
      const [day, month, year] = d.split('/');
      return { raw: d, sortKey: `${year}-${month}-${day}` };
    })
    .sort((a, b) => a.sortKey.localeCompare(b.sortKey));
  if (dates.length === 0) return '';
  const uniqueDates = [...new Set(dates.map(d => d.raw))];
  const first = uniqueDates[0];
  const last = uniqueDates[uniqueDates.length - 1];
  if (first === last) return `Timesheet do dia ${first}`;
  return `Timesheet do dia ${first} até ${last}`;
}

export default function AdminTimesheetsScreen() {
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
      if (Platform.OS === 'web') window.alert('Erro ao carregar timesheets');
      else Alert.alert('Erro', 'Erro ao carregar timesheets');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenPDF = async (timesheet: Timesheet) => {
    try {
      if (Platform.OS === 'web') {
        const blob = await timesheetAPI.downloadPDF(timesheet.id);
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank');
      } else {
        const token = await AsyncStorage.getItem('token');
        const baseURL = process.env.EXPO_PUBLIC_BACKEND_URL + '/api';
        const fileUri = `${FileSystem.cacheDirectory}timesheet_${timesheet.id}_${Date.now()}.pdf`;
        const result = await FileSystem.downloadAsync(
          `${baseURL}/timesheets/${timesheet.id}/pdf?t=${Date.now()}`,
          fileUri,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        if (result.status === 200) {
          const isAvailable = await Sharing.isAvailableAsync();
          if (isAvailable) {
            await Sharing.shareAsync(result.uri, { mimeType: 'application/pdf', UTI: 'com.adobe.pdf' });
          } else {
            Alert.alert('Sucesso', 'PDF salvo em: ' + result.uri);
          }
        } else {
          Alert.alert('Erro', 'Erro ao gerar PDF. Status: ' + result.status);
        }
      }
    } catch (error: any) {
      if (Platform.OS === 'web') window.alert('Erro ao abrir PDF');
      else Alert.alert('Erro', 'Erro ao abrir PDF: ' + (error.message || ''));
    }
  };

  const handleDownloadPDF = async (timesheet: Timesheet) => {
    try {
      if (Platform.OS === 'web') {
        const blob = await timesheetAPI.downloadPDF(timesheet.id);
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `timesheet_${timesheet.os_number}_${timesheet.client.replace(/[^a-zA-Z0-9]/g, '_')}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        window.alert('PDF baixado com sucesso!');
      } else {
        const token = await AsyncStorage.getItem('token');
        const baseURL = process.env.EXPO_PUBLIC_BACKEND_URL + '/api';
        const fileName = `timesheet_${timesheet.os_number || 'ts'}_${Date.now()}.pdf`;
        const fileUri = `${FileSystem.documentDirectory}${fileName}`;
        const result = await FileSystem.downloadAsync(
          `${baseURL}/timesheets/${timesheet.id}/pdf?t=${Date.now()}`,
          fileUri,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        if (result.status === 200) {
          const isAvailable = await Sharing.isAvailableAsync();
          if (isAvailable) {
            await Sharing.shareAsync(result.uri, { mimeType: 'application/pdf', UTI: 'com.adobe.pdf', dialogTitle: 'Salvar PDF' });
          } else {
            Alert.alert('Sucesso', 'PDF salvo com sucesso!');
          }
        } else {
          Alert.alert('Erro', 'Erro ao baixar PDF. Status: ' + result.status);
        }
      }
    } catch (error: any) {
      if (Platform.OS === 'web') window.alert('Erro ao baixar PDF');
      else Alert.alert('Erro', 'Erro ao baixar PDF: ' + (error.message || ''));
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
      if (Platform.OS === 'web') window.alert('Timesheet excluído!');
      else Alert.alert('Sucesso', 'Timesheet excluído com sucesso!');
    } catch (error: any) {
      if (Platform.OS === 'web') window.alert('Erro ao excluir');
      else Alert.alert('Erro', 'Erro ao excluir timesheet');
    }
  };

  const renderTimesheet = ({ item }: { item: Timesheet }) => (
    <View style={styles.card} data-testid={`timesheet-card-${item.id}`}>
      <View style={styles.topRow}>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{item.os_number}</Text>
        </View>
        <View style={styles.actions}>
          <TouchableOpacity onPress={() => handleOpenPDF(item)} style={styles.actionButton} data-testid={`open-pdf-btn-${item.id}`}>
            <Ionicons name="document-text-outline" size={22} color="#1a237e" />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => handleDownloadPDF(item)} style={styles.actionButton} data-testid={`download-pdf-btn-${item.id}`}>
            <Ionicons name="download-outline" size={22} color="#1a237e" />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => handleDelete(item)} style={styles.actionButton} data-testid={`delete-btn-${item.id}`}>
            <Ionicons name="trash-outline" size={22} color="#d32f2f" />
          </TouchableOpacity>
        </View>
      </View>
      <View style={styles.cardInfo}>
        <Text style={styles.cardTitle}>{item.client}</Text>
        <Text style={styles.cardSubtitle}>{item.location}</Text>
        <Text style={styles.cardService} numberOfLines={1} data-testid={`timesheet-service-${item.id}`}>{item.service}</Text>
        <Text style={styles.cardMeta}>Supervisor: {item.supervisor_name}</Text>
        <Text style={styles.cardMeta}>{item.entries.length} entrada(s)</Text>
        {item.entries.length > 0 && (
          <Text style={styles.dateRange} data-testid={`timesheet-date-range-${item.id}`}>{getDateRangeText(item.entries)}</Text>
        )}
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
        <Text style={styles.title}>Todos os Timesheets</Text>
        <View style={{ width: 40 }} />
      </View>

      <FlatList
        data={timesheets}
        renderItem={renderTimesheet}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.listContent}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Ionicons name="time-outline" size={64} color="#ccc" />
            <Text style={styles.emptyText}>Nenhum timesheet criado</Text>
          </View>
        }
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 12, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#e0e0e0' },
  backButton: { padding: 8 },
  title: { fontSize: 20, fontWeight: '600', color: '#1a237e' },
  listContent: { padding: 16 },
  card: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.1, shadowRadius: 2, elevation: 2 },
  topRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 },
  badge: { backgroundColor: '#e3f2fd', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8 },
  badgeText: { color: '#1a237e', fontWeight: '600', fontSize: 12 },
  cardInfo: { paddingLeft: 2 },
  cardTitle: { fontSize: 16, fontWeight: '600', color: '#212121' },
  cardSubtitle: { fontSize: 14, color: '#666', marginTop: 4 },
  cardService: { fontSize: 13, color: '#444', marginTop: 2, fontStyle: 'italic' },
  cardMeta: { fontSize: 12, color: '#999', marginTop: 4 },
  dateRange: { fontSize: 12, color: '#1a237e', marginTop: 4, fontWeight: '500' },
  actions: { flexDirection: 'row', gap: 4 },
  actionButton: { padding: 8 },
  emptyContainer: { alignItems: 'center', justifyContent: 'center', paddingVertical: 64 },
  emptyText: { fontSize: 16, color: '#999', marginTop: 16 },
});
