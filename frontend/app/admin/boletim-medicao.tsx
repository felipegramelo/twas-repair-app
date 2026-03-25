import React, { useState, useEffect } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, ScrollView, TextInput,
  ActivityIndicator, Platform, Alert, Modal,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { bmAPI, clientPriceAPI } from '../../services/api';
import AsyncStorage from '@react-native-async-storage/async-storage';
import api from '../../services/api';

const showMsg = (msg: string) => {
  if (Platform.OS === 'web') window.alert(msg);
  else Alert.alert('Info', msg);
};

export default function BMScreen() {
  const router = useRouter();
  const [tab, setTab] = useState<'bm' | 'prices'>('bm');
  const [bms, setBms] = useState<any[]>([]);
  const [prices, setPrices] = useState<any[]>([]);
  const [serviceOrders, setServiceOrders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Create BM state
  const [showCreate, setShowCreate] = useState(false);
  const [selectedOS, setSelectedOS] = useState('');
  const [calcResult, setCalcResult] = useState<any>(null);
  const [calcLoading, setCalcLoading] = useState(false);
  const [bmForm, setBmForm] = useState({ periodo: '', data: '', rev: '0', po_number: '', proposta: '', cod: '', impostos: '0' });

  // Price table state
  const [showPriceForm, setShowPriceForm] = useState(false);
  const [priceForm, setPriceForm] = useState({ client_name: '', prices: [] as any[] });
  const [editingPriceId, setEditingPriceId] = useState<string | null>(null);

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

  const handleCalculate = async () => {
    if (!selectedOS) return showMsg('Selecione uma O.S.');
    setCalcLoading(true);
    try {
      const result = await bmAPI.calculate(selectedOS);
      setCalcResult(result);
      if (!result.has_price_table) showMsg('Atenção: Não há tabela de preços cadastrada para o cliente ' + result.client + '. Os valores estarão zerados.');
    } catch { showMsg('Erro ao calcular BM'); }
    finally { setCalcLoading(false); }
  };

  const handleCreateBM = async () => {
    if (!calcResult || !bmForm.periodo) return showMsg('Preencha o período');
    const items = calcResult.items;
    const subtotal = items.reduce((s: number, i: any) => s + i.valor_total, 0);
    const impostos = parseFloat(bmForm.impostos) || 0;
    try {
      await bmAPI.create({
        os_id: selectedOS,
        periodo: bmForm.periodo,
        data: bmForm.data || new Date().toLocaleDateString('pt-BR'),
        rev: bmForm.rev,
        po_number: bmForm.po_number,
        proposta: bmForm.proposta,
        cod: bmForm.cod,
        items,
        subtotal: Math.round(subtotal * 100) / 100,
        impostos,
        valor_total: Math.round((subtotal + impostos) * 100) / 100,
      });
      showMsg('Boletim de Medição criado com sucesso!');
      setShowCreate(false);
      setCalcResult(null);
      setSelectedOS('');
      setBmForm({ periodo: '', data: '', rev: '0', po_number: '', proposta: '', cod: '', impostos: '0' });
      loadData();
    } catch { showMsg('Erro ao criar BM'); }
  };

  const handleDeleteBM = async (id: string) => {
    if (Platform.OS === 'web' && !window.confirm('Excluir este BM?')) return;
    try { await bmAPI.delete(id); loadData(); } catch { showMsg('Erro ao excluir'); }
  };

  const handleOpenPDF = async (id: string) => {
    const token = await AsyncStorage.getItem('token');
    const baseURL = process.env.EXPO_PUBLIC_BACKEND_URL + '/api';
    const url = `${baseURL}/bm/${id}/pdf?token=${token}&t=${Date.now()}`;
    if (Platform.OS === 'web') window.open(url, '_blank');
  };

  // Price table functions
  const FUNCTION_OPTIONS = [
    { code: 'Sup', name: 'SUPERVISOR' }, { code: 'T', name: 'TÉCNICO' },
    { code: 'M', name: 'MECÂNICO' }, { code: 'E', name: 'ELETRICISTA' },
    { code: 'TS', name: 'TÉCNICO DE SEGURANÇA' },
  ];

  const openPriceForm = (existing?: any) => {
    if (existing) {
      setEditingPriceId(existing.id);
      setPriceForm({ client_name: existing.client_name, prices: existing.prices || [] });
    } else {
      setEditingPriceId(null);
      setPriceForm({ client_name: '', prices: FUNCTION_OPTIONS.map(f => ({ function_code: f.code, function_name: f.name, day_rate: 0 })) });
    }
    setShowPriceForm(true);
  };

  const handleSavePrice = async () => {
    if (!priceForm.client_name) return showMsg('Informe o nome do cliente');
    try {
      if (editingPriceId) {
        await clientPriceAPI.update(editingPriceId, priceForm);
      } else {
        await clientPriceAPI.create(priceForm);
      }
      showMsg('Tabela de preços salva!');
      setShowPriceForm(false);
      loadData();
    } catch { showMsg('Erro ao salvar tabela'); }
  };

  const handleDeletePrice = async (id: string) => {
    if (Platform.OS === 'web' && !window.confirm('Excluir esta tabela de preços?')) return;
    try { await clientPriceAPI.delete(id); loadData(); } catch { showMsg('Erro ao excluir'); }
  };

  const updatePriceRow = (idx: number, field: string, value: string) => {
    const updated = [...priceForm.prices];
    updated[idx] = { ...updated[idx], [field]: parseFloat(value) || 0 };
    setPriceForm({ ...priceForm, prices: updated });
  };

  const formatCurrency = (v: number) => {
    return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  if (loading) return <View style={s.center}><ActivityIndicator size="large" color="#1a237e" /></View>;

  return (
    <SafeAreaView style={s.container}>
      <View style={s.header}>
        <TouchableOpacity onPress={() => router.replace('/admin')} style={s.backBtn} data-testid="bm-back-btn">
          <Ionicons name="arrow-back" size={24} color="#1a237e" />
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
      </View>

      <ScrollView contentContainerStyle={s.scrollContent}>
        {tab === 'bm' && (
          <>
            <TouchableOpacity style={s.addBtn} onPress={() => setShowCreate(true)} data-testid="create-bm-btn">
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
                    <Ionicons name="eye-outline" size={18} color="#1a237e" /><Text style={s.actionText}>Ver PDF</Text>
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
                  <Text style={s.cardClient}>{pt.client_name}</Text>
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
                    <Ionicons name="create-outline" size={18} color="#1a237e" /><Text style={s.actionText}>Editar</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={[s.actionBtn, { borderColor: '#d32f2f' }]} onPress={() => handleDeletePrice(pt.id)}>
                    <Ionicons name="trash-outline" size={18} color="#d32f2f" /><Text style={[s.actionText, { color: '#d32f2f' }]}>Excluir</Text>
                  </TouchableOpacity>
                </View>
              </View>
            ))}
          </>
        )}
      </ScrollView>

      {/* CREATE BM MODAL */}
      <Modal visible={showCreate} animationType="slide" transparent>
        <View style={s.modalOverlay}>
          <View style={s.modalContent}>
            <ScrollView>
              <Text style={s.modalTitle}>Novo Boletim de Medição</Text>

              <Text style={s.label}>Ordem de Serviço</Text>
              <View style={s.pickerWrap}>
                {serviceOrders.map(so => (
                  <TouchableOpacity key={so.id} style={[s.soOption, selectedOS === so.id && s.soOptionActive]} onPress={() => setSelectedOS(so.id)}>
                    <Text style={[s.soOptionText, selectedOS === so.id && { color: '#fff' }]}>{so.os_number} - {so.client}</Text>
                  </TouchableOpacity>
                ))}
              </View>

              <TouchableOpacity style={s.calcBtn} onPress={handleCalculate} disabled={calcLoading}>
                {calcLoading ? <ActivityIndicator color="#fff" /> : <><Ionicons name="calculator" size={18} color="#fff" /><Text style={s.calcBtnText}>Calcular</Text></>}
              </TouchableOpacity>

              {calcResult && (
                <>
                  <Text style={s.sectionTitle}>Itens Calculados ({calcResult.items.length})</Text>
                  {calcResult.items.map((item: any, i: number) => (
                    <View key={i} style={s.calcItem}>
                      <Text style={s.calcFunc}>{item.function_name}</Text>
                      <Text style={s.calcDetail}>{item.qtd} diária(s) x {formatCurrency(item.valor_und)} = {formatCurrency(item.valor_total)}</Text>
                    </View>
                  ))}
                  <Text style={s.calcSubtotal}>Subtotal: {formatCurrency(calcResult.subtotal)}</Text>

                  <Text style={s.label}>Período *</Text>
                  <TextInput style={s.input} value={bmForm.periodo} onChangeText={v => setBmForm({...bmForm, periodo: v})} placeholder="Ex: Janeiro / 2026" />

                  <Text style={s.label}>Data</Text>
                  <TextInput style={s.input} value={bmForm.data} onChangeText={v => setBmForm({...bmForm, data: v})} placeholder="DD/MM/AAAA" />

                  <Text style={s.label}>Revisão</Text>
                  <TextInput style={s.input} value={bmForm.rev} onChangeText={v => setBmForm({...bmForm, rev: v})} />

                  <Text style={s.label}>P.O.</Text>
                  <TextInput style={s.input} value={bmForm.po_number} onChangeText={v => setBmForm({...bmForm, po_number: v})} />

                  <Text style={s.label}>Proposta</Text>
                  <TextInput style={s.input} value={bmForm.proposta} onChangeText={v => setBmForm({...bmForm, proposta: v})} />

                  <Text style={s.label}>CÓD.</Text>
                  <TextInput style={s.input} value={bmForm.cod} onChangeText={v => setBmForm({...bmForm, cod: v})} />

                  <Text style={s.label}>Impostos (R$)</Text>
                  <TextInput style={s.input} value={bmForm.impostos} onChangeText={v => setBmForm({...bmForm, impostos: v})} keyboardType="numeric" />

                  <TouchableOpacity style={s.saveBtn} onPress={handleCreateBM}>
                    <Text style={s.saveBtnText}>Salvar Boletim</Text>
                  </TouchableOpacity>
                </>
              )}

              <TouchableOpacity style={s.cancelBtn} onPress={() => { setShowCreate(false); setCalcResult(null); }}>
                <Text style={s.cancelBtnText}>Cancelar</Text>
              </TouchableOpacity>
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* PRICE TABLE MODAL */}
      <Modal visible={showPriceForm} animationType="slide" transparent>
        <View style={s.modalOverlay}>
          <View style={s.modalContent}>
            <ScrollView>
              <Text style={s.modalTitle}>{editingPriceId ? 'Editar' : 'Nova'} Tabela de Preços</Text>

              <Text style={s.label}>Nome do Cliente</Text>
              <TextInput style={s.input} value={priceForm.client_name} onChangeText={v => setPriceForm({...priceForm, client_name: v})} placeholder="Nome exato do cliente" />

              {priceForm.prices.map((p: any, i: number) => (
                <View key={i} style={s.priceFormRow}>
                  <Text style={s.priceFormLabel}>{p.function_name}</Text>
                  <View style={s.priceFormInputs}>
                    <View style={s.priceFormField}>
                      <Text style={s.priceFormSublabel}>Valor Diurno (R$)</Text>
                      <TextInput style={s.priceFormInput} value={String(p.day_rate || '')} onChangeText={v => updatePriceRow(i, 'day_rate', v)} keyboardType="numeric" />
                    </View>
                    <View style={s.priceFormField}>
                      <Text style={s.priceFormSublabel}>Noturno (+20%)</Text>
                      <Text style={[s.priceFormInput, { paddingVertical: 11, color: '#666', backgroundColor: '#f5f5f5' }]}>{formatCurrency((p.day_rate || 0) * 1.2)}</Text>
                    </View>
                  </View>
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
  title: { fontSize: 20, fontWeight: '600', color: '#1a237e' },
  tabs: { flexDirection: 'row', backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#e0e0e0' },
  tab: { flex: 1, paddingVertical: 12, alignItems: 'center' },
  tabActive: { borderBottomWidth: 2, borderBottomColor: '#1a237e' },
  tabText: { fontSize: 14, color: '#999' },
  tabTextActive: { color: '#1a237e', fontWeight: '600' },
  scrollContent: { padding: 16 },
  addBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#1a237e', paddingVertical: 12, borderRadius: 10, marginBottom: 16, gap: 8 },
  addBtnText: { color: '#fff', fontSize: 15, fontWeight: '600' },
  empty: { alignItems: 'center', paddingVertical: 64 },
  emptyText: { fontSize: 16, color: '#999', marginTop: 16 },
  card: { backgroundColor: '#fff', borderRadius: 12, marginBottom: 12, padding: 16, elevation: 2, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.1, shadowRadius: 2 },
  cardHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
  osBadge: { backgroundColor: '#1a237e', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 6, marginRight: 10 },
  osBadgeText: { color: '#fff', fontWeight: '700', fontSize: 12 },
  cardInfo: { flex: 1 },
  cardClient: { fontSize: 16, fontWeight: '600', color: '#212121' },
  cardMeta: { fontSize: 12, color: '#666', marginTop: 2 },
  cardTotal: { fontSize: 16, fontWeight: '700', color: '#1a237e' },
  cardActions: { flexDirection: 'row', gap: 8, marginTop: 8, paddingTop: 8, borderTopWidth: 1, borderTopColor: '#f0f0f0' },
  actionBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingVertical: 6, paddingHorizontal: 12, borderRadius: 6, borderWidth: 1, borderColor: '#1a237e' },
  actionText: { fontSize: 13, color: '#1a237e' },
  priceRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 4, paddingHorizontal: 8 },
  priceFunc: { fontSize: 13, fontWeight: '500', color: '#333', flex: 1 },
  priceVal: { fontSize: 12, color: '#666', marginLeft: 8 },
  // Modal styles
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center' },
  modalContent: { backgroundColor: '#fff', borderRadius: 16, padding: 20, width: '90%', maxWidth: 600, maxHeight: '90%' },
  modalTitle: { fontSize: 20, fontWeight: '600', color: '#1a237e', marginBottom: 16, textAlign: 'center' },
  label: { fontSize: 13, fontWeight: '600', color: '#333', marginTop: 12, marginBottom: 4 },
  input: { borderWidth: 1, borderColor: '#ddd', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10, fontSize: 14, color: '#333' },
  pickerWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  soOption: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8, borderWidth: 1, borderColor: '#ddd', backgroundColor: '#f5f5f5' },
  soOptionActive: { backgroundColor: '#1a237e', borderColor: '#1a237e' },
  soOptionText: { fontSize: 13, color: '#333' },
  calcBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#ff6f00', paddingVertical: 10, borderRadius: 8, marginTop: 12, gap: 8 },
  calcBtnText: { color: '#fff', fontSize: 14, fontWeight: '600' },
  sectionTitle: { fontSize: 15, fontWeight: '600', color: '#1a237e', marginTop: 16, marginBottom: 8 },
  calcItem: { backgroundColor: '#f5f5f5', padding: 10, borderRadius: 8, marginBottom: 6 },
  calcFunc: { fontSize: 13, fontWeight: '600', color: '#333' },
  calcDetail: { fontSize: 12, color: '#666', marginTop: 2 },
  calcSubtotal: { fontSize: 15, fontWeight: '700', color: '#1a237e', marginTop: 8, textAlign: 'right' },
  saveBtn: { backgroundColor: '#1a237e', paddingVertical: 14, borderRadius: 10, alignItems: 'center', marginTop: 16 },
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
