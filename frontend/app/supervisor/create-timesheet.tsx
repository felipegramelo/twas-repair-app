import React, { useState, useEffect } from 'react';
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
import { ServiceOrder, Employee, TimesheetEntry } from '../../types';

// Generate 30-minute time slots
const TIME_SLOTS: string[] = [];
for (let h = 0; h < 24; h++) {
  for (let m = 0; m < 60; m += 30) {
    TIME_SLOTS.push(`${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`);
  }
}

// Generate calendar days
const WEEKDAYS = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
const MONTHS = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];

function CalendarPicker({ visible, onClose, onSelect }: { visible: boolean; onClose: () => void; onSelect: (date: string) => void }) {
  const [currentMonth, setCurrentMonth] = useState(new Date().getMonth());
  const [currentYear, setCurrentYear] = useState(new Date().getFullYear());

  const getDaysInMonth = (month: number, year: number) => new Date(year, month + 1, 0).getDate();
  const getFirstDayOfMonth = (month: number, year: number) => new Date(year, month, 1).getDay();

  const days = getDaysInMonth(currentMonth, currentYear);
  const firstDay = getFirstDayOfMonth(currentMonth, currentYear);
  const blanks = Array(firstDay).fill(null);
  const dayNumbers = Array.from({ length: days }, (_, i) => i + 1);
  const allCells = [...blanks, ...dayNumbers];

  const prevMonth = () => {
    if (currentMonth === 0) { setCurrentMonth(11); setCurrentYear(y => y - 1); }
    else setCurrentMonth(m => m - 1);
  };

  const nextMonth = () => {
    if (currentMonth === 11) { setCurrentMonth(0); setCurrentYear(y => y + 1); }
    else setCurrentMonth(m => m + 1);
  };

  const selectDay = (day: number) => {
    const formatted = `${String(day).padStart(2, '0')}/${String(currentMonth + 1).padStart(2, '0')}/${currentYear}`;
    onSelect(formatted);
    onClose();
  };

  return (
    <Modal visible={visible} animationType="fade" transparent onRequestClose={onClose}>
      <View style={calStyles.overlay}>
        <View style={calStyles.container}>
          <View style={calStyles.header}>
            <TouchableOpacity onPress={prevMonth}><Ionicons name="chevron-back" size={24} color="#1a237e" /></TouchableOpacity>
            <Text style={calStyles.monthText}>{MONTHS[currentMonth]} {currentYear}</Text>
            <TouchableOpacity onPress={nextMonth}><Ionicons name="chevron-forward" size={24} color="#1a237e" /></TouchableOpacity>
          </View>
          <View style={calStyles.weekRow}>
            {WEEKDAYS.map(d => <Text key={d} style={calStyles.weekDay}>{d}</Text>)}
          </View>
          <View style={calStyles.daysGrid}>
            {allCells.map((cell, idx) => (
              <TouchableOpacity
                key={idx}
                style={[calStyles.dayCell, cell ? calStyles.dayCellActive : null]}
                onPress={() => cell && selectDay(cell)}
                disabled={!cell}
              >
                <Text style={cell ? calStyles.dayText : calStyles.dayTextEmpty}>{cell || ''}</Text>
              </TouchableOpacity>
            ))}
          </View>
          <TouchableOpacity style={calStyles.closeBtn} onPress={onClose}>
            <Text style={calStyles.closeBtnText}>Fechar</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

function TimePickerModal({ visible, onClose, onSelect, title }: { visible: boolean; onClose: () => void; onSelect: (time: string) => void; title: string }) {
  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View style={tpStyles.overlay}>
        <View style={tpStyles.container}>
          <Text style={tpStyles.title}>{title}</Text>
          <FlatList
            data={TIME_SLOTS}
            keyExtractor={item => item}
            style={tpStyles.list}
            renderItem={({ item }) => (
              <TouchableOpacity style={tpStyles.item} onPress={() => { onSelect(item); onClose(); }}>
                <Text style={tpStyles.itemText}>{item}</Text>
              </TouchableOpacity>
            )}
          />
          <TouchableOpacity style={tpStyles.closeBtn} onPress={onClose}>
            <Text style={tpStyles.closeBtnText}>Cancelar</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
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
      const [soData, empData] = await Promise.all([serviceOrderAPI.getAll(), employeeAPI.getAll()]);
      setServiceOrders(soData);
      setAllEmployees(empData);
      setFilteredEmployees(empData);
    } catch (error: any) {
      Alert.alert('Erro', 'Erro ao carregar dados');
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
  };

  const handleAddEntry = () => {
    if (!entryDate || !selectedEmployee || !serviceStart || !serviceEnd) {
      Alert.alert('Erro', 'Preencha data, funcionário, início e fim do serviço');
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
    const newEntry: TimesheetEntry = {
      date: entryDate,
      employee_id: selectedEmployee.id,
      employee_name: selectedEmployee.name,
      employee_function: selectedEmployee.function || 'T',
      service_start: serviceStart,
      service_end: serviceEnd,
      travel_start: travelStart,
      travel_end: travelEnd,
    };
    if (editingEntryIndex !== null) {
      const newEntries = [...entries];
      newEntries[editingEntryIndex] = newEntry;
      setEntries(newEntries);
    } else {
      setEntries([...entries, newEntry]);
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

  const handleSave = async () => {
    if (!selectedSO) { if (Platform.OS === 'web') window.alert('Selecione uma Ordem de Serviço'); else Alert.alert('Erro', 'Selecione uma Ordem de Serviço'); return; }
    if (entries.length === 0) { if (Platform.OS === 'web') window.alert('Adicione pelo menos uma entrada'); else Alert.alert('Erro', 'Adicione pelo menos uma entrada'); return; }
    if (entries.length > 12) { if (Platform.OS === 'web') window.alert('Máximo de 12 funcionários por timesheet. Remova entradas extras ou crie um novo timesheet.'); else Alert.alert('Limite atingido', 'Máximo de 12 funcionários por timesheet.'); return; }
    setSaving(true);
    try {
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

  const openTimePicker = (field: string) => setTimePickerField(field);

  const handleTimeSelect = (time: string) => {
    switch (timePickerField) {
      case 'serviceStart': setServiceStart(time); break;
      case 'serviceEnd': setServiceEnd(time); break;
      case 'travelStart': setTravelStart(time); break;
      case 'travelEnd': setTravelEnd(time); break;
    }
  };

  const getTimePickerTitle = () => {
    switch (timePickerField) {
      case 'serviceStart': return 'Início do Serviço';
      case 'serviceEnd': return 'Fim do Serviço';
      case 'travelStart': return 'Início da Viagem';
      case 'travelEnd': return 'Fim da Viagem';
      default: return 'Selecionar Horário';
    }
  };

  if (loading) return <View style={styles.loadingContainer}><ActivityIndicator size="large" color="#1a237e" /></View>;

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#1a237e" />
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
                  <Ionicons name="add" size={20} color="#1a237e" />
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
                    <Text style={styles.entryDetail}>Serviço: {entry.service_start} - {entry.service_end}</Text>
                    {entry.travel_start && entry.travel_start !== '0' && entry.travel_start !== '' ? <Text style={styles.entryDetail}>Viagem: {entry.travel_start} - {entry.travel_end}</Text> : null}
                  </View>
                </View>
                <View style={styles.entryActions}>
                  <TouchableOpacity onPress={() => handleEditEntry(index)}><Ionicons name="pencil" size={20} color="#1a237e" /></TouchableOpacity>
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
            <TouchableOpacity style={styles.selectInput} onPress={() => setFunctionPickerVisible(true)}>
              <Text style={styles.selectInputText}>{supervisorFunction}</Text>
              <Ionicons name="chevron-down" size={20} color="#666" />
            </TouchableOpacity>
          </View>

          {/* Observations */}
          <View style={styles.section}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
              <Text style={styles.label}>Observações</Text>
              <Text style={{ fontSize: 12, color: observations.length >= 800 ? '#d32f2f' : '#999' }}>{observations.length}/800</Text>
            </View>
            <TextInput style={[styles.input, styles.textArea]} placeholder="Adicione observações (opcional)" value={observations} onChangeText={(text) => { if (text.length <= 800) setObservations(text); }} multiline numberOfLines={4} maxLength={800} />
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
                </TouchableOpacity>
              ))}
            </ScrollView>
            <TouchableOpacity style={styles.modalCloseButton} onPress={() => setSOModalVisible(false)}>
              <Text style={styles.modalCloseButtonText}>Fechar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* Entry Form Modal */}
      <Modal visible={employeeModalVisible} animationType="slide" transparent onRequestClose={() => setEmployeeModalVisible(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <ScrollView>
              <Text style={styles.modalTitle}>{editingEntryIndex !== null ? 'Editar Entrada' : 'Adicionar Entrada'}</Text>

              <Text style={styles.inputLabel}>Data *</Text>
              <TouchableOpacity style={styles.selectButton} onPress={() => setCalendarVisible(true)}>
                <Text style={entryDate ? styles.selectTextSelected : styles.selectText}>
                  {entryDate || 'Selecionar data'}
                </Text>
                <Ionicons name="calendar" size={20} color="#1a237e" />
              </TouchableOpacity>

              <Text style={styles.inputLabel}>Funcionário *</Text>
              <TouchableOpacity style={styles.selectButton} onPress={() => setEmployeePickerVisible(true)}>
                <Text style={selectedEmployee ? styles.selectTextSelected : styles.selectText}>
                  {selectedEmployee ? `${selectedEmployee.name} (${selectedEmployee.function})` : 'Selecionar'}
                </Text>
                <Ionicons name="chevron-down" size={20} color="#666" />
              </TouchableOpacity>

              <Text style={styles.inputLabel}>Serviço - Início *</Text>
              <TouchableOpacity style={styles.selectButton} onPress={() => openTimePicker('serviceStart')}>
                <Text style={serviceStart ? styles.selectTextSelected : styles.selectText}>
                  {serviceStart || 'Selecionar horário'}
                </Text>
                <Ionicons name="time" size={20} color="#1a237e" />
              </TouchableOpacity>

              <Text style={styles.inputLabel}>Serviço - Fim *</Text>
              <TouchableOpacity style={styles.selectButton} onPress={() => openTimePicker('serviceEnd')}>
                <Text style={serviceEnd ? styles.selectTextSelected : styles.selectText}>
                  {serviceEnd || 'Selecionar horário'}
                </Text>
                <Ionicons name="time" size={20} color="#1a237e" />
              </TouchableOpacity>

              <Text style={styles.inputLabel}>Viagem - Início</Text>
              <TouchableOpacity style={styles.selectButton} onPress={() => openTimePicker('travelStart')}>
                <Text style={travelStart ? styles.selectTextSelected : styles.selectText}>
                  {travelStart || 'Selecionar horário'}
                </Text>
                <Ionicons name="time" size={20} color="#666" />
              </TouchableOpacity>

              <Text style={styles.inputLabel}>Viagem - Fim</Text>
              <TouchableOpacity style={styles.selectButton} onPress={() => openTimePicker('travelEnd')}>
                <Text style={travelEnd ? styles.selectTextSelected : styles.selectText}>
                  {travelEnd || 'Selecionar horário'}
                </Text>
                <Ionicons name="time" size={20} color="#666" />
              </TouchableOpacity>

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

      {/* Employee Picker */}
      <Modal visible={employeePickerVisible} animationType="slide" transparent onRequestClose={() => setEmployeePickerVisible(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Selecionar Funcionário</Text>
            <ScrollView style={styles.modalList}>
              {filteredEmployees.length === 0 ? (
                <View style={styles.emptyEntries}>
                  <Ionicons name="people-outline" size={48} color="#ccc" />
                  <Text style={styles.emptyText}>Nenhum funcionário vinculado a esta O.S.</Text>
                </View>
              ) : (
                filteredEmployees.map(emp => (
                  <TouchableOpacity key={emp.id} style={styles.modalItem} onPress={() => {
                    const soEmp = selectedSO?.employees?.find(e => e.employee_id === emp.id);
                    setSelectedEmployee({ id: emp.id, name: emp.name, function: soEmp?.function || 'T' });
                    setEmployeePickerVisible(false);
                  }}>
                    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                      <View style={styles.entryBadge}><Text style={styles.entryBadgeText}>
                        {selectedSO?.employees?.find(e => e.employee_id === emp.id)?.function || '-'}
                      </Text></View>
                      <Text style={styles.modalItemTitle}>{emp.name}</Text>
                    </View>
                  </TouchableOpacity>
                ))
              )}
            </ScrollView>
            <TouchableOpacity style={styles.modalCloseButton} onPress={() => setEmployeePickerVisible(false)}>
              <Text style={styles.modalCloseButtonText}>Fechar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* Calendar Picker */}
      <CalendarPicker visible={calendarVisible} onClose={() => setCalendarVisible(false)} onSelect={setEntryDate} />

      {/* Time Picker */}
      <TimePickerModal visible={!!timePickerField} onClose={() => setTimePickerField(null)} onSelect={handleTimeSelect} title={getTimePickerTitle()} />
    </SafeAreaView>
  );
}

const calStyles = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', padding: 16 },
  container: { backgroundColor: '#fff', borderRadius: 16, padding: 20 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  monthText: { fontSize: 18, fontWeight: '600', color: '#1a237e' },
  weekRow: { flexDirection: 'row', justifyContent: 'space-around', marginBottom: 8 },
  weekDay: { width: 40, textAlign: 'center', fontSize: 12, fontWeight: '600', color: '#666' },
  daysGrid: { flexDirection: 'row', flexWrap: 'wrap' },
  dayCell: { width: '14.28%', height: 40, justifyContent: 'center', alignItems: 'center' },
  dayCellActive: { cursor: 'pointer' as any },
  dayText: { fontSize: 16, color: '#212121' },
  dayTextEmpty: { fontSize: 16, color: 'transparent' },
  closeBtn: { backgroundColor: '#f5f5f5', height: 44, borderRadius: 8, justifyContent: 'center', alignItems: 'center', marginTop: 12 },
  closeBtnText: { fontSize: 16, fontWeight: '600', color: '#666' },
});

const tpStyles = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', padding: 16 },
  container: { backgroundColor: '#fff', borderRadius: 16, padding: 20, maxHeight: '70%' },
  title: { fontSize: 18, fontWeight: '600', color: '#1a237e', marginBottom: 12, textAlign: 'center' },
  list: { maxHeight: 350 },
  item: { padding: 14, borderBottomWidth: 1, borderBottomColor: '#f0f0f0', alignItems: 'center' },
  itemText: { fontSize: 18, color: '#212121' },
  closeBtn: { backgroundColor: '#f5f5f5', height: 44, borderRadius: 8, justifyContent: 'center', alignItems: 'center', marginTop: 12 },
  closeBtnText: { fontSize: 16, fontWeight: '600', color: '#666' },
});

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 12, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#e0e0e0' },
  backButton: { padding: 8 },
  title: { fontSize: 20, fontWeight: '600', color: '#1a237e' },
  scrollContent: { padding: 16 },
  section: { marginBottom: 24 },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  label: { fontSize: 16, fontWeight: '600', color: '#212121', marginBottom: 8 },
  employeeHint: { fontSize: 12, color: '#1a237e', marginTop: 6, fontStyle: 'italic' },
  selectButton: { backgroundColor: '#fff', borderRadius: 8, padding: 16, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderWidth: 1, borderColor: '#e0e0e0' },
  selectText: { fontSize: 16, color: '#999' },
  selectTextSelected: { fontSize: 16, color: '#212121' },
  addEntryButton: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  addEntryText: { fontSize: 16, color: '#1a237e', fontWeight: '600' },
  entryCard: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 12, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  entryCardContent: { flexDirection: 'row', flex: 1 },
  entryBadge: { backgroundColor: '#e3f2fd', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 6, marginRight: 12 },
  entryBadgeText: { color: '#1a237e', fontWeight: '600', fontSize: 12 },
  entryInfo: { flex: 1 },
  entryName: { fontSize: 16, fontWeight: '600', color: '#212121' },
  entryDetail: { fontSize: 14, color: '#666', marginTop: 4 },
  entryActions: { flexDirection: 'row', gap: 12 },
  emptyEntries: { alignItems: 'center', paddingVertical: 48 },
  emptyText: { fontSize: 14, color: '#999', marginTop: 12, textAlign: 'center' },
  input: { backgroundColor: '#fff', borderRadius: 8, padding: 16, fontSize: 16, borderWidth: 1, borderColor: '#e0e0e0' },
  textArea: { minHeight: 100, textAlignVertical: 'top' },
  saveButton: { backgroundColor: '#1a237e', height: 56, borderRadius: 12, justifyContent: 'center', alignItems: 'center', marginTop: 16 },
  saveButtonDisabled: { opacity: 0.6 },
  saveButtonText: { color: '#fff', fontSize: 18, fontWeight: '600' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', padding: 16 },
  modalContent: { backgroundColor: '#fff', borderRadius: 16, padding: 24, maxHeight: '85%' },
  modalTitle: { fontSize: 20, fontWeight: '600', color: '#1a237e', marginBottom: 16 },
  modalList: { maxHeight: 400 },
  modalItem: { padding: 16, borderBottomWidth: 1, borderBottomColor: '#e0e0e0' },
  modalItemTitle: { fontSize: 16, fontWeight: '600', color: '#212121' },
  modalItemSubtitle: { fontSize: 14, color: '#666', marginTop: 4 },
  modalItemDetail: { fontSize: 12, color: '#999', marginTop: 2 },
  modalCloseButton: { backgroundColor: '#f5f5f5', height: 48, borderRadius: 8, justifyContent: 'center', alignItems: 'center', marginTop: 16 },
  modalCloseButtonText: { fontSize: 16, fontWeight: '600', color: '#666' },
  inputLabel: { fontSize: 14, fontWeight: '600', color: '#212121', marginBottom: 8, marginTop: 12 },
  modalButtons: { flexDirection: 'row', gap: 12, marginTop: 24 },
  modalButton: { flex: 1, height: 48, borderRadius: 8, justifyContent: 'center', alignItems: 'center' },
  cancelButton: { backgroundColor: '#f5f5f5' },
  cancelButtonText: { color: '#666', fontSize: 16, fontWeight: '600' },
  confirmButton: { backgroundColor: '#1a237e' },
  confirmButtonText: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
