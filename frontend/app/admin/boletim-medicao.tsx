import React, { useState, useEffect } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, ScrollView, TextInput,
  ActivityIndicator, Platform, Alert, Modal,
} from 'react-native';
import DateTimePicker from '@react-native-community/datetimepicker';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { bmAPI, clientPriceAPI, holidaysAPI } from '../../services/api';
import { BACKEND_URL } from '../../services/config';
import AsyncStorage from '@react-native-async-storage/async-storage';
import api from '../../services/api';

const showMsg = (msg: string) => {
  if (Platform.OS === 'web') window.alert(msg);
  else Alert.alert('Info', msg);
};

export default function BMScreen() {
  const router = useRouter();
  const [tab, setTab] = useState<'bm' | 'prices' | 'holidays'>('bm');
  const [bms, setBms] = useState<any[]>([]);
  const [prices, setPrices] = useState<any[]>([]);
  const [serviceOrders, setServiceOrders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Create BM state
  const [showCreate, setShowCreate] = useState(false);
  const [selectedOS, setSelectedOS] = useState('');
  const [calcResult, setCalcResult] = useState<any>(null);
  const [calcLoading, setCalcLoading] = useState(false);
  const [bmForm, setBmForm] = useState({ data: new Date().toLocaleDateString('pt-BR'), rev: '0', po_number: '', proposta: '', cod: '', incluirImpostos: false, impostoPct: '0' });

  // Timesheet selection state
  const [availableTimesheets, setAvailableTimesheets] = useState<any[]>([]);
  const [selectedTimesheets, setSelectedTimesheets] = useState<string[]>([]);
  const [loadingTimesheets, setLoadingTimesheets] = useState(false);
  // Date filter state
  const [dataInicio, setDataInicio] = useState('');
  const [dataFim, setDataFim] = useState('');
  const [selectedPriceTableId, setSelectedPriceTableId] = useState<string>('');
  const [showPriceTableModal, setShowPriceTableModal] = useState(false);
  const [priceTableSearch, setPriceTableSearch] = useState('');
  const [calcMode, setCalcMode] = useState<'onshore' | 'offshore'>('onshore');
  const [showDatePicker, setShowDatePicker] = useState<null | 'inicio' | 'fim'>(null);

  // Helpers to convert "DD/MM/YYYY" <-> Date
  const ptToDate = (s: string): Date | null => {
    if (!s) return null;
    const parts = s.split('/');
    if (parts.length !== 3) return null;
    const [d, m, y] = parts.map(Number);
    if (!d || !m || !y) return null;
    return new Date(y, m - 1, d);
  };
  const dateToPt = (d: Date): string => {
    const dd = String(d.getDate()).padStart(2, '0');
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const yy = d.getFullYear();
    return `${dd}/${mm}/${yy}`;
  };

  // Edit BM state
  const [editingBMId, setEditingBMId] = useState<string | null>(null);

  // Price table state
  const [showPriceForm, setShowPriceForm] = useState(false);
  const [priceForm, setPriceForm] = useState({ client_name: '', label: '', prices: [] as any[] });
  const [editingPriceId, setEditingPriceId] = useState<string | null>(null);

  // Holidays state
  const [holidays, setHolidays] = useState<any[]>([]);
  const [holidaysLoaded, setHolidaysLoaded] = useState(false);
  const [holidayYear, setHolidayYear] = useState<number>(new Date().getFullYear());
  const [newHolidayDate, setNewHolidayDate] = useState('');
  const [newHolidayDesc, setNewHolidayDesc] = useState('');
  const [showHolidayDatePicker, setShowHolidayDatePicker] = useState(false);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [bmData, priceData, soData] = await Promise.all([
        bmAPI.list(), clientPriceAPI.getAll(), api.get('/service-orders').then(r => r.data),
      ]);
      setBms(bmData);
      setPrices(priceData);
      setServiceOrders(soData);
    } catch { showMsg('Erro ao carregar dados'); }
    finally { setLoading(false); }
  };

  const handleSelectOS = async (osId: string) => {
    setSelectedOS(osId);
    setCalcResult(null);
    setSelectedTimesheets([]);
    setDataInicio('');
    setDataFim('');
    setLoadingTimesheets(true);
    try {
      const ts = await bmAPI.getTimesheets(osId);
      setAvailableTimesheets(ts);
      // Select all by default
      setSelectedTimesheets(ts.map((t: any) => t.id));
    } catch { showMsg('Erro ao carregar timesheets'); }
    finally { setLoadingTimesheets(false); }

    // Auto-fill proposal data from the selected OS
    const so = serviceOrders.find((s: any) => s.id === osId);
    if (so && so.proposal_id) {
      try {
        const proposta = await api.get(`/proposals/${so.proposal_id}`);
        setBmForm(prev => ({
          ...prev,
          po_number: so.po_number || proposta.data.po_number || '',
          proposta: proposta.data.numero_proposta || '',
        }));
      } catch {
        // Proposal might not exist, just use PO from OS
        setBmForm(prev => ({
          ...prev,
          po_number: so.po_number || '',
        }));
      }
    } else if (so && so.po_number) {
      setBmForm(prev => ({ ...prev, po_number: so.po_number }));
    }
  };

  const toggleTimesheet = (id: string) => {
    setSelectedTimesheets(prev =>
      prev.includes(id) ? prev.filter(t => t !== id) : [...prev, id]
    );
  };

  const toggleAllTimesheets = () => {
    if (selectedTimesheets.length === availableTimesheets.length) {
      setSelectedTimesheets([]);
    } else {
      setSelectedTimesheets(availableTimesheets.map((t: any) => t.id));
    }
  };

  const handleCalculate = async () => {
    if (!selectedOS) return showMsg('Selecione uma O.S.');
    if (selectedTimesheets.length === 0) return showMsg('Selecione ao menos uma timesheet');
    setCalcLoading(true);
    try {
      const result = await bmAPI.calculate(selectedOS, {
        timesheet_ids: selectedTimesheets,
        data_inicio: dataInicio,
        data_fim: dataFim,
        calc_mode: calcMode,
        price_table_id: selectedPriceTableId || undefined,
      });
      setCalcResult(result);
      if (!result.has_price_table) showMsg('Atenção: Não há tabela de preços cadastrada para o cliente ' + result.client + '. Os valores estarão zerados.');
    } catch { showMsg('Erro ao calcular BM'); }
    finally { setCalcLoading(false); }
  };

  const handleEditBM = async (bm: any) => {
    setEditingBMId(bm.id);
    setSelectedOS(bm.os_id);
    setSelectedPriceTableId(bm.price_table_id || '');
    const hasImpostos = (bm.impostos || 0) > 0;
    // Reverse-calculate percentage from stored impostos value
    const pct = hasImpostos && bm.subtotal > 0 ? String(Math.round((bm.impostos / bm.subtotal) * 10000) / 100) : '0';
    setBmForm({
      data: bm.data || new Date().toLocaleDateString('pt-BR'),
      rev: bm.rev || '0',
      po_number: bm.po_number || '',
      proposta: bm.proposta || '',
      cod: bm.cod || '',
      incluirImpostos: hasImpostos,
      impostoPct: pct,
    });
    setCalcResult({ items: bm.items, subtotal: bm.subtotal, has_price_table: true });
    // Load timesheets for the OS
    setLoadingTimesheets(true);
    try {
      const ts = await bmAPI.getTimesheets(bm.os_id);
      setAvailableTimesheets(ts);
      setSelectedTimesheets(ts.map((t: any) => t.id));
    } catch {}
    finally { setLoadingTimesheets(false); }
    setShowCreate(true);
  };

  const handleCreateBM = async () => {
    if (!calcResult) return showMsg('Calcule primeiro os itens');
    const items = calcResult.items;
    const subtotal = items.reduce((s: number, i: any) => s + i.valor_total, 0);
    const impostoPct = bmForm.incluirImpostos ? (parseFloat(bmForm.impostoPct) || 0) : 0;
    const impostos = Math.round(subtotal * impostoPct / 100 * 100) / 100;
    // Generate periodo from dataInicio/dataFim or calcResult dates
    const periodoStart = dataInicio || calcResult.data_inicial || '';
    const periodoEnd = dataFim || calcResult.data_final || '';
    const periodo = periodoStart && periodoEnd ? `${periodoStart} a ${periodoEnd}` : periodoStart || periodoEnd || new Date().toLocaleDateString('pt-BR');
    const payload = {
      os_id: selectedOS,
      periodo,
      data: bmForm.data || new Date().toLocaleDateString('pt-BR'),
      rev: bmForm.rev,
      po_number: bmForm.po_number,
      proposta: bmForm.proposta,
      cod: bmForm.cod,
      price_table_id: selectedPriceTableId || '',
      items,
      subtotal: Math.round(subtotal * 100) / 100,
      impostos,
      valor_total: Math.round((subtotal + impostos) * 100) / 100,
    };
    try {
      if (editingBMId) {
        await bmAPI.update(editingBMId, payload);
        showMsg('Boletim de Medição atualizado com sucesso!');
      } else {
        await bmAPI.create(payload);
        showMsg('Boletim de Medição criado com sucesso!');
      }
      setShowCreate(false);
      setCalcResult(null);
      setSelectedOS('');
      setEditingBMId(null);
      setAvailableTimesheets([]);
      setSelectedTimesheets([]);
      setDataInicio('');
      setDataFim('');
      setBmForm({ data: new Date().toLocaleDateString('pt-BR'), rev: '0', po_number: '', proposta: '', cod: '', incluirImpostos: false, impostoPct: '0' });
      loadData();
    } catch { showMsg(editingBMId ? 'Erro ao atualizar BM' : 'Erro ao criar BM'); }
  };

  const handleDeleteBM = async (id: string) => {
    if (Platform.OS === 'web' && !window.confirm('Excluir este BM?')) return;
    try { await bmAPI.delete(id); loadData(); } catch { showMsg('Erro ao excluir'); }
  };

  const handleOpenPDF = async (id: string) => {
    const token = await AsyncStorage.getItem('token');
    const baseURL = BACKEND_URL + '/api';
    const url = `${baseURL}/bm/${id}/pdf?token=${token}&t=${Date.now()}`;
    if (Platform.OS === 'web') window.open(url, '_blank');
  };

  // Price table functions
  const FUNCTION_OPTIONS = [
    { code: 'E', name: 'ENGENHEIRO' }, { code: 'EN', name: 'ENCARREGADO' },
    { code: 'Sup', name: 'SUPERVISOR' }, { code: 'T', name: 'TÉCNICO' },
    { code: 'M', name: 'MECÂNICO' }, { code: 'TS', name: 'TÉCNICO DE SEGURANÇA' },
  ];

  const openPriceForm = (existing?: any) => {
    if (existing) {
      setEditingPriceId(existing.id);
      // Format numbers to BR string for editing (2850.72 -> "2.850,72")
      const pricesAsStrings = (existing.prices || []).map((p: any) => ({
        ...p,
        day_rate: typeof p.day_rate === 'number' ? formatBRNumber(p.day_rate) : (p.day_rate || ''),
        day_discount_pct: p.day_discount_pct != null ? String(p.day_discount_pct).replace('.', ',') : '',
      }));
      setPriceForm({ client_name: existing.client_name, label: existing.label || '', prices: pricesAsStrings });
    } else {
      setEditingPriceId(null);
      setPriceForm({ client_name: '', label: '', prices: FUNCTION_OPTIONS.map(f => ({ function_code: f.code, function_name: f.name, day_rate: '', day_discount_pct: '' })) });
    }
    setShowPriceForm(true);
  };

  const handleSavePrice = async () => {
    if (!priceForm.client_name) return showMsg('Informe o nome do cliente');
    try {
      // Ensure each price entry has both day_rate and night_rate (backend requires both)
      const normalized = {
        client_name: priceForm.client_name,
        label: priceForm.label || '',
        prices: (priceForm.prices || []).map((p: any) => {
          const day = parseBR(p.day_rate);
          const night = p.night_rate != null && p.night_rate !== '' ? parseBR(p.night_rate) : +(day * 1.2).toFixed(2);
          let disc = parseBR(p.day_discount_pct);
          if (disc < 0) disc = 0;
          if (disc > 100) disc = 100;
          return {
            function_code: p.function_code,
            function_name: p.function_name || p.function_code,
            day_rate: day,
            night_rate: night,
            day_discount_pct: disc,
          };
        }),
      };
      if (editingPriceId) {
        await clientPriceAPI.update(editingPriceId, normalized);
      } else {
        await clientPriceAPI.create(normalized);
      }
      showMsg('Tabela de preços salva!');
      setShowPriceForm(false);
      loadData();
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Erro ao salvar tabela';
      showMsg(typeof detail === 'string' ? detail : 'Erro ao salvar tabela');
    }
  };

  const handleDuplicatePrice = (pt: any) => {
    const pricesAsStrings = (pt.prices || []).map((p: any) => ({
      ...p,
      day_rate: typeof p.day_rate === 'number' ? formatBRNumber(p.day_rate) : (p.day_rate || ''),
      day_discount_pct: p.day_discount_pct != null ? String(p.day_discount_pct).replace('.', ',') : '',
    }));
    setEditingPriceId(null);  // null => new table
    setPriceForm({
      client_name: pt.client_name,
      label: pt.label ? `${pt.label} - Cópia` : 'Cópia',
      prices: pricesAsStrings,
    });
    setShowPriceForm(true);
  };

  const handleDeletePrice = async (id: string) => {
    if (Platform.OS === 'web' && !window.confirm('Excluir esta tabela de preços?')) return;
    try { await clientPriceAPI.delete(id); loadData(); } catch { showMsg('Erro ao excluir'); }
  };

  // ===== Holidays handlers =====
  const loadHolidays = async (year: number) => {
    try {
      const data = await holidaysAPI.list(year);
      setHolidays(data || []);
    } catch {
      setHolidays([]);
      showMsg('Não foi possível carregar feriados (verifique se o backend está atualizado)');
    } finally {
      setHolidaysLoaded(true);
    }
  };

  const handleAddHoliday = async () => {
    if (!newHolidayDate) return showMsg('Informe a data');
    try {
      await holidaysAPI.create({ date: newHolidayDate, description: newHolidayDesc });
      setNewHolidayDate('');
      setNewHolidayDesc('');
      loadHolidays(holidayYear);
    } catch (err: any) {
      const detail = err?.response?.data?.detail || 'Erro ao adicionar feriado';
      showMsg(typeof detail === 'string' ? detail : 'Erro ao adicionar feriado');
    }
  };

  const handleDeleteHoliday = async (id: string) => {
    if (Platform.OS === 'web' && !window.confirm('Excluir este feriado regional?')) return;
    try {
      await holidaysAPI.delete(id);
      loadHolidays(holidayYear);
    } catch (err: any) {
      const detail = err?.response?.data?.detail || 'Erro ao excluir feriado';
      showMsg(typeof detail === 'string' ? detail : 'Erro ao excluir feriado');
    }
  };

  const updatePriceRow = (idx: number, field: string, value: string) => {
    const updated = [...priceForm.prices];
    // Keep value as raw string while user is typing - parse only on save
    updated[idx] = { ...updated[idx], [field]: value };
    setPriceForm({ ...priceForm, prices: updated });
  };

  // Parse Brazilian-format number string ("2.850,72" or "2850,72" or "2850.72") to number
  const parseBR = (val: any): number => {
    if (val == null || val === '') return 0;
    if (typeof val === 'number') return val;
    const cleaned = String(val).trim().replace(/\./g, '').replace(',', '.');
    const n = parseFloat(cleaned);
    return isNaN(n) ? 0 : n;
  };

  // Format number to Brazilian display string ("2850.72" -> "2.850,72")
  const formatBRNumber = (n: number): string => {
    if (n == null || isNaN(n)) return '';
    return n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const formatCurrency = (v: number) => {
    return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  if (loading) return <View style={s.center}><ActivityIndicator size="large" color="#000000" /></View>;

  return (
    <SafeAreaView style={s.container}>
      <View style={s.header}>
        <TouchableOpacity onPress={() => router.replace('/admin')} style={s.backBtn} data-testid="bm-back-btn">
          <Ionicons name="arrow-back" size={24} color="#000000" />
        </TouchableOpacity>
        <Text style={s.title}>Boletim de Medição</Text>
        <View style={{ width: 40 }} />
      </View>

      <View style={s.tabs}>
        <TouchableOpacity style={[s.tab, tab === 'bm' && s.tabActive]} onPress={() => setTab('bm')} data-testid="tab-bm">
          <Text style={[s.tabText, tab === 'bm' && s.tabTextActive]}>Boletins</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[s.tab, tab === 'prices' && s.tabActive]} onPress={() => setTab('prices')} data-testid="tab-prices">
          <Text style={[s.tabText, tab === 'prices' && s.tabTextActive]}>Tabela de Preços</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[s.tab, tab === 'holidays' && s.tabActive]} onPress={() => { setTab('holidays'); loadHolidays(holidayYear); }} testID="tab-holidays">
          <Text style={[s.tabText, tab === 'holidays' && s.tabTextActive]}>Feriados</Text>
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={s.scrollContent}>
        {tab === 'bm' && (
          <>
            <TouchableOpacity style={s.addBtn} onPress={() => { setEditingBMId(null); setSelectedPriceTableId(''); setShowCreate(true); }} data-testid="create-bm-btn">
              <Ionicons name="add-circle" size={22} color="#fff" />
              <Text style={s.addBtnText}>Novo Boletim</Text>
            </TouchableOpacity>

            {bms.length === 0 ? (
              <View style={s.empty}><Ionicons name="document-outline" size={64} color="#ccc" /><Text style={s.emptyText}>Nenhum boletim criado</Text></View>
            ) : bms.map(bm => (
              <View key={bm.id} style={s.card} data-testid={`bm-card-${bm.id}`}>
                <View style={s.cardHeader}>
                  <View style={s.osBadge}><Text style={s.osBadgeText}>{bm.os_number}</Text></View>
                  <View style={s.cardInfo}>
                    <Text style={s.cardClient}>{bm.client}</Text>
                    <Text style={s.cardMeta}>{bm.periodo} | Rev. {bm.rev}</Text>
                  </View>
                  <Text style={s.cardTotal}>{formatCurrency(bm.valor_total)}</Text>
                </View>
                <View style={s.cardActions}>
                  <TouchableOpacity style={s.actionBtn} onPress={() => handleOpenPDF(bm.id)} data-testid={`bm-pdf-${bm.id}`}>
                    <Ionicons name="eye-outline" size={18} color="#000000" /><Text style={s.actionText}>Ver PDF</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={s.actionBtn} onPress={() => handleEditBM(bm)} data-testid={`bm-edit-${bm.id}`}>
                    <Ionicons name="create-outline" size={18} color="#000000" /><Text style={s.actionText}>Editar</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={[s.actionBtn, { borderColor: '#d32f2f' }]} onPress={() => handleDeleteBM(bm.id)} data-testid={`bm-delete-${bm.id}`}>
                    <Ionicons name="trash-outline" size={18} color="#d32f2f" /><Text style={[s.actionText, { color: '#d32f2f' }]}>Excluir</Text>
                  </TouchableOpacity>
                </View>
              </View>
            ))}
          </>
        )}

        {tab === 'prices' && (
          <>
            <TouchableOpacity style={s.addBtn} onPress={() => openPriceForm()} data-testid="create-price-btn">
              <Ionicons name="add-circle" size={22} color="#fff" />
              <Text style={s.addBtnText}>Nova Tabela de Preços</Text>
            </TouchableOpacity>

            {prices.length === 0 ? (
              <View style={s.empty}><Ionicons name="pricetag-outline" size={64} color="#ccc" /><Text style={s.emptyText}>Nenhuma tabela cadastrada</Text></View>
            ) : prices.map(pt => (
              <View key={pt.id} style={s.card} data-testid={`price-card-${pt.id}`}>
                <View style={s.cardHeader}>
                  <Text style={s.cardClient}>{pt.client_name}{pt.label ? ` — ${pt.label}` : ''}</Text>
                </View>
                {(pt.prices || []).map((p: any, i: number) => (
                  <View key={i} style={s.priceRow}>
                    <Text style={s.priceFunc}>{p.function_name}</Text>
                    <Text style={s.priceVal}>Diurno: {formatCurrency(p.day_rate)}</Text>
                    <Text style={s.priceVal}>Noturno: {formatCurrency(p.day_rate * 1.2)}</Text>
                  </View>
                ))}
                <View style={s.cardActions}>
                  <TouchableOpacity style={s.actionBtn} onPress={() => openPriceForm(pt)}>
                    <Ionicons name="create-outline" size={18} color="#000000" /><Text style={s.actionText}>Editar</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={s.actionBtn} onPress={() => handleDuplicatePrice(pt)} testID={`price-duplicate-${pt.id}`}>
                    <Ionicons name="copy-outline" size={18} color="#000000" /><Text style={s.actionText}>Duplicar</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={[s.actionBtn, { borderColor: '#d32f2f' }]} onPress={() => handleDeletePrice(pt.id)}>
                    <Ionicons name="trash-outline" size={18} color="#d32f2f" /><Text style={[s.actionText, { color: '#d32f2f' }]}>Excluir</Text>
                  </TouchableOpacity>
                </View>
              </View>
            ))}
          </>
        )}

        {tab === 'holidays' && (
          <>
            <View style={{ backgroundColor: '#fff', borderRadius: 8, padding: 16, marginBottom: 12, borderWidth: 1, borderColor: '#e0e0e0' }}>
              <Text style={{ fontSize: 13, color: '#666', marginBottom: 12 }}>
                Feriados nacionais brasileiros são detectados automaticamente. Use esta tela para cadastrar feriados regionais (estaduais ou municipais) que devem contar como Domingo (+100%) no cálculo do BM.
              </Text>
              <Text style={[s.label, { marginTop: 4 }]}>Ano</Text>
              <View style={{ flexDirection: 'row', gap: 8, marginBottom: 12 }}>
                {[holidayYear - 1, holidayYear, holidayYear + 1].map(y => (
                  <TouchableOpacity
                    key={y}
                    style={{
                      paddingVertical: 8, paddingHorizontal: 14, borderRadius: 6,
                      backgroundColor: holidayYear === y ? '#000' : '#f5f5f5',
                      borderWidth: 1, borderColor: holidayYear === y ? '#000' : '#e0e0e0',
                    }}
                    onPress={() => { setHolidayYear(y); loadHolidays(y); }}
                  >
                    <Text style={{ color: holidayYear === y ? '#fff' : '#333', fontWeight: '600' }}>{y}</Text>
                  </TouchableOpacity>
                ))}
              </View>

              <Text style={[s.label, { marginTop: 4 }]}>Adicionar Feriado Regional</Text>
              <View style={{ flexDirection: 'row', gap: 8, marginBottom: 8 }}>
                <TouchableOpacity
                  style={[s.input, { flex: 1, justifyContent: 'center' }]}
                  onPress={() => setShowHolidayDatePicker(true)}
                  testID="holiday-date-picker-btn"
                >
                  <Text style={{ color: newHolidayDate ? '#000' : '#999' }}>{newHolidayDate || 'DD/MM/AAAA'}</Text>
                </TouchableOpacity>
                <TextInput
                  style={[s.input, { flex: 2 }]}
                  value={newHolidayDesc}
                  onChangeText={setNewHolidayDesc}
                  placeholder="Descrição (ex: Dia da Cidade)"
                />
              </View>
              {showHolidayDatePicker && (
                <DateTimePicker
                  value={ptToDate(newHolidayDate) || new Date(holidayYear, 0, 1)}
                  mode="date"
                  display={Platform.OS === 'ios' ? 'inline' : 'default'}
                  onChange={(_, selected) => {
                    if (Platform.OS !== 'ios') setShowHolidayDatePicker(false);
                    if (selected) setNewHolidayDate(dateToPt(selected));
                  }}
                />
              )}
              {Platform.OS === 'ios' && showHolidayDatePicker && (
                <TouchableOpacity onPress={() => setShowHolidayDatePicker(false)} style={{ alignSelf: 'flex-end', padding: 8 }}>
                  <Text style={{ color: '#000', fontWeight: '600' }}>OK</Text>
                </TouchableOpacity>
              )}
              <TouchableOpacity style={s.saveBtn} onPress={handleAddHoliday} testID="add-holiday-btn">
                <Text style={s.saveBtnText}>+ Adicionar</Text>
              </TouchableOpacity>
            </View>

            {!holidaysLoaded ? (
              <View style={s.empty}>
                <Ionicons name="hourglass-outline" size={64} color="#ccc" />
                <Text style={s.emptyText}>Carregando feriados...</Text>
              </View>
            ) : holidays.length === 0 ? (
              <View style={s.empty}>
                <Ionicons name="calendar-outline" size={64} color="#ccc" />
                <Text style={s.emptyText}>Nenhum feriado encontrado para {holidayYear}</Text>
              </View>
            ) : (
              <>
                {holidays.filter(h => h.type === 'regional').length > 0 && (
                  <Text style={[s.sectionTitle, { marginTop: 8 }]}>Feriados Regionais</Text>
                )}
                {holidays.filter(h => h.type === 'regional').map(h => (
                  <View key={h.id} style={[s.card, { padding: 12 }]} testID={`holiday-${h.id}`}>
                    <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
                      <View style={{ flex: 1 }}>
                        <Text style={{ fontSize: 15, fontWeight: '700', color: '#000' }}>{h.date}</Text>
                        <Text style={{ fontSize: 13, color: '#666' }}>{h.description || 'Feriado regional'}</Text>
                      </View>
                      <TouchableOpacity onPress={() => handleDeleteHoliday(h.id)} style={{ padding: 8 }}>
                        <Ionicons name="trash-outline" size={20} color="#d32f2f" />
                      </TouchableOpacity>
                    </View>
                  </View>
                ))}

                <Text style={[s.sectionTitle, { marginTop: 16 }]}>Feriados Nacionais (automáticos)</Text>
                {holidays.filter(h => h.type === 'national').map(h => (
                  <View key={h.id} style={[s.card, { padding: 12, backgroundColor: '#fafafa' }]}>
                    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                      <Ionicons name="flag" size={16} color="#888" style={{ marginRight: 8 }} />
                      <Text style={{ fontSize: 14, fontWeight: '600', color: '#333' }}>{h.date}</Text>
                      <Text style={{ fontSize: 13, color: '#666', marginLeft: 12 }}>{h.description}</Text>
                    </View>
                  </View>
                ))}
              </>
            )}
          </>
        )}
      </ScrollView>

      {/* CREATE BM MODAL */}
      <Modal visible={showCreate} animationType="slide" transparent>
        <View style={s.modalOverlay}>
          <View style={s.modalContent}>
            <ScrollView>
              <Text style={s.modalTitle}>{editingBMId ? 'Editar Boletim de Medição' : 'Novo Boletim de Medição'}</Text>

              <Text style={s.label}>Ordem de Serviço</Text>
              <View style={s.pickerWrap}>
                {serviceOrders.map(so => (
                  <TouchableOpacity key={so.id} style={[s.soOption, selectedOS === so.id && s.soOptionActive]} onPress={() => handleSelectOS(so.id)}>
                    <Text style={[s.soOptionText, selectedOS === so.id && { color: '#fff' }]}>{so.os_number} - {so.client}</Text>
                  </TouchableOpacity>
                ))}
              </View>

              {/* Timesheet selection */}
              {selectedOS && loadingTimesheets && (
                <ActivityIndicator style={{ marginTop: 12 }} color="#000000" />
              )}
              {selectedOS && !loadingTimesheets && availableTimesheets.length > 0 && (
                <>
                  <View style={s.tsHeaderRow}>
                    <Text style={s.sectionTitle}>Timesheets ({selectedTimesheets.length}/{availableTimesheets.length})</Text>
                    <TouchableOpacity onPress={toggleAllTimesheets} data-testid="toggle-all-timesheets">
                      <Text style={s.selectAllText}>
                        {selectedTimesheets.length === availableTimesheets.length ? 'Desmarcar Todos' : 'Selecionar Todos'}
                      </Text>
                    </TouchableOpacity>
                  </View>
                  {availableTimesheets.map((ts: any) => (
                    <TouchableOpacity
                      key={ts.id}
                      style={[s.tsItem, selectedTimesheets.includes(ts.id) && s.tsItemActive]}
                      onPress={() => toggleTimesheet(ts.id)}
                      data-testid={`ts-check-${ts.id}`}
                    >
                      <Ionicons
                        name={selectedTimesheets.includes(ts.id) ? 'checkbox' : 'square-outline'}
                        size={22}
                        color={selectedTimesheets.includes(ts.id) ? '#000000' : '#999'}
                      />
                      <View style={s.tsInfo}>
                        <Text style={s.tsDate}>{ts.date_range || 'Sem datas'}</Text>
                        <Text style={s.tsMeta}>{ts.entries_count} registro(s) | {ts.supervisor_name}</Text>
                        <Text style={s.tsEmployees} numberOfLines={1}>{ts.employees.join(', ')}</Text>
                      </View>
                    </TouchableOpacity>
                  ))}
                </>
              )}
              {selectedOS && !loadingTimesheets && availableTimesheets.length === 0 && (
                <Text style={{ color: '#999', marginTop: 12, textAlign: 'center' }}>Nenhuma timesheet encontrada para esta O.S.</Text>
              )}

              {/* Date pickers */}
              {selectedOS && availableTimesheets.length > 0 && (
                <View style={s.dateRow}>
                  <View style={s.dateField}>
                    <Text style={s.label}>Data Início</Text>
                    {Platform.OS === 'web' ? (
                      <input
                        type="date"
                        value={dataInicio ? dataInicio.split('/').reverse().join('-') : ''}
                        onChange={(e: any) => {
                          const val = e.target.value;
                          if (val) {
                            const [y, m, d] = val.split('-');
                            setDataInicio(`${d}/${m}/${y}`);
                          } else {
                            setDataInicio('');
                          }
                        }}
                        style={{ border: '1px solid #ddd', borderRadius: 8, padding: '10px 12px', fontSize: 14, width: '100%', boxSizing: 'border-box' } as any}
                        data-testid="date-inicio-picker"
                      />
                    ) : (
                      <TouchableOpacity
                        style={[s.input, { justifyContent: 'center' }]}
                        onPress={() => setShowDatePicker('inicio')}
                        data-testid="date-inicio-picker-mobile"
                      >
                        <Text style={{ fontSize: 14, color: dataInicio ? '#212121' : '#999' }}>
                          {dataInicio || 'Selecionar data'}
                        </Text>
                      </TouchableOpacity>
                    )}
                  </View>
                  <View style={s.dateField}>
                    <Text style={s.label}>Data Fim</Text>
                    {Platform.OS === 'web' ? (
                      <input
                        type="date"
                        value={dataFim ? dataFim.split('/').reverse().join('-') : ''}
                        onChange={(e: any) => {
                          const val = e.target.value;
                          if (val) {
                            const [y, m, d] = val.split('-');
                            setDataFim(`${d}/${m}/${y}`);
                          } else {
                            setDataFim('');
                          }
                        }}
                        style={{ border: '1px solid #ddd', borderRadius: 8, padding: '10px 12px', fontSize: 14, width: '100%', boxSizing: 'border-box' } as any}
                        data-testid="date-fim-picker"
                      />
                    ) : (
                      <TouchableOpacity
                        style={[s.input, { justifyContent: 'center' }]}
                        onPress={() => setShowDatePicker('fim')}
                        data-testid="date-fim-picker-mobile"
                      >
                        <Text style={{ fontSize: 14, color: dataFim ? '#212121' : '#999' }}>
                          {dataFim || 'Selecionar data'}
                        </Text>
                      </TouchableOpacity>
                    )}
                  </View>
                </View>
              )}

              {/* Native date picker (iOS in modal, Android inline auto-popup) */}
              {showDatePicker && Platform.OS === 'android' && (
                <DateTimePicker
                  value={
                    (showDatePicker === 'inicio' ? ptToDate(dataInicio) : ptToDate(dataFim)) || new Date()
                  }
                  mode="date"
                  display="default"
                  onChange={(event: any, selectedDate?: Date) => {
                    setShowDatePicker(null);
                    if (event?.type === 'dismissed') return;
                    if (selectedDate) {
                      const formatted = dateToPt(selectedDate);
                      if (showDatePicker === 'inicio') setDataInicio(formatted);
                      else setDataFim(formatted);
                    }
                  }}
                />
              )}
              {showDatePicker && Platform.OS === 'ios' && (
                <Modal
                  visible
                  transparent
                  animationType="fade"
                  onRequestClose={() => setShowDatePicker(null)}
                >
                  <TouchableOpacity
                    activeOpacity={1}
                    style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.5)' }}
                    onPress={() => setShowDatePicker(null)}
                  >
                    <TouchableOpacity activeOpacity={1} style={{ width: '92%', maxWidth: 380, backgroundColor: '#fff', borderRadius: 14, overflow: 'hidden' }}>
                      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 14, borderBottomWidth: 1, borderBottomColor: '#eee' }}>
                        <TouchableOpacity onPress={() => setShowDatePicker(null)}>
                          <Text style={{ fontSize: 16, color: '#888' }}>Cancelar</Text>
                        </TouchableOpacity>
                        <Text style={{ fontSize: 16, fontWeight: '700', color: '#000' }}>
                          {showDatePicker === 'inicio' ? 'Data Início' : 'Data Fim'}
                        </Text>
                        <TouchableOpacity onPress={() => setShowDatePicker(null)}>
                          <Text style={{ fontSize: 16, color: '#000', fontWeight: '700' }}>OK</Text>
                        </TouchableOpacity>
                      </View>
                      <View style={{ height: 380, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 8 }}>
                        <DateTimePicker
                          value={
                            (showDatePicker === 'inicio' ? ptToDate(dataInicio) : ptToDate(dataFim)) || new Date()
                          }
                          mode="date"
                          display="inline"
                          themeVariant="light"
                          locale="pt-BR"
                          maximumDate={new Date(2030, 11, 31)}
                          minimumDate={new Date(2020, 0, 1)}
                          style={{ width: '100%', height: 360 }}
                          onChange={(_event: any, selectedDate?: Date) => {
                            if (selectedDate) {
                              const formatted = dateToPt(selectedDate);
                              if (showDatePicker === 'inicio') setDataInicio(formatted);
                              else setDataFim(formatted);
                            }
                          }}
                        />
                      </View>
                    </TouchableOpacity>
                  </TouchableOpacity>
                </Modal>
              )}

              <Text style={s.sectionTitle}>Modo de Cálculo</Text>
              <View style={{ flexDirection: 'row', gap: 8, marginBottom: 10 }}>
                {([
                  { key: 'onshore', label: 'Onshore (8h)' },
                  { key: 'offshore', label: 'Offshore (12h)' },
                ] as const).map(opt => (
                  <TouchableOpacity
                    key={opt.key}
                    testID={`bm-calc-mode-${opt.key}`}
                    style={{
                      flex: 1,
                      paddingVertical: 12,
                      borderRadius: 8,
                      backgroundColor: calcMode === opt.key ? '#000000' : '#f5f5f5',
                      alignItems: 'center',
                      borderWidth: 1,
                      borderColor: calcMode === opt.key ? '#000000' : '#e0e0e0',
                    }}
                    onPress={() => setCalcMode(opt.key)}
                  >
                    <Text style={{ fontSize: 15, fontWeight: '700', color: calcMode === opt.key ? '#fff' : '#333' }}>
                      {opt.label}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>

              <Text style={s.sectionTitle}>Tabela de Preço</Text>
              <Text style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>
                Por padrão usa a tabela do cliente da OS. Toque para escolher outra.
              </Text>
              <TouchableOpacity
                testID="bm-price-table-open"
                style={{
                  flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
                  paddingVertical: 14, paddingHorizontal: 14, borderRadius: 8,
                  backgroundColor: '#fff', borderWidth: 1, borderColor: '#e0e0e0', marginBottom: 12,
                }}
                onPress={() => { setPriceTableSearch(''); setShowPriceTableModal(true); }}
              >
                <View style={{ flex: 1 }}>
                  <Text style={{ fontSize: 12, color: '#666' }}>
                    {selectedPriceTableId ? 'Tabela escolhida' : 'Tabela'}
                  </Text>
                  <Text style={{ fontSize: 16, fontWeight: '600', color: '#000', marginTop: 2 }}>
                    {(() => {
                      if (!selectedPriceTableId) return 'Auto (cliente da OS)';
                      const pt: any = prices.find((p: any) => p.id === selectedPriceTableId);
                      if (!pt) return 'Auto (cliente da OS)';
                      return `${pt.client_name}${pt.label ? ` — ${pt.label}` : ''}`;
                    })()}
                  </Text>
                </View>
                <Ionicons name="chevron-down" size={20} color="#666" />
              </TouchableOpacity>

              <TouchableOpacity style={s.calcBtn} onPress={handleCalculate} disabled={calcLoading}>
                {calcLoading ? <ActivityIndicator color="#fff" /> : <><Ionicons name="calculator" size={18} color="#fff" /><Text style={s.calcBtnText}>Calcular</Text></>}
              </TouchableOpacity>

              {calcResult && (
                <>
                  <Text style={s.sectionTitle}>Itens Calculados ({calcResult.items.length})</Text>
                  {calcResult.items.map((item: any, i: number) => (
                    <View key={i} style={s.calcItem}>
                      <Text style={s.calcFunc}>{item.function_name}</Text>
                      <Text style={s.calcDetail}>{item.qtd} {item.unit_label || 'dia'}(s) x {formatCurrency(item.valor_und)} = {formatCurrency(item.valor_total)}</Text>
                      <View style={{ flexDirection: 'row', gap: 8, marginTop: 6 }}>
                        <View style={{ flex: 1 }}>
                          <Text style={[s.label, { marginTop: 0, fontSize: 12 }]}>Cod.</Text>
                          <TextInput style={[s.input, { paddingVertical: 8, fontSize: 13 }]} value={item.cod || ''} onChangeText={v => {
                            const items = [...calcResult.items];
                            items[i] = { ...items[i], cod: v };
                            setCalcResult({ ...calcResult, items });
                          }} placeholder="Cod." />
                        </View>
                        <View style={{ flex: 1 }}>
                          <Text style={[s.label, { marginTop: 0, fontSize: 12 }]}>Linha</Text>
                          <TextInput style={[s.input, { paddingVertical: 8, fontSize: 13 }]} value={item.linha || ''} onChangeText={v => {
                            const items = [...calcResult.items];
                            items[i] = { ...items[i], linha: v };
                            setCalcResult({ ...calcResult, items });
                          }} placeholder="Linha" />
                        </View>
                      </View>
                    </View>
                  ))}
                  <Text style={s.calcSubtotal}>Subtotal: {formatCurrency(calcResult.subtotal)}</Text>

                  <Text style={s.label}>Data do Boletim</Text>
                  <TextInput style={s.input} value={bmForm.data} onChangeText={v => setBmForm({...bmForm, data: v})} placeholder="DD/MM/AAAA" />

                  <Text style={s.label}>Revisao</Text>
                  <TextInput style={s.input} value={bmForm.rev} onChangeText={v => setBmForm({...bmForm, rev: v})} />

                  <Text style={s.label}>P.O.</Text>
                  <TextInput style={s.input} value={bmForm.po_number} onChangeText={v => setBmForm({...bmForm, po_number: v})} />

                  <Text style={s.label}>Proposta</Text>
                  <TextInput style={s.input} value={bmForm.proposta} onChangeText={v => setBmForm({...bmForm, proposta: v})} />

                  {/* Impostos toggle */}
                  <View style={s.impostoToggleRow}>
                    <Text style={s.label}>Incluir Impostos?</Text>
                    <TouchableOpacity
                      style={[s.impostoToggle, bmForm.incluirImpostos && s.impostoToggleActive]}
                      onPress={() => setBmForm({...bmForm, incluirImpostos: !bmForm.incluirImpostos})}
                      data-testid="toggle-impostos"
                    >
                      <Text style={[s.impostoToggleText, bmForm.incluirImpostos && { color: '#fff' }]}>
                        {bmForm.incluirImpostos ? 'Sim' : 'Não'}
                      </Text>
                    </TouchableOpacity>
                  </View>

                  {bmForm.incluirImpostos && (
                    <>
                      <Text style={s.label}>Porcentagem de Impostos (%)</Text>
                      <TextInput
                        style={s.input}
                        value={bmForm.impostoPct}
                        onChangeText={v => setBmForm({...bmForm, impostoPct: v})}
                        keyboardType="numeric"
                        placeholder="Ex: 15"
                      />
                      <Text style={s.impostoCalcText}>
                        Impostos: {formatCurrency(calcResult.subtotal * (parseFloat(bmForm.impostoPct) || 0) / 100)}
                      </Text>
                      <Text style={s.calcSubtotal}>
                        Valor Total: {formatCurrency(calcResult.subtotal + calcResult.subtotal * (parseFloat(bmForm.impostoPct) || 0) / 100)}
                      </Text>
                    </>
                  )}

                  <TouchableOpacity style={s.saveBtn} onPress={handleCreateBM}>
                    <Text style={s.saveBtnText}>{editingBMId ? 'Atualizar Boletim' : 'Salvar Boletim'}</Text>
                  </TouchableOpacity>
                </>
              )}

              <TouchableOpacity style={s.cancelBtn} onPress={() => { setShowCreate(false); setCalcResult(null); setEditingBMId(null); setAvailableTimesheets([]); setSelectedTimesheets([]); setDataInicio(''); setDataFim(''); setSelectedPriceTableId(''); }}>
                <Text style={s.cancelBtnText}>Cancelar</Text>
              </TouchableOpacity>
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* PRICE TABLE PICKER MODAL (BM context) */}
      <Modal visible={showPriceTableModal} animationType="slide" transparent>
        <View style={s.modalOverlay}>
          <View style={[s.modalContent, { maxHeight: '85%' }]}>
            <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <Text style={s.modalTitle}>Escolher Tabela de Preço</Text>
              <TouchableOpacity onPress={() => setShowPriceTableModal(false)} testID="price-table-modal-close">
                <Ionicons name="close" size={26} color="#000" />
              </TouchableOpacity>
            </View>

            <TextInput
              style={s.input}
              value={priceTableSearch}
              onChangeText={setPriceTableSearch}
              placeholder="Buscar por cliente ou identificação..."
              testID="price-table-search"
            />

            <ScrollView style={{ marginTop: 8 }}>
              {/* Auto option */}
              <TouchableOpacity
                testID="price-table-option-auto"
                style={{
                  paddingVertical: 14, paddingHorizontal: 14, borderRadius: 8, marginBottom: 8,
                  backgroundColor: !selectedPriceTableId ? '#000' : '#f5f5f5',
                  borderWidth: 1, borderColor: !selectedPriceTableId ? '#000' : '#e0e0e0',
                }}
                onPress={() => { setSelectedPriceTableId(''); setShowPriceTableModal(false); }}
              >
                <Text style={{ fontSize: 15, fontWeight: '700', color: !selectedPriceTableId ? '#fff' : '#000' }}>
                  Auto (cliente da OS)
                </Text>
                <Text style={{ fontSize: 12, color: !selectedPriceTableId ? '#ddd' : '#666', marginTop: 2 }}>
                  Detecta automaticamente pelo nome do cliente da OS selecionada
                </Text>
              </TouchableOpacity>

              {/* Filtered tables */}
              {prices
                .filter((pt: any) => {
                  const q = priceTableSearch.trim().toLowerCase();
                  if (!q) return true;
                  const txt = `${pt.client_name || ''} ${pt.label || ''}`.toLowerCase();
                  return txt.includes(q);
                })
                .map((pt: any) => (
                  <TouchableOpacity
                    key={pt.id}
                    testID={`price-table-option-${pt.id}`}
                    style={{
                      paddingVertical: 14, paddingHorizontal: 14, borderRadius: 8, marginBottom: 8,
                      backgroundColor: selectedPriceTableId === pt.id ? '#000' : '#f5f5f5',
                      borderWidth: 1, borderColor: selectedPriceTableId === pt.id ? '#000' : '#e0e0e0',
                    }}
                    onPress={() => { setSelectedPriceTableId(pt.id); setShowPriceTableModal(false); }}
                  >
                    <Text style={{ fontSize: 15, fontWeight: '700', color: selectedPriceTableId === pt.id ? '#fff' : '#000' }}>
                      {pt.client_name}{pt.label ? ` — ${pt.label}` : ''}
                    </Text>
                    <Text style={{ fontSize: 12, color: selectedPriceTableId === pt.id ? '#ddd' : '#666', marginTop: 2 }}>
                      {(pt.prices || []).length} função(ões) cadastrada(s)
                    </Text>
                  </TouchableOpacity>
                ))}

              {prices.filter((pt: any) => {
                const q = priceTableSearch.trim().toLowerCase();
                if (!q) return true;
                return `${pt.client_name || ''} ${pt.label || ''}`.toLowerCase().includes(q);
              }).length === 0 && (
                <Text style={{ textAlign: 'center', color: '#999', marginTop: 16 }}>
                  Nenhuma tabela encontrada
                </Text>
              )}
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* PRICE TABLE FORM MODAL */}
      <Modal visible={showPriceForm} animationType="slide" transparent>
        <View style={s.modalOverlay}>
          <View style={s.modalContent}>
            <ScrollView>
              <Text style={s.modalTitle}>{editingPriceId ? 'Editar' : 'Nova'} Tabela de Preços</Text>

              <Text style={s.label}>Nome do Cliente</Text>
              <TextInput style={s.input} value={priceForm.client_name} onChangeText={v => setPriceForm({...priceForm, client_name: v})} placeholder="Nome exato do cliente" />
              <Text style={s.label}>Identificação da Tabela (opcional)</Text>
              <TextInput style={s.input} value={priceForm.label} onChangeText={v => setPriceForm({...priceForm, label: v})} placeholder="Ex: Padrão, Promocional 2026, Contrato A" />

              {priceForm.prices.map((p: any, i: number) => (
                <View key={i} style={s.priceFormRow}>
                  <Text style={s.priceFormLabel}>{p.function_name}</Text>
                  <View style={s.priceFormInputs}>
                    <View style={s.priceFormField}>
                      <Text style={s.priceFormSublabel}>Valor Diurno (R$)</Text>
                      <TextInput
                        style={s.priceFormInput}
                        value={String(p.day_rate ?? '')}
                        onChangeText={v => updatePriceRow(i, 'day_rate', v)}
                        keyboardType="decimal-pad"
                        placeholder="Ex: 2.850,72"
                      />
                    </View>
                    <View style={s.priceFormField}>
                      <Text style={s.priceFormSublabel}>Desconto Diurno (%)</Text>
                      <TextInput
                        style={s.priceFormInput}
                        value={String(p.day_discount_pct ?? '')}
                        onChangeText={v => updatePriceRow(i, 'day_discount_pct', v)}
                        keyboardType="decimal-pad"
                        placeholder="0"
                      />
                    </View>
                    <View style={s.priceFormField}>
                      <Text style={s.priceFormSublabel}>Noturno (+20%)</Text>
                      <Text style={[s.priceFormInput, { paddingVertical: 11, color: '#666', backgroundColor: '#f5f5f5' }]}>{formatCurrency(parseBR(p.day_rate) * 1.2)}</Text>
                    </View>
                  </View>
                  {parseBR(p.day_discount_pct) > 0 && parseBR(p.day_rate) > 0 && (
                    <Text style={{ fontSize: 12, color: '#0a7c2f', marginTop: 4, fontStyle: 'italic' }}>
                      Diurno c/ desconto: {formatCurrency(parseBR(p.day_rate) * (1 - parseBR(p.day_discount_pct) / 100))}
                    </Text>
                  )}
                </View>
              ))}

              <TouchableOpacity style={s.saveBtn} onPress={handleSavePrice}>
                <Text style={s.saveBtnText}>Salvar Tabela</Text>
              </TouchableOpacity>
              <TouchableOpacity style={s.cancelBtn} onPress={() => setShowPriceForm(false)}>
                <Text style={s.cancelBtnText}>Cancelar</Text>
              </TouchableOpacity>
            </ScrollView>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 12, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#e0e0e0' },
  backBtn: { padding: 8 },
  title: { fontSize: 20, fontWeight: '600', color: '#000000' },
  tabs: { flexDirection: 'row', backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#e0e0e0' },
  tab: { flex: 1, paddingVertical: 12, alignItems: 'center' },
  tabActive: { borderBottomWidth: 2, borderBottomColor: '#000000' },
  tabText: { fontSize: 14, color: '#999' },
  tabTextActive: { color: '#000000', fontWeight: '600' },
  scrollContent: { padding: 16 },
  addBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#000000', paddingVertical: 12, borderRadius: 10, marginBottom: 16, gap: 8 },
  addBtnText: { color: '#fff', fontSize: 15, fontWeight: '600' },
  empty: { alignItems: 'center', paddingVertical: 64 },
  emptyText: { fontSize: 16, color: '#999', marginTop: 16 },
  card: { backgroundColor: '#fff', borderRadius: 12, marginBottom: 12, padding: 16, elevation: 2, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.1, shadowRadius: 2 },
  cardHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
  osBadge: { backgroundColor: '#000000', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 6, marginRight: 10 },
  osBadgeText: { color: '#fff', fontWeight: '700', fontSize: 12 },
  cardInfo: { flex: 1 },
  cardClient: { fontSize: 16, fontWeight: '600', color: '#212121' },
  cardMeta: { fontSize: 12, color: '#666', marginTop: 2 },
  cardTotal: { fontSize: 16, fontWeight: '700', color: '#000000' },
  cardActions: { flexDirection: 'row', gap: 8, marginTop: 8, paddingTop: 8, borderTopWidth: 1, borderTopColor: '#f0f0f0' },
  actionBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingVertical: 6, paddingHorizontal: 12, borderRadius: 6, borderWidth: 1, borderColor: '#000000' },
  actionText: { fontSize: 13, color: '#000000' },
  priceRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 4, paddingHorizontal: 8 },
  priceFunc: { fontSize: 13, fontWeight: '500', color: '#333', flex: 1 },
  priceVal: { fontSize: 12, color: '#666', marginLeft: 8 },
  // Modal styles
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center' },
  modalContent: { backgroundColor: '#fff', borderRadius: 16, padding: 20, width: '90%', maxWidth: 600, maxHeight: '90%' },
  modalTitle: { fontSize: 20, fontWeight: '600', color: '#000000', marginBottom: 16, textAlign: 'center' },
  label: { fontSize: 13, fontWeight: '600', color: '#333', marginTop: 12, marginBottom: 4 },
  input: { borderWidth: 1, borderColor: '#ddd', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10, fontSize: 14, color: '#333' },
  pickerWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  soOption: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8, borderWidth: 1, borderColor: '#ddd', backgroundColor: '#f5f5f5' },
  soOptionActive: { backgroundColor: '#000000', borderColor: '#000000' },
  soOptionText: { fontSize: 13, color: '#333' },
  calcBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#ff6f00', paddingVertical: 10, borderRadius: 8, marginTop: 12, gap: 8 },
  calcBtnText: { color: '#fff', fontSize: 14, fontWeight: '600' },
  // Timesheet selection styles
  tsHeaderRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 16, marginBottom: 8 },
  selectAllText: { fontSize: 13, color: '#000000', fontWeight: '600' },
  tsItem: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#f9f9f9', padding: 12, borderRadius: 8, marginBottom: 6, borderWidth: 1, borderColor: '#eee', gap: 10 },
  tsItemActive: { backgroundColor: '#f0f0f0', borderColor: '#000000' },
  tsInfo: { flex: 1 },
  tsDate: { fontSize: 13, fontWeight: '600', color: '#333' },
  tsMeta: { fontSize: 11, color: '#666', marginTop: 2 },
  tsEmployees: { fontSize: 11, color: '#999', marginTop: 1 },
  // Date picker styles
  dateRow: { flexDirection: 'row', gap: 12, marginTop: 12 },
  dateField: { flex: 1 },
  sectionTitle: { fontSize: 15, fontWeight: '600', color: '#000000', marginTop: 16, marginBottom: 8 },
  calcItem: { backgroundColor: '#f5f5f5', padding: 10, borderRadius: 8, marginBottom: 6 },
  calcFunc: { fontSize: 13, fontWeight: '600', color: '#333' },
  calcDetail: { fontSize: 12, color: '#666', marginTop: 2 },
  calcSubtotal: { fontSize: 15, fontWeight: '700', color: '#000000', marginTop: 8, textAlign: 'right' },
  // Imposto toggle styles
  impostoToggleRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 12 },
  impostoToggle: { paddingHorizontal: 16, paddingVertical: 8, borderRadius: 20, borderWidth: 1, borderColor: '#ddd', backgroundColor: '#f5f5f5' },
  impostoToggleActive: { backgroundColor: '#000000', borderColor: '#000000' },
  impostoToggleText: { fontSize: 13, fontWeight: '600', color: '#666' },
  impostoCalcText: { fontSize: 13, color: '#666', marginTop: 6, textAlign: 'right' },
  saveBtn: { backgroundColor: '#000000', paddingVertical: 14, borderRadius: 10, alignItems: 'center', marginTop: 16 },
  saveBtnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  cancelBtn: { paddingVertical: 12, alignItems: 'center', marginTop: 8 },
  cancelBtnText: { color: '#999', fontSize: 14 },
  priceFormRow: { marginTop: 12, paddingTop: 8, borderTopWidth: 1, borderTopColor: '#f0f0f0' },
  priceFormLabel: { fontSize: 14, fontWeight: '600', color: '#333', marginBottom: 6 },
  priceFormInputs: { flexDirection: 'row', gap: 12 },
  priceFormField: { flex: 1 },
  priceFormSublabel: { fontSize: 11, color: '#666', marginBottom: 2 },
  priceFormInput: { borderWidth: 1, borderColor: '#ddd', borderRadius: 6, paddingHorizontal: 10, paddingVertical: 8, fontSize: 14 },
});
