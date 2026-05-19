import React, { useState, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  TextInput,
  Modal,
  Alert,
  ActivityIndicator,
  Platform,
  KeyboardAvoidingView,
  FlatList,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { serviceOrderAPI, employeeAPI, timesheetAPI } from '../../services/api';
import { offlineQueue } from '../../services/offlineQueue';
import { useOffline } from '../../contexts/OfflineContext';
import { ServiceOrder, Employee, TimesheetEntry } from '../../types';

// Generate 30-minute time slots
const TIME_SLOTS: string[] = [];
for (let h = 0; h < 24; h++) {
  for (let m = 0; m < 60; m += 30) {
    TIME_SLOTS.push(`${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`);
  }
}

const WEEKDAYS = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
const MONTHS = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];

// Inline calendar - renders directly in form without overlay/modal
function InlineCalendar({ onSelect }: { onSelect: (date: string) => void }) {
  const [currentMonth, setCurrentMonth] = useState(new Date().getMonth());
  const [currentYear, setCurrentYear] = useState(new Date().getFullYear());
  const days = new Date(currentYear, currentMonth + 1, 0).getDate();
  const firstDay = new Date(currentYear, currentMonth, 1).getDay();
  const allCells = [...Array(firstDay).fill(null), ...Array.from({ length: days }, (_, i) => i + 1)];

  return (
    <View style={{ backgroundColor: '#f8f9fa', borderRadius: 12, padding: 12, marginTop: 8, borderWidth: 1, borderColor: '#e0e0e0' }}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <TouchableOpacity onPress={() => { if (currentMonth === 0) { setCurrentMonth(11); setCurrentYear(y => y - 1); } else setCurrentMonth(m => m - 1); }}>
          <Ionicons name="chevron-back" size={22} color="#000000" />
        </TouchableOpacity>
        <Text style={{ fontSize: 16, fontWeight: '600', color: '#000000' }}>{MONTHS[currentMonth]} {currentYear}</Text>
        <TouchableOpacity onPress={() => { if (currentMonth === 11) { setCurrentMonth(0); setCurrentYear(y => y + 1); } else setCurrentMonth(m => m + 1); }}>
          <Ionicons name="chevron-forward" size={22} color="#000000" />
        </TouchableOpacity>
      </View>
      <View style={{ flexDirection: 'row', justifyContent: 'space-around', marginBottom: 4 }}>
        {WEEKDAYS.map(d => <Text key={d} style={{ width: 36, textAlign: 'center', fontSize: 11, fontWeight: '600', color: '#666' }}>{d}</Text>)}
      </View>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
        {allCells.map((cell, idx) => (
          <TouchableOpacity
            key={idx}
            style={{ width: '14.28%' as any, height: 36, justifyContent: 'center', alignItems: 'center' }}
            onPress={() => cell && onSelect(`${String(cell).padStart(2, '0')}/${String(currentMonth + 1).padStart(2, '0')}/${currentYear}`)}
            disabled={!cell}
          >
            <Text style={{ fontSize: 15, color: cell ? '#212121' : 'transparent' }}>{cell || ''}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}

// Inline time picker - renders directly in form without overlay/modal
function InlineTimePicker({ onSelect, allowNone = false }: { onSelect: (time: string) => void; allowNone?: boolean }) {
  return (
    <View style={{ maxHeight: 240, backgroundColor: '#f8f9fa', borderRadius: 12, marginTop: 8, borderWidth: 1, borderColor: '#e0e0e0', overflow: 'hidden' }}>
      {allowNone && (
        <TouchableOpacity
          testID="time-picker-none"
          style={{ padding: 12, borderBottomWidth: 2, borderBottomColor: '#d32f2f', alignItems: 'center', backgroundColor: '#fff5f5' }}
          onPress={() => onSelect('')}
        >
          <Text style={{ fontSize: 15, color: '#d32f2f', fontWeight: '700' }}>Nenhum horário (apenas viagem)</Text>
        </TouchableOpacity>
      )}
      <FlatList
        data={TIME_SLOTS}
        keyExtractor={item => item}
        nestedScrollEnabled
        style={{ maxHeight: 200 }}
        renderItem={({ item }) => (
          <TouchableOpacity style={{ padding: 10, borderBottomWidth: 1, borderBottomColor: '#f0f0f0', alignItems: 'center' }} onPress={() => onSelect(item)}>
            <Text style={{ fontSize: 16, color: '#212121' }}>{item}</Text>
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

export default function CreateTimesheetScreen() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [serviceOrders, setServiceOrders] = useState<ServiceOrder[]>([]);
  const [allEmployees, setAllEmployees] = useState<Employee[]>([]);
  const [filteredEmployees, setFilteredEmployees] = useState<Employee[]>([]);

  const [selectedSO, setSelectedSO] = useState<ServiceOrder | null>(null);
  const [entries, setEntries] = useState<TimesheetEntry[]>([]);
  const [observations, setObservations] = useState('');
  const [supervisorFunction, setSupervisorFunction] = useState('Supervisor');
  const [functionPickerVisible, setFunctionPickerVisible] = useState(false);

  const SUPERVISOR_FUNCTIONS = ['Engenheiro (E)', 'Encarregado (EN)', 'Supervisor (Sup)', 'Técnico (T)', 'Mecânico (M)', 'Téc. Seg. (TS)'];

  const [soModalVisible, setSOModalVisible] = useState(false);
  const [employeeModalVisible, setEmployeeModalVisible] = useState(false);
  const [employeePickerVisible, setEmployeePickerVisible] = useState(false);
  const [editingEntryIndex, setEditingEntryIndex] = useState<number | null>(null);

  // Entry form
  const [entryDate, setEntryDate] = useState('');
  const [selectedEmployee, setSelectedEmployee] = useState<{id: string, name: string, function: string} | null>(null);
  const [serviceStart, setServiceStart] = useState('');
  const [serviceEnd, setServiceEnd] = useState('');
  const [travelStart, setTravelStart] = useState('');
  const [travelEnd, setTravelEnd] = useState('');
  const [hasTravel, setHasTravel] = useState(false);

  // Picker visibility
  const [calendarVisible, setCalendarVisible] = useState(false);
  const [timePickerField, setTimePickerField] = useState<string | null>(null);

  useEffect(() => { loadData(); }, []);

  useEffect(() => {
    if (selectedSO && selectedSO.employees && selectedSO.employees.length > 0) {
      const filtered = selectedSO.employees.map(soEmp => {
        const emp = allEmployees.find(e => e.id === soEmp.employee_id);
        return emp ? { ...emp, function: soEmp.function } : null;
      }).filter(Boolean) as Employee[];
      setFilteredEmployees(filtered);
    } else {
      setFilteredEmployees(allEmployees);
    }
  }, [selectedSO, allEmployees]);

  const loadData = async () => {
    try {
      // Try online; if offline, fall back to caches stored after the last
      // successful sync (supervisor index caches both OSs and employees).
      let soData: any[] = [];
      let empData: any[] = [];
      try { soData = await serviceOrderAPI.getAll(); } catch { soData = []; }
      try { empData = await employeeAPI.getAll(); } catch { empData = []; }
      if (!soData || soData.length === 0) {
        const cached = await AsyncStorage.getItem('cached_service_orders');
        if (cached) { try { soData = JSON.parse(cached); } catch {} }
      } else {
        try { await AsyncStorage.setItem('cached_service_orders', JSON.stringify(soData)); } catch {}
      }
      if (!empData || empData.length === 0) {
        const cached = await AsyncStorage.getItem('cached_employees');
        if (cached) { try { empData = JSON.parse(cached); } catch {} }
      } else {
        try { await AsyncStorage.setItem('cached_employees', JSON.stringify(empData)); } catch {}
      }
      setServiceOrders(soData || []);
      setAllEmployees(empData || []);
      setFilteredEmployees(empData || []);
    } catch (error: any) {
      // Already handled above
    } finally {
      setLoading(false);
    }
  };

  const MAX_ENTRIES = 12;

  const openAddEntryModal = () => {
    if (entries.length >= MAX_ENTRIES) {
      if (Platform.OS === 'web') {
        window.alert('Limite de 12 funcionários por timesheet atingido. Crie um novo timesheet para adicionar mais funcionários.');
      } else {
        Alert.alert('Limite atingido', 'Limite de 12 funcionários por timesheet atingido. Crie um novo timesheet para adicionar mais funcionários.');
      }
      return;
    }
    setEditingEntryIndex(null);
    resetEntryForm();
    setEmployeeModalVisible(true);
  };

  const resetEntryForm = () => {
    setEntryDate('');
    setSelectedEmployee(null);
    setServiceStart('');
    setServiceEnd('');
    setTravelStart('');
    setTravelEnd('');
    setHasTravel(false);
    setCalendarVisible(false);
    setEmployeePickerVisible(false);
    setTimePickerField(null);
  };

  const handleAddEntry = () => {
    if (!entryDate || !selectedEmployee) {
      Alert.alert('Erro', 'Preencha data e funcionário');
      return;
    }
    const hasService = !!(serviceStart && serviceEnd);
    const hasTravelHours = !!(hasTravel && travelStart && travelEnd);
    if (!hasService && !hasTravelHours) {
      Alert.alert('Erro', 'Informe ao menos hora de serviço OU hora de viagem');
      return;
    }
    if (editingEntryIndex === null && entries.length >= MAX_ENTRIES) {
      if (Platform.OS === 'web') {
        window.alert('Limite de 12 funcionários por timesheet atingido. Crie um novo timesheet para adicionar mais funcionários.');
      } else {
        Alert.alert('Limite atingido', 'Limite de 12 funcionários por timesheet. Crie um novo.');
      }
      return;
    }
    // Validate travel vs service conflict (only if both are present)
    if (hasService && hasTravelHours) {
      const toMin = (t: string) => { const [h, m] = t.split(':').map(Number); return h * 60 + m; };
      const ss = toMin(serviceStart), se = toMin(serviceEnd), ts = toMin(travelStart), te = toMin(travelEnd);
      if (ts < se && ss < te) {
        const msg = `O horario de viagem (${travelStart}-${travelEnd}) nao pode coincidir com o horario de servico (${serviceStart}-${serviceEnd}). A viagem deve ser antes ou depois do periodo de servico.`;
        if (Platform.OS === 'web') window.alert(msg); else Alert.alert('Conflito de Horario', msg);
        return;
      }
    }
    const newEntry: TimesheetEntry = {
      date: entryDate,
      employee_id: selectedEmployee.id,
      employee_name: selectedEmployee.name,
      employee_function: selectedEmployee.function || 'T',
      service_start: serviceStart || '',
      service_end: serviceEnd || '',
      travel_start: hasTravelHours ? travelStart : '-',
      travel_end: hasTravelHours ? travelEnd : '-',
    };
    if (editingEntryIndex !== null) {
      const newEntries = [...entries];
      newEntries[editingEntryIndex] = newEntry;
      setEntries(newEntries.sort((a, b) => {
        const [ad, am, ay] = a.date.split('/'); const [bd, bm, by] = b.date.split('/');
        const dateComp = `${ay}-${am}-${ad}`.localeCompare(`${by}-${bm}-${bd}`);
        return dateComp || a.employee_name.localeCompare(b.employee_name);
      }));
    } else {
      setEntries([...entries, newEntry].sort((a, b) => {
        const [ad, am, ay] = a.date.split('/'); const [bd, bm, by] = b.date.split('/');
        const dateComp = `${ay}-${am}-${ad}`.localeCompare(`${by}-${bm}-${bd}`);
        return dateComp || a.employee_name.localeCompare(b.employee_name);
      }));
    }
    setEmployeeModalVisible(false);
    resetEntryForm();
  };

  const handleEditEntry = (index: number) => {
    const entry = entries[index];
    setEditingEntryIndex(index);
    setEntryDate(entry.date);
    const emp = allEmployees.find(e => e.id === entry.employee_id);
    setSelectedEmployee(emp || null);
    setServiceStart(entry.service_start);
    setServiceEnd(entry.service_end);
    setTravelStart(entry.travel_start || '');
    setTravelEnd(entry.travel_end || '');
    setHasTravel(!!(entry.travel_start && entry.travel_start !== '' && entry.travel_start !== '-'));
    setCalendarVisible(false);
    setEmployeePickerVisible(false);
    setTimePickerField(null);
    setEmployeeModalVisible(true);
  };

  const handleDeleteEntry = (index: number) => {
    if (Platform.OS === 'web') {
      if (window.confirm('Deseja remover esta entrada?')) {
        setEntries(entries.filter((_, i) => i !== index));
      }
    } else {
      Alert.alert('Confirmar', 'Deseja remover esta entrada?', [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Remover', style: 'destructive', onPress: () => setEntries(entries.filter((_, i) => i !== index)) },
      ]);
    }
  };

  const { isOnline } = useOffline();

  const handleSave = async () => {
    if (!selectedSO) { if (Platform.OS === 'web') window.alert('Selecione uma Ordem de Serviço'); else Alert.alert('Erro', 'Selecione uma Ordem de Serviço'); return; }
    if (entries.length === 0) { if (Platform.OS === 'web') window.alert('Adicione pelo menos uma entrada'); else Alert.alert('Erro', 'Adicione pelo menos uma entrada'); return; }
    if (entries.length > 12) { if (Platform.OS === 'web') window.alert('Máximo de 12 funcionários por timesheet. Remova entradas extras ou crie um novo timesheet.'); else Alert.alert('Limite atingido', 'Máximo de 12 funcionários por timesheet.'); return; }
    setSaving(true);
    try {
      if (!isOnline) {
        // Offline: store in local queue. It will be auto-synced when online.
        await offlineQueue.enqueue({
          type: 'create_timesheet',
          payload: { os_id: selectedSO.id, entries, observations, supervisor_function: supervisorFunction },
          snapshot: {
            id: `local_${Date.now()}`,
            os_id: selectedSO.id,
            os_number: selectedSO.os_number,
            client: selectedSO.client,
            service: selectedSO.service,
            entries,
            observations,
            status: 'draft',
            is_offline: true,
            created_at: new Date().toISOString(),
          },
        });
        const msg = 'Timesheet salvo offline. Será sincronizado quando você tiver conexão.';
        if (Platform.OS === 'web') {
          window.alert(msg);
          router.replace(`/supervisor?refresh=${Date.now()}`);
        } else {
          Alert.alert('Salvo offline', msg, [{ text: 'OK', onPress: () => router.replace(`/supervisor?refresh=${Date.now()}`) }]);
        }
        return;
      }
      await timesheetAPI.create(selectedSO.id, entries, observations, supervisorFunction);
      if (Platform.OS === 'web') {
        window.alert('Timesheet criado com sucesso!');
        router.replace(`/supervisor?refresh=${Date.now()}`);
      } else {
        Alert.alert('Sucesso', 'Timesheet criado com sucesso', [{ text: 'OK', onPress: () => router.replace(`/supervisor?refresh=${Date.now()}`) }]);
      }
    } catch (error: any) {
      const msg = error?.response?.data?.detail || 'Erro ao salvar timesheet';
      if (Platform.OS === 'web') window.alert(msg); else Alert.alert('Erro', msg);
    } finally {
      setSaving(false);
    }
  };

  // Close all inline pickers except the one being opened
  const openInlinePicker = (picker: 'calendar' | 'employee' | string | null) => {
    setCalendarVisible(picker === 'calendar' ? !calendarVisible : false);
    setEmployeePickerVisible(picker === 'employee' ? !employeePickerVisible : false);
    setTimePickerField(picker && picker !== 'calendar' && picker !== 'employee' ? (timePickerField === picker ? null : picker) : null);
  };

  if (loading) return <View style={styles.loadingContainer}><ActivityIndicator size="large" color="#000000" /></View>;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#000000" />
        </TouchableOpacity>
        <Text style={styles.title}>Novo Timesheet</Text>
        <View style={{ width: 40 }} />
      </View>

      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={styles.scrollContent}>
          {/* Service Order Selection */}
          <View style={styles.section}>
            <Text style={styles.label}>Ordem de Serviço *</Text>
            <TouchableOpacity style={styles.selectButton} onPress={() => setSOModalVisible(true)}>
              <Text style={selectedSO ? styles.selectTextSelected : styles.selectText}>
                {selectedSO ? `${selectedSO.os_number} - ${selectedSO.client}` : 'Selecionar O.S.'}
              </Text>
              <Ionicons name="chevron-down" size={20} color="#666" />
            </TouchableOpacity>
            {selectedSO && filteredEmployees.length > 0 && (
              <Text style={styles.employeeHint}>
                {filteredEmployees.length} funcionário(s) vinculados a esta O.S.
              </Text>
            )}
          </View>

          {/* Entries */}
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text style={styles.label}>Entradas ({entries.length}/12)</Text>
              {entries.length < 12 ? (
                <TouchableOpacity onPress={openAddEntryModal} style={styles.addEntryButton}>
                  <Ionicons name="add" size={20} color="#000000" />
                  <Text style={styles.addEntryText}>Adicionar</Text>
                </TouchableOpacity>
              ) : (
                <View style={styles.addEntryButton}>
                  <Ionicons name="lock-closed" size={16} color="#999" />
                  <Text style={{ fontSize: 14, color: '#999' }}>Limite atingido</Text>
                </View>
              )}
            </View>
            {entries.length >= 12 && (
              <View style={{ backgroundColor: '#fff3e0', padding: 10, borderRadius: 8, marginBottom: 8, borderWidth: 1, borderColor: '#ffb74d' }}>
                <Text style={{ color: '#e65100', fontSize: 13, textAlign: 'center' }}>Máximo de 12 funcionários atingido. Para adicionar mais, crie um novo timesheet.</Text>
              </View>
            )}
            {entries.map((entry, index) => (
              <View key={index} style={styles.entryCard}>
                <View style={styles.entryCardContent}>
                  <View style={styles.entryBadge}><Text style={styles.entryBadgeText}>{entry.employee_function}</Text></View>
                  <View style={styles.entryInfo}>
                    <Text style={styles.entryName}>{entry.employee_name}</Text>
                    <Text style={styles.entryDetail}>Data: {entry.date}</Text>
                    <Text style={styles.entryDetail}>Serviço: {entry.service_start || '-'} - {entry.service_end || '-'}</Text>
                    {entry.travel_start && entry.travel_start !== '0' && entry.travel_start !== '' ? <Text style={styles.entryDetail}>Viagem: {entry.travel_start} - {entry.travel_end}</Text> : null}
                  </View>
                </View>
                <View style={styles.entryActions}>
                  <TouchableOpacity onPress={() => handleEditEntry(index)}><Ionicons name="pencil" size={20} color="#000000" /></TouchableOpacity>
                  <TouchableOpacity onPress={() => handleDeleteEntry(index)}><Ionicons name="trash" size={20} color="#d32f2f" /></TouchableOpacity>
                </View>
              </View>
            ))}
            {entries.length === 0 && (
              <View style={styles.emptyEntries}>
                <Ionicons name="people-outline" size={48} color="#ccc" />
                <Text style={styles.emptyText}>Nenhuma entrada adicionada</Text>
              </View>
            )}
          </View>

          {/* Supervisor Function */}
          <View style={styles.section}>
            <Text style={styles.label}>Função do Supervisor</Text>
            <TouchableOpacity style={styles.selectButton} onPress={() => setFunctionPickerVisible(true)}>
              <Text style={supervisorFunction !== 'Supervisor' ? styles.selectTextSelected : styles.selectText}>{supervisorFunction}</Text>
              <Ionicons name="chevron-down" size={20} color="#666" />
            </TouchableOpacity>
          </View>

          {/* Observations */}
          <View style={styles.section}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
              <Text style={styles.label}>Observações</Text>
              <Text style={{ fontSize: 12, color: (() => { const chars = 100; const vl = observations.split(/\r\n|\r|\n/).reduce((t, l) => t + Math.max(1, Math.ceil(l.length / chars)), 0); return vl > 9 || observations.length >= 1200 ? '#d32f2f' : '#999'; })() }}>{observations.length}/1200 ({(() => { const chars = 100; return observations.split(/\r\n|\r|\n/).reduce((t, l) => t + Math.max(1, Math.ceil(l.length / chars)), 0); })()}/9 linhas)</Text>
            </View>
            <TextInput style={[styles.input, styles.textArea]} placeholder="Adicione observações (opcional)" value={observations} onChangeText={(text) => { const charsPerLine = 100; const lines = text.split(/\r\n|\r|\n/); const visualLines = lines.reduce((t, l) => t + Math.max(1, Math.ceil(l.length / charsPerLine)), 0); if (visualLines > 9 || text.length > 1200) { if (Platform.OS === 'web') window.alert('Limite atingido: máximo de 1200 caracteres ou 9 linhas visuais.'); else Alert.alert('Limite atingido', 'Máximo de 1200 caracteres ou 9 linhas visuais.'); const trimmedLines: string[] = []; let count = 0; for (const line of lines) { const needed = Math.max(1, Math.ceil(line.length / charsPerLine)); if (count + needed <= 9) { trimmedLines.push(line); count += needed; } else { const remaining = 9 - count; if (remaining > 0) { trimmedLines.push(line.substring(0, remaining * charsPerLine)); } break; } } text = trimmedLines.join('\n'); if (text.length > 1200) text = text.substring(0, 1200); } setObservations(text); }} multiline numberOfLines={9} blurOnSubmit={false} />
          </View>

          <TouchableOpacity style={[styles.saveButton, saving && styles.saveButtonDisabled]} onPress={handleSave} disabled={saving}>
            {saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.saveButtonText}>Salvar Timesheet</Text>}
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>

      {/* Service Order Modal */}
      <Modal visible={soModalVisible} animationType="slide" transparent onRequestClose={() => setSOModalVisible(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Selecionar Ordem de Serviço</Text>
            <ScrollView style={styles.modalList}>
              {serviceOrders.map(so => (
                <TouchableOpacity key={so.id} style={styles.modalItem} onPress={() => { setSelectedSO(so); setSOModalVisible(false); }}>
                  <Text style={styles.modalItemTitle}>{so.os_number}</Text>
                  <Text style={styles.modalItemSubtitle}>{so.client}</Text>
                  <Text style={styles.modalItemDetail}>{so.location}</Text>
                  <Text style={styles.modalItemService} numberOfLines={1}>{so.service || ''}</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
            <TouchableOpacity style={styles.modalCloseButton} onPress={() => setSOModalVisible(false)}>
              <Text style={styles.modalCloseButtonText}>Fechar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* Entry Form Modal - ALL pickers render INLINE inside this modal */}
      <Modal visible={employeeModalVisible} animationType="slide" transparent onRequestClose={() => { setEmployeeModalVisible(false); resetEntryForm(); }}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <ScrollView nestedScrollEnabled keyboardShouldPersistTaps="handled">
              <Text style={styles.modalTitle}>{editingEntryIndex !== null ? 'Editar Entrada' : 'Adicionar Entrada'}</Text>

              {/* Date */}
              <Text style={styles.inputLabel}>Data *</Text>
              <TouchableOpacity style={styles.selectButton} onPress={() => openInlinePicker('calendar')} data-testid="entry-date-btn">
                <Text style={entryDate ? styles.selectTextSelected : styles.selectText}>
                  {entryDate || 'Selecionar data'}
                </Text>
                <Ionicons name={calendarVisible ? 'chevron-up' : 'calendar'} size={20} color="#000000" />
              </TouchableOpacity>
              {calendarVisible && <InlineCalendar onSelect={(date: string) => { setEntryDate(date); setCalendarVisible(false); }} />}

              {/* Employee */}
              <Text style={styles.inputLabel}>Funcionário *</Text>
              <TouchableOpacity style={styles.selectButton} onPress={() => openInlinePicker('employee')} data-testid="entry-employee-btn">
                <Text style={selectedEmployee ? styles.selectTextSelected : styles.selectText}>
                  {selectedEmployee ? `${selectedEmployee.name} (${selectedEmployee.function})` : 'Selecionar'}
                </Text>
                <Ionicons name={employeePickerVisible ? 'chevron-up' : 'chevron-down'} size={20} color="#666" />
              </TouchableOpacity>
              {employeePickerVisible && (
                <View style={{ maxHeight: 200, borderWidth: 1, borderColor: '#e0e0e0', borderRadius: 8, marginTop: 4, overflow: 'hidden', backgroundColor: '#fff' }}>
                  <FlatList
                    data={filteredEmployees}
                    keyExtractor={(emp) => emp.id}
                    nestedScrollEnabled
                    style={{ maxHeight: 200 }}
                    ListEmptyComponent={<Text style={{ padding: 16, textAlign: 'center', color: '#999' }}>Nenhum funcionário vinculado a esta O.S.</Text>}
                    renderItem={({ item: emp }) => (
                      <TouchableOpacity style={{ padding: 12, borderBottomWidth: 1, borderBottomColor: '#f0f0f0', flexDirection: 'row', alignItems: 'center' }} onPress={() => {
                        const soEmp = selectedSO?.employees?.find(e => e.employee_id === emp.id);
                        setSelectedEmployee({ id: emp.id, name: emp.name, function: soEmp?.function || 'T' });
                        setEmployeePickerVisible(false);
                      }}>
                        <View style={styles.entryBadge}><Text style={styles.entryBadgeText}>
                          {selectedSO?.employees?.find(e => e.employee_id === emp.id)?.function || '-'}
                        </Text></View>
                        <Text style={{ fontSize: 15, color: '#212121', marginLeft: 8 }}>{emp.name}</Text>
                      </TouchableOpacity>
                    )}
                  />
                </View>
              )}

              {/* Service Start */}
              <Text style={styles.inputLabel}>Serviço - Início</Text>
              <TouchableOpacity style={styles.selectButton} onPress={() => openInlinePicker('serviceStart')} data-testid="entry-service-start-btn">
                <Text style={serviceStart ? styles.selectTextSelected : styles.selectText}>
                  {serviceStart || 'Selecionar horário (ou deixe em branco se só viagem)'}
                </Text>
                <Ionicons name="time" size={20} color="#000000" />
              </TouchableOpacity>
              {serviceStart ? (
                <TouchableOpacity onPress={() => { setServiceStart(''); setServiceEnd(''); }} style={{ alignSelf: 'flex-start', paddingVertical: 4 }}>
                  <Text style={{ color: '#d32f2f', fontSize: 12 }}>Limpar horários de serviço</Text>
                </TouchableOpacity>
              ) : null}
              {timePickerField === 'serviceStart' && <InlineTimePicker allowNone onSelect={(t: string) => { setServiceStart(t); if (!t) setServiceEnd(''); setTimePickerField(null); }} />}

              {/* Service End */}
              <Text style={styles.inputLabel}>Serviço - Fim</Text>
              <TouchableOpacity style={styles.selectButton} onPress={() => openInlinePicker('serviceEnd')} data-testid="entry-service-end-btn">
                <Text style={serviceEnd ? styles.selectTextSelected : styles.selectText}>
                  {serviceEnd || 'Selecionar horário (ou deixe em branco se só viagem)'}
                </Text>
                <Ionicons name="time" size={20} color="#000000" />
              </TouchableOpacity>
              {timePickerField === 'serviceEnd' && <InlineTimePicker allowNone onSelect={(t: string) => { setServiceEnd(t); if (!t) setServiceStart(''); setTimePickerField(null); }} />}

              {/* Travel */}
              <TouchableOpacity style={styles.travelCheckRow} onPress={() => { setHasTravel(!hasTravel); if (hasTravel) { setTravelStart(''); setTravelEnd(''); } }} data-testid="has-travel-checkbox">
                <Ionicons name={hasTravel ? 'checkbox' : 'square-outline'} size={24} color="#000000" />
                <Text style={styles.travelCheckText}>Tem viagem?</Text>
              </TouchableOpacity>

              {hasTravel && (
                <>
                  <Text style={styles.inputLabel}>Viagem - Início</Text>
                  <TouchableOpacity style={styles.selectButton} onPress={() => openInlinePicker('travelStart')}>
                    <Text style={travelStart ? styles.selectTextSelected : styles.selectText}>
                      {travelStart || 'Selecionar horário'}
                    </Text>
                    <Ionicons name="time" size={20} color="#666" />
                  </TouchableOpacity>
                  {timePickerField === 'travelStart' && <InlineTimePicker onSelect={(t: string) => { setTravelStart(t); setTimePickerField(null); }} />}

                  <Text style={styles.inputLabel}>Viagem - Fim</Text>
                  <TouchableOpacity style={styles.selectButton} onPress={() => openInlinePicker('travelEnd')}>
                    <Text style={travelEnd ? styles.selectTextSelected : styles.selectText}>
                      {travelEnd || 'Selecionar horário'}
                    </Text>
                    <Ionicons name="time" size={20} color="#666" />
                  </TouchableOpacity>
                  {timePickerField === 'travelEnd' && <InlineTimePicker onSelect={(t: string) => { setTravelEnd(t); setTimePickerField(null); }} />}
                </>
              )}

              <View style={styles.modalButtons}>
                <TouchableOpacity style={[styles.modalButton, styles.cancelButton]} onPress={() => setEmployeeModalVisible(false)}>
                  <Text style={styles.cancelButtonText}>Cancelar</Text>
                </TouchableOpacity>
                <TouchableOpacity style={[styles.modalButton, styles.confirmButton]} onPress={handleAddEntry}>
                  <Text style={styles.confirmButtonText}>{editingEntryIndex !== null ? 'Atualizar' : 'Adicionar'}</Text>
                </TouchableOpacity>
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* Function Picker Modal */}
      <Modal visible={functionPickerVisible} animationType="slide" transparent onRequestClose={() => setFunctionPickerVisible(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Função do Supervisor</Text>
            <ScrollView style={styles.modalList}>
              {SUPERVISOR_FUNCTIONS.map(fn => (
                <TouchableOpacity key={fn} style={[styles.modalItem, supervisorFunction === fn && { backgroundColor: '#f0f0f0' }]} onPress={() => { setSupervisorFunction(fn); setFunctionPickerVisible(false); }}>
                  <Text style={[styles.modalItemTitle, supervisorFunction === fn && { color: '#000000' }]}>{fn}</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
            <TouchableOpacity style={styles.modalCloseButton} onPress={() => setFunctionPickerVisible(false)}>
              <Text style={styles.modalCloseButtonText}>Fechar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 12, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#e0e0e0' },
  backButton: { padding: 8 },
  title: { fontSize: 20, fontWeight: '600', color: '#000000' },
  scrollContent: { padding: 16 },
  section: { marginBottom: 24 },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  label: { fontSize: 16, fontWeight: '600', color: '#212121', marginBottom: 8 },
  employeeHint: { fontSize: 12, color: '#000000', marginTop: 6, fontStyle: 'italic' },
  selectButton: { backgroundColor: '#fff', borderRadius: 8, padding: 16, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderWidth: 1, borderColor: '#e0e0e0' },
  selectText: { fontSize: 16, color: '#999' },
  selectTextSelected: { fontSize: 16, color: '#212121' },
  addEntryButton: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  addEntryText: { fontSize: 16, color: '#000000', fontWeight: '600' },
  entryCard: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 12, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  entryCardContent: { flexDirection: 'row', flex: 1 },
  entryBadge: { backgroundColor: '#f0f0f0', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 6, marginRight: 12 },
  entryBadgeText: { color: '#000000', fontWeight: '600', fontSize: 12 },
  entryInfo: { flex: 1 },
  entryName: { fontSize: 16, fontWeight: '600', color: '#212121' },
  entryDetail: { fontSize: 14, color: '#666', marginTop: 4 },
  entryActions: { flexDirection: 'row', gap: 12 },
  emptyEntries: { alignItems: 'center', paddingVertical: 48 },
  emptyText: { fontSize: 14, color: '#999', marginTop: 12, textAlign: 'center' },
  input: { backgroundColor: '#fff', borderRadius: 8, padding: 16, fontSize: 16, borderWidth: 1, borderColor: '#e0e0e0' },
  textArea: { minHeight: 100, textAlignVertical: 'top' },
  saveButton: { backgroundColor: '#000000', height: 56, borderRadius: 12, justifyContent: 'center', alignItems: 'center', marginTop: 16 },
  saveButtonDisabled: { opacity: 0.6 },
  saveButtonText: { color: '#fff', fontSize: 18, fontWeight: '600' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', padding: 16 },
  modalContent: { backgroundColor: '#fff', borderRadius: 16, padding: 24, maxHeight: '85%' },
  modalTitle: { fontSize: 20, fontWeight: '600', color: '#000000', marginBottom: 16 },
  modalList: { maxHeight: 400 },
  modalItem: { padding: 16, borderBottomWidth: 1, borderBottomColor: '#e0e0e0' },
  modalItemTitle: { fontSize: 16, fontWeight: '600', color: '#212121' },
  modalItemSubtitle: { fontSize: 14, color: '#666', marginTop: 4 },
  modalItemDetail: { fontSize: 12, color: '#999', marginTop: 2 },
  modalItemService: { fontSize: 12, color: '#444', marginTop: 2, fontStyle: 'italic' },
  travelCheckRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, gap: 8 },
  travelCheckText: { fontSize: 16, color: '#212121' },
  modalCloseButton: { backgroundColor: '#f5f5f5', height: 48, borderRadius: 8, justifyContent: 'center', alignItems: 'center', marginTop: 16 },
  modalCloseButtonText: { fontSize: 16, fontWeight: '600', color: '#666' },
  inputLabel: { fontSize: 14, fontWeight: '600', color: '#212121', marginBottom: 8, marginTop: 12 },
  modalButtons: { flexDirection: 'row', gap: 12, marginTop: 24 },
  modalButton: { flex: 1, height: 48, borderRadius: 8, justifyContent: 'center', alignItems: 'center' },
  cancelButton: { backgroundColor: '#f5f5f5' },
  cancelButtonText: { color: '#666', fontSize: 16, fontWeight: '600' },
  confirmButton: { backgroundColor: '#000000' },
  confirmButtonText: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
