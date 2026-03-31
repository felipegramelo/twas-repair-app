import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, FlatList, Alert, TextInput, Modal,
  ActivityIndicator, ScrollView, KeyboardAvoidingView, Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { proposalAPI } from '../../services/api';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Proposal, ProposalItem } from '../../types';

export default function PropostasScreen() {
  const router = useRouter();
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingProposal, setEditingProposal] = useState<Proposal | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  // Form fields
  const [empresa, setEmpresa] = useState('');
  const [contato, setContato] = useState('');
  const [email, setEmail] = useState('');
  const [embarcacao, setEmbarcacao] = useState('');
  const [equipamento, setEquipamento] = useState('');
  const [observacoes, setObservacoes] = useState('');
  const [itens, setItens] = useState<ProposalItem[]>([]);

  useEffect(() => { loadProposals(); }, []);

  const loadProposals = async () => {
    try {
      const data = await proposalAPI.getAll();
      setProposals(data);
    } catch {
      if (Platform.OS === 'web') window.alert('Erro ao carregar propostas');
      else Alert.alert('Erro', 'Erro ao carregar propostas');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setEmpresa(''); setContato(''); setEmail(''); setEmbarcacao('');
    setEquipamento(''); setObservacoes(''); setItens([]); setEditingProposal(null);
  };

  const openAddModal = () => { resetForm(); setModalVisible(true); };

  const handleEdit = (proposal: Proposal) => {
    setEditingProposal(proposal);
    setEmpresa(proposal.empresa);
    setContato(proposal.contato);
    setEmail(proposal.email);
    setEmbarcacao(proposal.embarcacao);
    setEquipamento(proposal.equipamento);
    setObservacoes(proposal.observacoes || '');
    setItens(proposal.itens || []);
    setModalVisible(true);
  };

  const addItem = () => {
    setItens([...itens, { id: Date.now().toString(), titulo: '', descricao: '', valor: 0 }]);
  };

  const updateItem = (index: number, field: keyof ProposalItem, value: string | number) => {
    const updated = [...itens];
    (updated[index] as any)[field] = value;
    setItens(updated);
  };

  const removeItem = (index: number) => {
    setItens(itens.filter((_, i) => i !== index));
  };

  const handleSave = async () => {
    if (!empresa.trim() || !contato.trim()) {
      if (Platform.OS === 'web') window.alert('Preencha Empresa e Contato');
      else Alert.alert('Erro', 'Preencha Empresa e Contato');
      return;
    }
    if (itens.length === 0) {
      if (Platform.OS === 'web') window.alert('Adicione pelo menos um item');
      else Alert.alert('Erro', 'Adicione pelo menos um item');
      return;
    }
    for (const item of itens) {
      if (!item.titulo.trim()) {
        if (Platform.OS === 'web') window.alert('Preencha o título de todos os itens');
        else Alert.alert('Erro', 'Preencha o título de todos os itens');
        return;
      }
    }
    try {
      const payload = { empresa, contato, email, embarcacao, equipamento, observacoes, itens };
      if (editingProposal) {
        await proposalAPI.update(editingProposal.id, payload);
      } else {
        await proposalAPI.create(payload);
      }
      setModalVisible(false);
      resetForm();
      loadProposals();
      const msg = editingProposal ? 'Proposta atualizada' : 'Proposta criada com sucesso';
      if (Platform.OS === 'web') window.alert(msg);
      else Alert.alert('Sucesso', msg);
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || 'Erro ao salvar proposta';
      if (Platform.OS === 'web') window.alert(errorMsg);
      else Alert.alert('Erro', errorMsg);
    }
  };

  const handleDelete = (proposal: Proposal) => {
    if (Platform.OS === 'web') {
      if (window.confirm(`Excluir a proposta ${proposal.numero_proposta}?`)) performDelete(proposal);
    } else {
      Alert.alert('Confirmar', `Excluir a proposta ${proposal.numero_proposta}?`, [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Excluir', style: 'destructive', onPress: () => performDelete(proposal) },
      ]);
    }
  };

  const performDelete = async (proposal: Proposal) => {
    try {
      await proposalAPI.delete(proposal.id);
      loadProposals();
    } catch (error: any) {
      const msg = error.response?.data?.detail || 'Erro ao excluir';
      if (Platform.OS === 'web') window.alert(msg);
      else Alert.alert('Erro', msg);
    }
  };

  const handleDownloadPDF = async (proposal: Proposal, tipo: string) => {
    setDownloading(`${proposal.id}-${tipo}`);
    try {
      const blob = await proposalAPI.downloadPDF(proposal.id, tipo);
      if (Platform.OS === 'web') {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Proposta_${tipo}_${proposal.numero_proposta.replace(/ /g, '_')}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    } catch (error: any) {
      const msg = error.response?.data?.detail || 'Erro ao gerar PDF';
      if (Platform.OS === 'web') window.alert(msg);
      else Alert.alert('Erro', msg);
    } finally {
      setDownloading(null);
    }
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      return `${d.getDate().toString().padStart(2, '0')}/${(d.getMonth() + 1).toString().padStart(2, '0')}/${d.getFullYear()}`;
    } catch { return dateStr; }
  };

  const calcTotal = (items: ProposalItem[]) => {
    return items.reduce((sum, i) => sum + (i.valor || 0), 0);
  };

  const formatCurrency = (val: number) => {
    return `R$ ${val.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const renderProposal = ({ item }: { item: Proposal }) => (
    <View style={s.card} data-testid={`proposal-card-${item.id}`}>
      <View style={s.cardHeader}>
        <View style={s.numberBadge}>
          <Text style={s.numberText}>{item.numero_proposta}</Text>
        </View>
        <Text style={s.dateText}>{formatDate(item.created_at)}</Text>
      </View>
      <Text style={s.cardTitle}>{item.empresa}</Text>
      <Text style={s.cardSub}>A/C: {item.contato}</Text>
      {item.embarcacao ? <Text style={s.cardSub}>Embarcacao: {item.embarcacao}</Text> : null}
      {item.equipamento ? <Text style={s.cardSub}>Equipamento: {item.equipamento}</Text> : null}
      <Text style={s.cardTotal}>{formatCurrency(calcTotal(item.itens))} ({item.itens.length} {item.itens.length === 1 ? 'item' : 'itens'})</Text>

      <View style={s.pdfRow}>
        <TouchableOpacity
          style={[s.pdfBtn, { backgroundColor: '#1a237e' }]}
          onPress={() => handleDownloadPDF(item, 'comercial')}
          disabled={downloading === `${item.id}-comercial`}
          data-testid={`pdf-comercial-${item.id}`}
        >
          {downloading === `${item.id}-comercial` ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <>
              <Ionicons name="document-text" size={16} color="#fff" />
              <Text style={s.pdfBtnText}>PDF Comercial</Text>
            </>
          )}
        </TouchableOpacity>
        <TouchableOpacity
          style={[s.pdfBtn, { backgroundColor: '#2e7d32' }]}
          onPress={() => handleDownloadPDF(item, 'tecnica')}
          disabled={downloading === `${item.id}-tecnica`}
          data-testid={`pdf-tecnica-${item.id}`}
        >
          {downloading === `${item.id}-tecnica` ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <>
              <Ionicons name="document" size={16} color="#fff" />
              <Text style={s.pdfBtnText}>PDF Tecnica</Text>
            </>
          )}
        </TouchableOpacity>
      </View>

      <View style={s.cardActions}>
        <TouchableOpacity onPress={() => handleEdit(item)} style={s.actionBtn} data-testid={`edit-proposal-${item.id}`}>
          <Ionicons name="pencil" size={20} color="#1a237e" />
        </TouchableOpacity>
        <TouchableOpacity onPress={() => handleDelete(item)} style={s.actionBtn} data-testid={`delete-proposal-${item.id}`}>
          <Ionicons name="trash" size={20} color="#d32f2f" />
        </TouchableOpacity>
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
        <Text style={s.title}>Propostas Comerciais</Text>
        <TouchableOpacity onPress={openAddModal} style={s.addBtn} data-testid="add-proposal-btn">
          <Ionicons name="add" size={24} color="#fff" />
        </TouchableOpacity>
      </View>

      <FlatList
        data={proposals}
        renderItem={renderProposal}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ padding: 16 }}
        ListEmptyComponent={
          <View style={s.empty}>
            <Ionicons name="briefcase-outline" size={64} color="#ccc" />
            <Text style={s.emptyText}>Nenhuma proposta cadastrada</Text>
            <Text style={s.emptySubText}>Toque no + para criar uma nova proposta</Text>
          </View>
        }
      />

      <Modal visible={modalVisible} animationType="slide" transparent onRequestClose={() => setModalVisible(false)}>
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={s.modalOverlay}>
          <View style={s.modalContent}>
            <ScrollView showsVerticalScrollIndicator={false}>
              <Text style={s.modalTitle}>{editingProposal ? `Editar Proposta ${editingProposal.numero_proposta}` : 'Nova Proposta'}</Text>

              <Text style={s.label}>Empresa *</Text>
              <TextInput style={s.input} placeholder="Nome da empresa" value={empresa} onChangeText={setEmpresa} data-testid="proposal-empresa-input" />

              <Text style={s.label}>Pessoa de Contato (A/C) *</Text>
              <TextInput style={s.input} placeholder="Nome do contato" value={contato} onChangeText={setContato} data-testid="proposal-contato-input" />

              <Text style={s.label}>Email</Text>
              <TextInput style={s.input} placeholder="email@exemplo.com" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" data-testid="proposal-email-input" />

              <Text style={s.label}>Embarcacao / Plataforma</Text>
              <TextInput style={s.input} placeholder="Ex: Plataforma P-71" value={embarcacao} onChangeText={setEmbarcacao} data-testid="proposal-embarcacao-input" />

              <Text style={s.label}>Equipamento</Text>
              <TextInput style={s.input} placeholder="Ex: Turbina Principal" value={equipamento} onChangeText={setEquipamento} data-testid="proposal-equipamento-input" />

              {/* Items Section */}
              <View style={s.itemsHeader}>
                <Text style={s.label}>Itens do Escopo *</Text>
                <TouchableOpacity onPress={addItem} style={s.addItemBtn} data-testid="add-item-btn">
                  <Ionicons name="add-circle" size={28} color="#1a237e" />
                </TouchableOpacity>
              </View>

              {itens.map((item, idx) => (
                <View key={item.id} style={s.itemCard}>
                  <View style={s.itemHeader}>
                    <Text style={s.itemNum}>Item {idx + 1}</Text>
                    <TouchableOpacity onPress={() => removeItem(idx)} data-testid={`remove-item-${idx}`}>
                      <Ionicons name="close-circle" size={24} color="#d32f2f" />
                    </TouchableOpacity>
                  </View>
                  <TextInput
                    style={s.input}
                    placeholder="Titulo do item *"
                    value={item.titulo}
                    onChangeText={(v) => updateItem(idx, 'titulo', v)}
                    data-testid={`item-titulo-${idx}`}
                  />
                  <TextInput
                    style={[s.input, { minHeight: 60, textAlignVertical: 'top' }]}
                    placeholder="Descricao detalhada"
                    value={item.descricao}
                    onChangeText={(v) => updateItem(idx, 'descricao', v)}
                    multiline
                    data-testid={`item-descricao-${idx}`}
                  />
                  <TextInput
                    style={s.input}
                    placeholder="Valor (R$)"
                    value={item.valor ? String(item.valor) : ''}
                    onChangeText={(v) => updateItem(idx, 'valor', parseFloat(v) || 0)}
                    keyboardType="numeric"
                    data-testid={`item-valor-${idx}`}
                  />
                </View>
              ))}

              {itens.length > 0 && (
                <View style={s.totalRow}>
                  <Text style={s.totalLabel}>Total:</Text>
                  <Text style={s.totalValue}>{formatCurrency(calcTotal(itens))}</Text>
                </View>
              )}

              <Text style={[s.label, { marginTop: 16 }]}>Observacoes</Text>
              <TextInput
                style={[s.input, { minHeight: 80, textAlignVertical: 'top' }]}
                placeholder="Observacoes gerais da proposta"
                value={observacoes}
                onChangeText={setObservacoes}
                multiline
                data-testid="proposal-observacoes-input"
              />

              <View style={s.modalBtns}>
                <TouchableOpacity style={[s.modalBtn, s.cancelBtn]} onPress={() => { setModalVisible(false); resetForm(); }}>
                  <Text style={s.cancelText}>Cancelar</Text>
                </TouchableOpacity>
                <TouchableOpacity style={[s.modalBtn, s.saveBtn]} onPress={handleSave} data-testid="save-proposal-btn">
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
  addBtn: { backgroundColor: '#2e7d32', width: 40, height: 40, borderRadius: 20, justifyContent: 'center', alignItems: 'center' },
  card: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.1, shadowRadius: 2, elevation: 2 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  numberBadge: { backgroundColor: '#1a237e', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 6 },
  numberText: { color: '#fff', fontSize: 13, fontWeight: '700' },
  dateText: { fontSize: 12, color: '#999' },
  cardTitle: { fontSize: 16, fontWeight: '600', color: '#212121', marginBottom: 4 },
  cardSub: { fontSize: 13, color: '#666', marginBottom: 2 },
  cardTotal: { fontSize: 14, fontWeight: '700', color: '#2e7d32', marginTop: 8 },
  pdfRow: { flexDirection: 'row', gap: 8, marginTop: 12 },
  pdfBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, paddingVertical: 10, borderRadius: 8 },
  pdfBtnText: { color: '#fff', fontSize: 13, fontWeight: '600' },
  cardActions: { flexDirection: 'row', gap: 8, marginTop: 8, justifyContent: 'flex-end' },
  actionBtn: { padding: 8 },
  empty: { alignItems: 'center', paddingVertical: 64 },
  emptyText: { fontSize: 16, color: '#999', marginTop: 16 },
  emptySubText: { fontSize: 13, color: '#bbb', marginTop: 4 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modalContent: { backgroundColor: '#fff', borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 24, maxHeight: '95%' },
  modalTitle: { fontSize: 20, fontWeight: '600', color: '#1a237e', marginBottom: 16 },
  label: { fontSize: 14, fontWeight: '600', color: '#212121', marginBottom: 6, marginTop: 10 },
  input: { backgroundColor: '#f5f5f5', borderRadius: 8, padding: 14, fontSize: 15, borderWidth: 1, borderColor: '#e0e0e0', marginBottom: 4 },
  itemsHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 16, marginBottom: 4 },
  addItemBtn: { padding: 4 },
  itemCard: { backgroundColor: '#f9f9f9', borderRadius: 10, padding: 12, marginBottom: 10, borderWidth: 1, borderColor: '#e8e8e8' },
  itemHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  itemNum: { fontSize: 13, fontWeight: '700', color: '#1a237e' },
  totalRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 12, paddingVertical: 10, backgroundColor: '#E8EAF6', borderRadius: 8, marginTop: 8 },
  totalLabel: { fontSize: 15, fontWeight: '700', color: '#1a237e' },
  totalValue: { fontSize: 15, fontWeight: '700', color: '#2e7d32' },
  modalBtns: { flexDirection: 'row', gap: 12, marginTop: 24, marginBottom: 16 },
  modalBtn: { flex: 1, height: 48, borderRadius: 8, justifyContent: 'center', alignItems: 'center' },
  cancelBtn: { backgroundColor: '#f5f5f5' },
  cancelText: { color: '#666', fontSize: 16, fontWeight: '600' },
  saveBtn: { backgroundColor: '#1a237e' },
  saveText: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
