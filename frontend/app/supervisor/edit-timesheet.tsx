import React, { useState, useEffect } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, ScrollView, TextInput, Modal, Alert, ActivityIndicator, Platform, KeyboardAvoidingView, FlatList,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { serviceOrderAPI, employeeAPI, timesheetAPI } from '../../services/api';
import { ServiceOrder, Employee, TimesheetEntry } from '../../types';

const TIME_SLOTS: string[] = [];
for (let h = 0; h < 24; h++) {
  for (let m = 0; m < 60; m += 30) {
    TIME_SLOTS.push(`${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`);
  }
}

const WEEKDAYS = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
const MONTHS = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];

function CalendarPicker({ visible, onClose, onSelect }: { visible: boolean; onClose: () => void; onSelect: (date: string) => void }) {
  const [currentMonth, setCurrentMonth] = useState(new Date().getMonth());
  const [currentYear, setCurrentYear] = useState(new Date().getFullYear());
  const days = new Date(currentYear, currentMonth + 1, 0).getDate();
  const firstDay = new Date(currentYear, currentMonth, 1).getDay();
  const allCells = [...Array(firstDay).fill(null), ...Array.from({ length: days }, (_, i) => i + 1)];
  const prevMonth = () => { if (currentMonth === 0) { setCurrentMonth(11); setCurrentYear(y => y - 1); } else setCurrentMonth(m => m - 1); };
  const nextMonth = () => { if (currentMonth === 11) { setCurrentMonth(0); setCurrentYear(y => y + 1); } else setCurrentMonth(m => m + 1); };
  return (
    <Modal visible={visible} animationType="fade" transparent onRequestClose={onClose}>
      <View style={cs.overlay}><View style={cs.container}>
        <View style={cs.header}>
          <TouchableOpacity onPress={prevMonth}><Ionicons name="chevron-back" size={24} color="#1a237e" /></TouchableOpacity>
          <Text style={cs.monthText}>{MONTHS[currentMonth]} {currentYear}</Text>
          <TouchableOpacity onPress={nextMonth}><Ionicons name="chevron-forward" size={24} color="#1a237e" /></TouchableOpacity>
        </View>
        <View style={cs.weekRow}>{WEEKDAYS.map(d => <Text key={d} style={cs.weekDay}>{d}</Text>)}</View>
        <View style={cs.daysGrid}>
          {allCells.map((cell, idx) => (
            <TouchableOpacity key={idx} style={[cs.dayCell, cell ? cs.dayCellActive : null]} onPress={() => cell && (onSelect(`${String(cell).padStart(2, '0')}/${String(currentMonth + 1).padStart(2, '0')}/${currentYear}`), onClose())} disabled={!cell}>
              <Text style={cell ? cs.dayText : cs.dayTextEmpty}>{cell || ''}</Text>
            </TouchableOpacity>
          ))}
        </View>
        <TouchableOpacity style={cs.closeBtn} onPress={onClose}><Text style={cs.closeBtnText}>Fechar</Text></TouchableOpacity>
      </View></View>
    </Modal>
  );
}

function TimePickerModal({ visible, onClose, onSelect, title }: { visible: boolean; onClose: () => void; onSelect: (time: string) => void; title: string }) {
  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View style={ts.overlay}><View style={ts.container}>
        <Text style={ts.title}>{title}</Text>
        <FlatList data={TIME_SLOTS} keyExtractor={item => item} style={ts.list} renderItem={({ item }) => (
          <TouchableOpacity style={ts.item} onPress={() => { onSelect(item); onClose(); }}><Text style={ts.itemText}>{item}</Text></TouchableOpacity>
        )} />
        <TouchableOpacity style={ts.closeBtn} onPress={onClose}><Text style={ts.closeBtnText}>Cancelar</Text></TouchableOpacity>
      </View></View>
    </Modal>
  );
}

export default function EditTimesheetScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [serviceOrders, setServiceOrders] = useState<ServiceOrder[]>([]);
  const [allEmployees, setAllEmployees] = useState<Employee[]>([]);
  const [filteredEmployees, setFilteredEmployees] = useState<any[]>([]);
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
  const [entryDate, setEntryDate] = useState('');
  const [selectedEmployee, setSelectedEmployee] = useState<{id: string, name: string, function: string} | null>(null);
  const [serviceStart, setServiceStart] = useState('');
  const [serviceEnd, setServiceEnd] = useState('');
  const [travelStart, setTravelStart] = useState('');
  const [travelEnd, setTravelEnd] = useState('');
  const [calendarVisible, setCalendarVisible] = useState(false);
  const [timePickerField, setTimePickerField] = useState<string | null>(null);

  useEffect(() => { if (id) loadTimesheetData(); else { if (Platform.OS === 'web') window.alert('ID não fornecido'); else Alert.alert('Erro', 'ID não fornecido'); router.back(); } }, []);

  useEffect(() => {
    if (selectedSO && selectedSO.employees && selectedSO.employees.length > 0) {
      const filtered = selectedSO.employees.map(soEmp => {
        const emp = allEmployees.find(e => e.id === soEmp.employee_id);
        return emp ? { id: emp.id, name: emp.name, function: soEmp.function } : null;
      }).filter(Boolean);
      setFilteredEmployees(filtered);
    } else {
      setFilteredEmployees(allEmployees.map(e => ({ id: e.id, name: e.name, function: 'T' })));
    }
  }, [selectedSO, allEmployees]);

  const loadTimesheetData = async () => {
    try {
      const [soData, empData, tsData] = await Promise.all([serviceOrderAPI.getAll(), employeeAPI.getAll(), timesheetAPI.getById(id as string)]);
      setServiceOrders(soData); setAllEmployees(empData);
      const so = soData.find((s: ServiceOrder) => s.id === tsData.os_id);
      setSelectedSO(so || null); setEntries(tsData.entries); setObservations(tsData.observations || ''); setSupervisorFunction(tsData.supervisor_function || 'Supervisor');
    } catch { if (Platform.OS === 'web') window.alert('Erro ao carregar dados'); else Alert.alert('Erro', 'Erro ao carregar dados'); router.back(); }
    finally { setLoading(false); }
  };

  const resetEntryForm = () => { setEntryDate(''); setSelectedEmployee(null); setServiceStart(''); setServiceEnd(''); setTravelStart(''); setTravelEnd(''); };

  const MAX_ENTRIES = 12;

  const handleAddEntry = () => {
    if (!entryDate || !selectedEmployee || !serviceStart || !serviceEnd) { if (Platform.OS === 'web') window.alert('Preencha data, funcionário, início e fim'); else Alert.alert('Erro', 'Preencha data, funcionário, início e fim'); return; }
    if (editingEntryIndex === null && entries.length >= MAX_ENTRIES) { if (Platform.OS === 'web') window.alert('Limite de 12 funcionários por timesheet atingido. Crie um novo timesheet para adicionar mais funcionários.'); else Alert.alert('Limite atingido', 'Limite de 12 funcionários por timesheet. Crie um novo.'); return; }
    const newEntry: TimesheetEntry = { date: entryDate, employee_id: selectedEmployee.id, employee_name: selectedEmployee.name, employee_function: selectedEmployee.function || 'T', service_start: serviceStart, service_end: serviceEnd, travel_start: travelStart, travel_end: travelEnd };
    if (editingEntryIndex !== null) { const u = [...entries]; u[editingEntryIndex] = newEntry; setEntries(u.sort((a, b) => a.date.localeCompare(b.date) || a.employee_name.localeCompare(b.employee_name))); } else { setEntries([...entries, newEntry].sort((a, b) => a.date.localeCompare(b.date) || a.employee_name.localeCompare(b.employee_name))); }
    setEmployeeModalVisible(false); resetEntryForm();
  };

  const handleEditEntry = (index: number) => {
    const entry = entries[index]; setEditingEntryIndex(index); setEntryDate(entry.date);
    const soEmp = selectedSO?.employees?.find(e => e.employee_id === entry.employee_id);
    setSelectedEmployee({ id: entry.employee_id, name: entry.employee_name, function: soEmp?.function || entry.employee_function });
    setServiceStart(entry.service_start); setServiceEnd(entry.service_end); setTravelStart(entry.travel_start || ''); setTravelEnd(entry.travel_end || '');
    setEmployeeModalVisible(true);
  };

  const handleDeleteEntry = (index: number) => {
    if (Platform.OS === 'web') { if (window.confirm('Remover esta entrada?')) setEntries(entries.filter((_, i) => i !== index)); }
    else { Alert.alert('Confirmar', 'Remover esta entrada?', [{ text: 'Cancelar', style: 'cancel' }, { text: 'Remover', style: 'destructive', onPress: () => setEntries(entries.filter((_, i) => i !== index)) }]); }
  };

  const handleSave = async () => {
    if (!selectedSO) { if (Platform.OS === 'web') window.alert('Selecione uma O.S.'); else Alert.alert('Erro', 'Selecione uma O.S.'); return; }
    if (entries.length === 0) { if (Platform.OS === 'web') window.alert('Adicione ao menos uma entrada'); else Alert.alert('Erro', 'Adicione ao menos uma entrada'); return; }
    if (entries.length > 12) { if (Platform.OS === 'web') window.alert('Máximo de 12 funcionários por timesheet. Remova entradas extras ou crie um novo timesheet.'); else Alert.alert('Limite atingido', 'Máximo de 12 funcionários por timesheet.'); return; }
    setSaving(true);
    try {
      await timesheetAPI.update(id as string, selectedSO.id, entries, observations, supervisorFunction);
      if (Platform.OS === 'web') { window.alert('Timesheet atualizado!'); router.back(); }
      else { Alert.alert('Sucesso', 'Timesheet atualizado!', [{ text: 'OK', onPress: () => router.back() }]); }
    } catch (error: any) {
      const msg = error?.response?.data?.detail || 'Erro ao atualizar timesheet';
      if (Platform.OS === 'web') window.alert(msg); else Alert.alert('Erro', msg);
    } finally { setSaving(false); }
  };

  const openTimePicker = (field: string) => setTimePickerField(field);
  const handleTimeSelect = (time: string) => {
    switch (timePickerField) { case 'serviceStart': setServiceStart(time); break; case 'serviceEnd': setServiceEnd(time); break; case 'travelStart': setTravelStart(time); break; case 'travelEnd': setTravelEnd(time); break; }
  };
  const getTimePickerTitle = () => {
    switch (timePickerField) { case 'serviceStart': return 'Início do Serviço'; case 'serviceEnd': return 'Fim do Serviço'; case 'travelStart': return 'Início da Viagem'; case 'travelEnd': return 'Fim da Viagem'; default: return 'Selecionar Horário'; }
  };

  if (loading) return <View style={s.center}><ActivityIndicator size="large" color="#1a237e" /></View>;

  return (
    <SafeAreaView style={s.container}>
      <View style={s.header}>
        <TouchableOpacity onPress={() => router.back()} style={s.backBtn}><Ionicons name="arrow-back" size={24} color="#1a237e" /></TouchableOpacity>
        <Text style={s.title}>Editar Timesheet</Text>
        <View style={{ width: 40 }} />
      </View>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={s.scrollContent}>
          <View style={s.section}>
            <Text style={s.label}>Ordem de Serviço *</Text>
            <TouchableOpacity style={s.selectButton} onPress={() => setSOModalVisible(true)}>
              <Text style={selectedSO ? s.selectTextSelected : s.selectText}>{selectedSO ? `${selectedSO.os_number} - ${selectedSO.client}` : 'Selecionar O.S.'}</Text>
              <Ionicons name="chevron-down" size={20} color="#666" />
            </TouchableOpacity>
          </View>
          <View style={s.section}>
            <View style={s.sectionHeader}>
              <Text style={s.label}>Entradas ({entries.length}/12)</Text>
              {entries.length < 12 ? (
                <TouchableOpacity onPress={() => { setEditingEntryIndex(null); resetEntryForm(); setEmployeeModalVisible(true); }} style={s.addEntryBtn}><Ionicons name="add" size={20} color="#1a237e" /><Text style={s.addEntryText}>Adicionar</Text></TouchableOpacity>
              ) : (
                <View style={s.addEntryBtn}><Ionicons name="lock-closed" size={16} color="#999" /><Text style={{ fontSize: 14, color: '#999' }}>Limite atingido</Text></View>
              )}
            </View>
            {entries.length >= 12 && (
              <View style={{ backgroundColor: '#fff3e0', padding: 10, borderRadius: 8, marginBottom: 8, borderWidth: 1, borderColor: '#ffb74d' }}>
                <Text style={{ color: '#e65100', fontSize: 13, textAlign: 'center' }}>Máximo de 12 funcionários atingido. Para adicionar mais, crie um novo timesheet.</Text>
              </View>
            )}
            {entries.map((entry, i) => (
              <View key={i} style={s.entryCard}>
                <View style={s.entryCardContent}>
                  <View style={s.entryBadge}><Text style={s.entryBadgeText}>{entry.employee_function}</Text></View>
                  <View style={s.entryInfo}>
                    <Text style={s.entryName}>{entry.employee_name}</Text>
                    <Text style={s.entryDetail}>Data: {entry.date}</Text>
                    <Text style={s.entryDetail}>Serviço: {entry.service_start} - {entry.service_end}</Text>
                    {entry.travel_start && entry.travel_start !== '0' && entry.travel_start !== '' ? <Text style={s.entryDetail}>Viagem: {entry.travel_start} - {entry.travel_end}</Text> : null}
                  </View>
                </View>
                <View style={s.entryActions}>
                  <TouchableOpacity onPress={() => handleEditEntry(i)}><Ionicons name="pencil" size={20} color="#1a237e" /></TouchableOpacity>
                  <TouchableOpacity onPress={() => handleDeleteEntry(i)}><Ionicons name="trash" size={20} color="#d32f2f" /></TouchableOpacity>
                </View>
              </View>
            ))}
            {entries.length === 0 && <View style={s.emptyEntries}><Ionicons name="people-outline" size={48} color="#ccc" /><Text style={s.emptyText}>Nenhuma entrada</Text></View>}
          </View>
          {/* Supervisor Function */}
          <View style={s.section}>
            <Text style={s.label}>Função do Supervisor</Text>
            <TouchableOpacity style={s.selectButton} onPress={() => setFunctionPickerVisible(true)}>
              <Text style={supervisorFunction !== 'Supervisor' ? s.selectTextSelected : s.selectText}>{supervisorFunction}</Text>
              <Ionicons name="chevron-down" size={20} color="#666" />
            </TouchableOpacity>
          </View>

          <View style={s.section}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
              <Text style={s.label}>Observações</Text>
              <Text style={{ fontSize: 12, color: observations.length >= 800 ? '#d32f2f' : '#999' }}>{observations.length}/800</Text>
            </View>
            <TextInput style={[s.input, s.textArea]} placeholder="Observações (opcional)" value={observations} onChangeText={(text) => { if (text.length <= 800) setObservations(text); }} multiline numberOfLines={4} maxLength={800} />
          </View>
          <TouchableOpacity style={[s.saveButton, saving && s.saveButtonDisabled]} onPress={handleSave} disabled={saving}>
            {saving ? <ActivityIndicator color="#fff" /> : <Text style={s.saveButtonText}>Atualizar Timesheet</Text>}
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>

      {/* SO Modal */}
      <Modal visible={soModalVisible} animationType="slide" transparent onRequestClose={() => setSOModalVisible(false)}>
        <View style={s.modalOverlay}><View style={s.modalContent}>
          <Text style={s.modalTitle}>Selecionar O.S.</Text>
          <ScrollView style={s.modalList}>{serviceOrders.map(so => (
            <TouchableOpacity key={so.id} style={s.modalItem} onPress={() => { setSelectedSO(so); setSOModalVisible(false); }}>
              <Text style={s.modalItemTitle}>{so.os_number}</Text><Text style={s.modalItemSub}>{so.client} - {so.location}</Text>
            </TouchableOpacity>
          ))}</ScrollView>
          <TouchableOpacity style={s.modalCloseBtn} onPress={() => setSOModalVisible(false)}><Text style={s.modalCloseBtnText}>Fechar</Text></TouchableOpacity>
        </View></View>
      </Modal>

      {/* Entry Form Modal */}
      <Modal visible={employeeModalVisible} animationType="slide" transparent onRequestClose={() => setEmployeeModalVisible(false)}>
        <View style={s.modalOverlay}><View style={s.modalContent}><ScrollView>
          <Text style={s.modalTitle}>{editingEntryIndex !== null ? 'Editar Entrada' : 'Adicionar Entrada'}</Text>
          <Text style={s.inputLabel}>Data *</Text>
          <TouchableOpacity style={s.selectButton} onPress={() => setCalendarVisible(true)}>
            <Text style={entryDate ? s.selectTextSelected : s.selectText}>{entryDate || 'Selecionar data'}</Text>
            <Ionicons name="calendar" size={20} color="#1a237e" />
          </TouchableOpacity>
          <Text style={s.inputLabel}>Funcionário *</Text>
          <TouchableOpacity style={s.selectButton} onPress={() => setEmployeePickerVisible(true)}>
            <Text style={selectedEmployee ? s.selectTextSelected : s.selectText}>{selectedEmployee ? `${selectedEmployee.name} (${selectedEmployee.function})` : 'Selecionar'}</Text>
            <Ionicons name="chevron-down" size={20} color="#666" />
          </TouchableOpacity>
          <Text style={s.inputLabel}>Serviço - Início *</Text>
          <TouchableOpacity style={s.selectButton} onPress={() => openTimePicker('serviceStart')}>
            <Text style={serviceStart ? s.selectTextSelected : s.selectText}>{serviceStart || 'Selecionar horário'}</Text>
            <Ionicons name="time" size={20} color="#1a237e" />
          </TouchableOpacity>
          <Text style={s.inputLabel}>Serviço - Fim *</Text>
          <TouchableOpacity style={s.selectButton} onPress={() => openTimePicker('serviceEnd')}>
            <Text style={serviceEnd ? s.selectTextSelected : s.selectText}>{serviceEnd || 'Selecionar horário'}</Text>
            <Ionicons name="time" size={20} color="#1a237e" />
          </TouchableOpacity>
          <Text style={s.inputLabel}>Viagem - Início</Text>
          <TouchableOpacity style={s.selectButton} onPress={() => openTimePicker('travelStart')}>
            <Text style={travelStart ? s.selectTextSelected : s.selectText}>{travelStart || 'Selecionar horário'}</Text>
            <Ionicons name="time" size={20} color="#666" />
          </TouchableOpacity>
          <Text style={s.inputLabel}>Viagem - Fim</Text>
          <TouchableOpacity style={s.selectButton} onPress={() => openTimePicker('travelEnd')}>
            <Text style={travelEnd ? s.selectTextSelected : s.selectText}>{travelEnd || 'Selecionar horário'}</Text>
            <Ionicons name="time" size={20} color="#666" />
          </TouchableOpacity>
          <View style={s.modalBtns}>
            <TouchableOpacity style={[s.modalBtn, s.cancelBtn]} onPress={() => setEmployeeModalVisible(false)}><Text style={s.cancelText}>Cancelar</Text></TouchableOpacity>
            <TouchableOpacity style={[s.modalBtn, s.confirmBtn]} onPress={handleAddEntry}><Text style={s.confirmText}>{editingEntryIndex !== null ? 'Atualizar' : 'Adicionar'}</Text></TouchableOpacity>
          </View>
        </ScrollView></View></View>
      </Modal>

      {/* Employee Picker */}
      <Modal visible={employeePickerVisible} animationType="slide" transparent onRequestClose={() => setEmployeePickerVisible(false)}>
        <View style={s.modalOverlay}><View style={s.modalContent}>
          <Text style={s.modalTitle}>Selecionar Funcionário</Text>
          <ScrollView style={s.modalList}>
            {filteredEmployees.length === 0 ? <Text style={s.emptyText}>Nenhum funcionário vinculado</Text> :
              filteredEmployees.map((emp: any) => (
                <TouchableOpacity key={emp.id} style={s.modalItem} onPress={() => { setSelectedEmployee(emp); setEmployeePickerVisible(false); }}>
                  <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                    <View style={s.entryBadge}><Text style={s.entryBadgeText}>{emp.function}</Text></View>
                    <Text style={s.modalItemTitle}>{emp.name}</Text>
                  </View>
                </TouchableOpacity>
              ))
            }
          </ScrollView>
          <TouchableOpacity style={s.modalCloseBtn} onPress={() => setEmployeePickerVisible(false)}><Text style={s.modalCloseBtnText}>Fechar</Text></TouchableOpacity>
        </View></View>
      </Modal>

      {/* Function Picker Modal */}
      <Modal visible={functionPickerVisible} animationType="slide" transparent onRequestClose={() => setFunctionPickerVisible(false)}>
        <View style={s.modalOverlay}><View style={s.modalContent}>
          <Text style={s.modalTitle}>Função do Supervisor</Text>
          <ScrollView style={s.modalList}>
            {SUPERVISOR_FUNCTIONS.map(fn => (
              <TouchableOpacity key={fn} style={[s.modalItem, supervisorFunction === fn && { backgroundColor: '#e8eaf6' }]} onPress={() => { setSupervisorFunction(fn); setFunctionPickerVisible(false); }}>
                <Text style={[s.modalItemTitle, supervisorFunction === fn && { color: '#1a237e', fontWeight: '700' }]}>{fn}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
          <TouchableOpacity style={s.modalCloseBtn} onPress={() => setFunctionPickerVisible(false)}><Text style={s.modalCloseBtnText}>Fechar</Text></TouchableOpacity>
        </View></View>
      </Modal>

      <CalendarPicker visible={calendarVisible} onClose={() => setCalendarVisible(false)} onSelect={setEntryDate} />
      <TimePickerModal visible={!!timePickerField} onClose={() => setTimePickerField(null)} onSelect={handleTimeSelect} title={getTimePickerTitle()} />
    </SafeAreaView>
  );
}

const cs = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', padding: 16 },
  container: { backgroundColor: '#fff', borderRadius: 16, padding: 20 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  monthText: { fontSize: 18, fontWeight: '600', color: '#1a237e' },
  weekRow: { flexDirection: 'row', justifyContent: 'space-around', marginBottom: 8 },
  weekDay: { width: 40, textAlign: 'center', fontSize: 12, fontWeight: '600', color: '#666' },
  daysGrid: { flexDirection: 'row', flexWrap: 'wrap' },
  dayCell: { width: '14.28%', height: 40, justifyContent: 'center', alignItems: 'center' } as any,
  dayCellActive: {},
  dayText: { fontSize: 16, color: '#212121' },
  dayTextEmpty: { fontSize: 16, color: 'transparent' },
  closeBtn: { backgroundColor: '#f5f5f5', height: 44, borderRadius: 8, justifyContent: 'center', alignItems: 'center', marginTop: 12 },
  closeBtnText: { fontSize: 16, fontWeight: '600', color: '#666' },
});

const ts = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', padding: 16 },
  container: { backgroundColor: '#fff', borderRadius: 16, padding: 20, maxHeight: '70%' },
  title: { fontSize: 18, fontWeight: '600', color: '#1a237e', marginBottom: 12, textAlign: 'center' },
  list: { maxHeight: 350 },
  item: { padding: 14, borderBottomWidth: 1, borderBottomColor: '#f0f0f0', alignItems: 'center' },
  itemText: { fontSize: 18, color: '#212121' },
  closeBtn: { backgroundColor: '#f5f5f5', height: 44, borderRadius: 8, justifyContent: 'center', alignItems: 'center', marginTop: 12 },
  closeBtnText: { fontSize: 16, fontWeight: '600', color: '#666' },
});

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 12, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#e0e0e0' },
  backBtn: { padding: 8 },
  title: { fontSize: 20, fontWeight: '600', color: '#1a237e' },
  scrollContent: { padding: 16 },
  section: { marginBottom: 24 },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  label: { fontSize: 16, fontWeight: '600', color: '#212121', marginBottom: 8 },
  selectButton: { backgroundColor: '#fff', borderRadius: 8, padding: 16, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderWidth: 1, borderColor: '#e0e0e0' },
  selectText: { fontSize: 16, color: '#999' },
  selectTextSelected: { fontSize: 16, color: '#212121' },
  addEntryBtn: { flexDirection: 'row', alignItems: 'center', gap: 4 },
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
  modalItemSub: { fontSize: 14, color: '#666', marginTop: 4 },
  modalCloseBtn: { backgroundColor: '#f5f5f5', height: 48, borderRadius: 8, justifyContent: 'center', alignItems: 'center', marginTop: 16 },
  modalCloseBtnText: { fontSize: 16, fontWeight: '600', color: '#666' },
  inputLabel: { fontSize: 14, fontWeight: '600', color: '#212121', marginBottom: 8, marginTop: 12 },
  modalBtns: { flexDirection: 'row', gap: 12, marginTop: 24 },
  modalBtn: { flex: 1, height: 48, borderRadius: 8, justifyContent: 'center', alignItems: 'center' },
  cancelBtn: { backgroundColor: '#f5f5f5' },
  cancelText: { color: '#666', fontSize: 16, fontWeight: '600' },
  confirmBtn: { backgroundColor: '#1a237e' },
  confirmText: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
