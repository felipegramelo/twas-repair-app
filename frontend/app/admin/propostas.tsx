import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, FlatList, Alert, TextInput, Modal,
  ActivityIndicator, ScrollView, KeyboardAvoidingView, Platform, Image,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Sharing from 'expo-sharing';
import { proposalAPI } from '../../services/api';
import { downloadAndSharePDF } from '../../utils/pdfHelper';
import { Proposal, ProposalItem, ProposalSubsection } from '../../types';

const MONTHS = [
  { value: 0, label: 'Todos' }, { value: 1, label: 'Jan' }, { value: 2, label: 'Fev' }, { value: 3, label: 'Mar' },
  { value: 4, label: 'Abr' }, { value: 5, label: 'Mai' }, { value: 6, label: 'Jun' },
  { value: 7, label: 'Jul' }, { value: 8, label: 'Ago' }, { value: 9, label: 'Set' },
  { value: 10, label: 'Out' }, { value: 11, label: 'Nov' }, { value: 12, label: 'Dez' },
];

const DEFAULT_TERMOS = `\u2212 Horas de Viagem e Espera: Ser\u00e3o cobradas conforme as horas de trabalho padr\u00e3o e as taxas aplic\u00e1veis.
\u2212 Horas Offshore: Cobran\u00e7a m\u00ednima de 12 horas por dia.
\u2212 Horas Onshore: Cobran\u00e7a m\u00ednima de 8 horas por dia.
\u2212 Horas Extras:
  o Dias \u00fateis: Valor da hora trabalhada multiplicado por 1,70.
  o S\u00e1bados: Valor da hora trabalhada multiplicado por 1,80.
  o Domingos e feriados nacionais ou municipais em S\u00e3o Gon\u00e7alo, RJ: Valor da hora trabalhada multiplicado por 2.
\u2212 Servi\u00e7os Fora do Rio de Janeiro: Ser\u00e1 aplicada uma taxa adicional de 15% para servi\u00e7os realizados fora do estado do RJ.
\u2212 Despesas: Os custos de viagem, hospedagem, alimenta\u00e7\u00e3o, materiais, ferramentas e transporte de m\u00e3o de obra ser\u00e3o cobrados ao custo, acrescidos de uma taxa administrativa de 15% e impostos aplic\u00e1veis (19,53%).
\u2212 Impostos: O total de 19,53% (IRPJ e adicional IR 8%, CSLL 2,88%, COFINS 3%, PIS 0,65% e ISS 5%) j\u00e1 est\u00e1 inclu\u00eddo nos valores finais.
\u2212 Condi\u00e7\u00f5es de Pagamento: O pagamento dever\u00e1 ser realizado em at\u00e9 30 dias a partir da data de emiss\u00e3o da fatura.
\u2212 Penalidades por Atraso de Pagamento: Ser\u00e1 aplicada multa de 2% sobre o valor em atraso, conforme a Lei n\u00ba 8.078/90, e juros de 0,0333% ao dia, conforme a Lei n\u00ba 5.172/66.
\u2212 C\u00e1lculo da Taxa Di\u00e1ria: O c\u00e1lculo ser\u00e1 realizado com base no per\u00edodo compreendido entre o primeiro dia de viagem e o retorno \u00e0s nossas instala\u00e7\u00f5es.
\u2212 Ajuste Anual: As taxas ser\u00e3o reajustadas anualmente com base no \u00cdndice Geral de Pre\u00e7os do Mercado (IGP-M), publicado pela Funda\u00e7\u00e3o Get\u00falio Vargas (FGV), e em conformidade com o acordo coletivo vigente celebrado entre [RJ METAL/SIMMMERJ-RJ metal] e [TWAS Repair Servi\u00e7os Navais e Industriais Ltda], ou conforme a legisla\u00e7\u00e3o em vigor. O reajuste ser\u00e1 autom\u00e1tico e n\u00e3o haver\u00e1 necessidade de aviso pr\u00e9vio.
Quaisquer pre\u00e7os e prazos diferentes relacionados ao servi\u00e7o em negocia\u00e7\u00e3o devem ser previamente acordados antes da aceita\u00e7\u00e3o do servi\u00e7o.`;

interface ProposalPhoto {
  id: string;
  section_index: number;
  section_key: string;
  storage_path: string;
  original_filename: string;
}

export default function PropostasScreen() {
  const router = useRouter();
  const [authToken, setAuthToken] = useState('');
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingProposal, setEditingProposal] = useState<Proposal | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [poModalVisible, setPOModalVisible] = useState(false);
  const [poProposal, setPOProposal] = useState<Proposal | null>(null);
  const [poNumber, setPONumber] = useState('');
  const [submittingPO, setSubmittingPO] = useState(false);

  // Photos
  const [photos, setPhotos] = useState<ProposalPhoto[]>([]);
  const [uploadingSectionKey, setUploadingSectionKey] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const currentUploadKey = useRef<string>('');
  const currentUploadIndex = useRef<number>(0);

  // Filters
  const now = new Date();
  const [filterMonth, setFilterMonth] = useState(now.getMonth() + 1);
  const [filterYear, setFilterYear] = useState(now.getFullYear());
  const [filterPickerVisible, setFilterPickerVisible] = useState(false);

  // Form fields
  const [empresa, setEmpresa] = useState('');
  const [contato, setContato] = useState('');
  const [email, setEmail] = useState('');
  const [embarcacao, setEmbarcacao] = useState('');
  const [local, setLocal] = useState('');
  const [equipamento, setEquipamento] = useState('');
  const [servico, setServico] = useState('');
  const [observacoes, setObservacoes] = useState('');
  const [itens, setItens] = useState<ProposalItem[]>([]);
  const [termosGerais, setTermosGerais] = useState(DEFAULT_TERMOS);
  const [showTermos, setShowTermos] = useState(true);
  const [expandedSection, setExpandedSection] = useState<string | null>(null);

  useEffect(() => { loadProposals(); loadToken(); }, [filterMonth, filterYear]);

  const loadToken = async () => {
    const t = await AsyncStorage.getItem('token');
    if (t) setAuthToken(t);
  };

  const loadProposals = async () => {
    setLoading(true);
    try {
      const m = filterMonth === 0 ? undefined : filterMonth;
      const data = await proposalAPI.getAllFiltered(m, filterYear);
      setProposals(data);
    } catch {
      showMsg('Erro ao carregar propostas');
    } finally {
      setLoading(false);
    }
  };

  const showMsg = (msg: string) => {
    if (Platform.OS === 'web') window.alert(msg);
    else Alert.alert('Aviso', msg);
  };

  const resetForm = () => {
    setEmpresa(''); setContato(''); setEmail(''); setEmbarcacao('');
    setEquipamento(''); setServico(''); setObservacoes(''); setItens([]); setEditingProposal(null);
    setTermosGerais(DEFAULT_TERMOS); setShowTermos(true); setPhotos([]);
    setExpandedSection(null);
  };

  const openAddModal = () => { resetForm(); setModalVisible(true); };

  const handleEdit = async (proposal: Proposal) => {
    setEditingProposal(proposal);
    setEmpresa(proposal.empresa);
    setContato(proposal.contato);
    setEmail(proposal.email);
    setEmbarcacao(proposal.embarcacao);
    setLocal(proposal.local || '');
    setEquipamento(proposal.equipamento);
    setServico(proposal.servico || '');
    setObservacoes(proposal.observacoes || '');
    setItens(proposal.itens || []);
    setTermosGerais(proposal.termos_gerais || DEFAULT_TERMOS);
    setShowTermos(true);
    try {
      const p = await proposalAPI.getPhotos(proposal.id);
      setPhotos(p);
    } catch { setPhotos([]); }
    setModalVisible(true);
  };

  // === Section Management ===
  const addItem = () => {
    setItens([...itens, { id: Date.now().toString(), titulo: '', descricao: '', valor: 0, subsections: [] }]);
  };

  const updateItem = (index: number, field: keyof ProposalItem, value: string | number) => {
    const updated = [...itens];
    (updated[index] as any)[field] = value;
    setItens(updated);
  };

  const removeItem = (index: number) => {
    setItens(itens.filter((_, i) => i !== index));
  };

  const moveItem = (index: number, direction: 'up' | 'down') => {
    if (direction === 'up' && index === 0) return;
    if (direction === 'down' && index === itens.length - 1) return;
    const updated = [...itens];
    const swap = direction === 'up' ? index - 1 : index + 1;
    [updated[index], updated[swap]] = [updated[swap], updated[index]];
    setItens(updated);
  };

  // === Subsection Management ===
  const addSubsection = (sectionIndex: number) => {
    const updated = [...itens];
    const subs = updated[sectionIndex].subsections || [];
    subs.push({ id: Date.now().toString(), titulo: '', descricao: '' });
    updated[sectionIndex] = { ...updated[sectionIndex], subsections: subs };
    setItens(updated);
  };

  const updateSubsection = (secIdx: number, subIdx: number, field: keyof ProposalSubsection, value: string) => {
    const updated = [...itens];
    const subs = [...(updated[secIdx].subsections || [])];
    subs[subIdx] = { ...subs[subIdx], [field]: value };
    updated[secIdx] = { ...updated[secIdx], subsections: subs };
    setItens(updated);
  };

  const removeSubsection = (secIdx: number, subIdx: number) => {
    const updated = [...itens];
    const subs = (updated[secIdx].subsections || []).filter((_, i) => i !== subIdx);
    updated[secIdx] = { ...updated[secIdx], subsections: subs };
    setItens(updated);
  };

  // === Photo Upload ===
  const triggerUpload = (sectionKey: string, sectionIndex: number) => {
    currentUploadKey.current = sectionKey;
    currentUploadIndex.current = sectionIndex;
    if (Platform.OS === 'web' && fileInputRef.current) fileInputRef.current.click();
  };

  const handleFileSelected = async (event: any) => {
    const files = event.target.files;
    if (!files || files.length === 0 || !editingProposal) return;
    const secKey = currentUploadKey.current;
    const secIdx = currentUploadIndex.current;
    setUploadingSectionKey(secKey);
    try {
      for (let i = 0; i < files.length; i++) {
        await proposalAPI.uploadPhoto(editingProposal.id, files[i], secIdx, files[i].name, secKey);
      }
      const p = await proposalAPI.getPhotos(editingProposal.id);
      setPhotos(p);
      showMsg('Arquivo enviado com sucesso');
    } catch (e: any) {
      showMsg('Erro ao enviar arquivo: ' + (e.message || ''));
    } finally {
      setUploadingSectionKey(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDeletePhoto = async (photoId: string) => {
    if (!editingProposal) return;
    if (Platform.OS === 'web' && !window.confirm('Excluir esta foto/arquivo?')) return;
    try {
      await proposalAPI.deletePhoto(editingProposal.id, photoId);
      setPhotos(prev => prev.filter(p => p.id !== photoId));
    } catch { showMsg('Erro ao excluir'); }
  };

  const getPhotoUrl = (storagePath: string) => proposalAPI.getPhotoUrl(storagePath, authToken);
  const getPhotosForKey = (key: string) => photos.filter(p => p.section_key === key);

  // === Save ===
  const handleSave = async () => {
    if (!empresa.trim() || !contato.trim()) { showMsg('Preencha Empresa e Contato'); return; }
    if (!servico.trim()) { showMsg('Preencha o campo Servico'); return; }
    if (itens.length === 0) { showMsg('Adicione pelo menos uma secao no escopo'); return; }
    for (const item of itens) {
      if (!item.titulo.trim()) { showMsg('Preencha o titulo de todas as secoes'); return; }
    }
    try {
      const payload = {
        empresa, contato, email, embarcacao, local, equipamento, servico, observacoes,
        itens: itens.map(item => ({
          ...item,
          subsections: (item.subsections || []).map(sub => ({
            id: sub.id,
            titulo: sub.titulo,
            descricao: sub.descricao,
          })),
        })),
        termos_gerais: termosGerais,
      };
      if (editingProposal) {
        await proposalAPI.update(editingProposal.id, payload);
      } else {
        await proposalAPI.create(payload);
      }
      setModalVisible(false);
      resetForm();
      loadProposals();
      showMsg(editingProposal ? 'Proposta atualizada' : 'Proposta criada com sucesso');
    } catch (error: any) {
      showMsg(error.response?.data?.detail || 'Erro ao salvar proposta');
    }
  };

  const handleDelete = (proposal: Proposal) => {
    if (Platform.OS === 'web') {
      if (window.confirm(`Excluir a proposta ${proposal.numero_proposta}?`)) performDelete(proposal);
    } else {
      Alert.alert('Confirmar', `Excluir?`, [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Excluir', style: 'destructive', onPress: () => performDelete(proposal) },
      ]);
    }
  };

  const performDelete = async (proposal: Proposal) => {
    try { await proposalAPI.delete(proposal.id); loadProposals(); }
    catch (error: any) { showMsg(error.response?.data?.detail || 'Erro ao excluir'); }
  };

  const handleDownloadPDF = async (proposal: Proposal, tipo: string) => {
    setDownloading(`${proposal.id}-${tipo}`);
    try {
      if (Platform.OS === 'web') {
        const blob = await proposalAPI.downloadPDF(proposal.id, tipo);
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Proposta_${tipo}_${proposal.numero_proposta.replace(/ /g, '_')}.pdf`;
        document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
      } else {
        // iOS/Android native: download via expo-file-system and share
        const backendUrl = process.env.EXPO_PUBLIC_BACKEND_URL || '';
        const pdfUrl = `${backendUrl}/api/proposals/${proposal.id}/pdf?tipo=${tipo}&t=${Date.now()}`;
        const fileName = `Proposta_${tipo}_${proposal.numero_proposta.replace(/ /g, '_')}.pdf`;
        await downloadAndSharePDF(
          () => proposalAPI.downloadPDF(proposal.id, tipo),
          pdfUrl,
          fileName,
        );
      }
    } catch (error: any) {
      showMsg(error.response?.data?.detail || 'Erro ao gerar PDF');
    } finally { setDownloading(null); }
  };

  const openPOModal = (proposal: Proposal) => { setPOProposal(proposal); setPONumber(''); setPOModalVisible(true); };

  const handleInformarPO = async () => {
    if (!poNumber.trim() || !poProposal) { showMsg('Informe o numero da P.O.'); return; }
    setSubmittingPO(true);
    try {
      await proposalAPI.informarPO(poProposal.id, poNumber.trim());
      setPOModalVisible(false); setPOProposal(null); setPONumber('');
      loadProposals();
      showMsg('P.O. informada! Ordem de Servico criada automaticamente.');
    } catch (error: any) {
      showMsg(error.response?.data?.detail || 'Erro ao informar P.O.');
    } finally { setSubmittingPO(false); }
  };

  const formatDate = (d: string) => { try { const dt = new Date(d); return `${dt.getDate().toString().padStart(2,'0')}/${(dt.getMonth()+1).toString().padStart(2,'0')}/${dt.getFullYear()}`; } catch { return d; } };
  const calcTotal = (items: ProposalItem[]) => items.reduce((s, i) => s + (i.valor || 0), 0);
  const formatCurrency = (v: number) => `R$ ${v.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const getFilterLabel = () => { const m = MONTHS.find(m => m.value === filterMonth)?.label || 'Todos'; return filterMonth === 0 ? `${filterYear}` : `${m}/${filterYear}`; };
  const pendentesCount = proposals.filter(p => (p.status || 'pendente') === 'pendente').length;
  const aprovadasCount = proposals.filter(p => p.status === 'aprovada').length;

  // Count total items for termos section number
  const termosNumber = itens.length + 1;

  // === Photo Grid Render ===
  const renderPhotoArea = (sectionKey: string, sectionIndex: number) => {
    const sPhotos = getPhotosForKey(sectionKey);
    return (
      <View style={s.photosArea}>
        {sPhotos.map(photo => (
          <View key={photo.id} style={s.photoItem}>
            <Image source={{ uri: getPhotoUrl(photo.storage_path) }} style={s.photoThumb} />
            <Text style={s.photoName} numberOfLines={1}>{photo.original_filename}</Text>
            <TouchableOpacity onPress={() => handleDeletePhoto(photo.id)} style={s.photoDeleteBtn}>
              <Ionicons name="trash-outline" size={16} color="#d32f2f" />
            </TouchableOpacity>
          </View>
        ))}
        <TouchableOpacity
          style={s.uploadBtn}
          onPress={() => triggerUpload(sectionKey, sectionIndex)}
          disabled={uploadingSectionKey === sectionKey}
          data-testid={`upload-photo-${sectionKey}`}
        >
          {uploadingSectionKey === sectionKey ? <ActivityIndicator size="small" color="#000000" /> : (
            <><Ionicons name="cloud-upload-outline" size={18} color="#000000" /><Text style={s.uploadBtnText}>Adicionar Foto/Arquivo</Text></>
          )}
        </TouchableOpacity>
      </View>
    );
  };

  // === List Item Render ===
  const renderProposal = ({ item }: { item: Proposal }) => {
    const isAprovada = item.status === 'aprovada';
    const totalSubs = (item.itens || []).reduce((acc, it) => acc + (it.subsections?.length || 0), 0);
    const sectionLabel = `${item.itens.length} ${item.itens.length === 1 ? 'secao' : 'secoes'}${totalSubs > 0 ? `, ${totalSubs} sub` : ''}`;
    return (
      <View style={[s.card, isAprovada && { borderLeftWidth: 4, borderLeftColor: '#2e7d32' }]} data-testid={`proposal-card-${item.id}`}>
        <View style={s.cardHeader}>
          <View style={s.numberBadge}><Text style={s.numberText}>{item.numero_proposta}</Text></View>
          <View style={s.headerRight}>
            <View style={[s.statusBadge, isAprovada ? { backgroundColor: '#E8F5E9' } : { backgroundColor: '#FFF3E0' }]}>
              <Text style={[s.statusText, isAprovada ? { color: '#2e7d32' } : { color: '#e65100' }]}>{isAprovada ? 'Aprovada' : 'Pendente'}</Text>
            </View>
            <Text style={s.dateText}>{formatDate(item.created_at)}</Text>
          </View>
        </View>
        <Text style={s.cardTitle}>{item.empresa}</Text>
        <Text style={s.cardSub}>A/C: {item.contato}</Text>
        {item.embarcacao ? <Text style={s.cardSub}>Embarcacao: {item.embarcacao}</Text> : null}
        {item.local ? <Text style={s.cardSub}>Local: {item.local}</Text> : null}
        <Text style={s.cardTotal}>{formatCurrency(calcTotal(item.itens))} ({sectionLabel})</Text>

        {isAprovada && (
          <View style={s.approvedInfo}>
            <View style={s.infoRow}><Ionicons name="receipt" size={14} color="#000000" /><Text style={s.infoText}>P.O.: {item.po_number}</Text></View>
            <View style={s.infoRow}><Ionicons name="document-text" size={14} color="#2e7d32" /><Text style={s.infoText}>O.S.: {item.os_number}</Text></View>
          </View>
        )}

        {!isAprovada && (
          <TouchableOpacity style={s.poBtn} onPress={() => openPOModal(item)} data-testid={`informar-po-${item.id}`}>
            <Ionicons name="checkmark-circle" size={18} color="#fff" />
            <Text style={s.poBtnText}>Informar P.O.</Text>
          </TouchableOpacity>
        )}

        <View style={s.pdfRow}>
          <TouchableOpacity style={[s.pdfBtn, { backgroundColor: '#000000' }]} onPress={() => handleDownloadPDF(item, 'comercial')} disabled={downloading === `${item.id}-comercial`} data-testid={`pdf-comercial-${item.id}`}>
            {downloading === `${item.id}-comercial` ? <ActivityIndicator size="small" color="#fff" /> : <><Ionicons name="document-text" size={16} color="#fff" /><Text style={s.pdfBtnText}>PDF Comercial</Text></>}
          </TouchableOpacity>
          <TouchableOpacity style={[s.pdfBtn, { backgroundColor: '#2e7d32' }]} onPress={() => handleDownloadPDF(item, 'tecnica')} disabled={downloading === `${item.id}-tecnica`} data-testid={`pdf-tecnica-${item.id}`}>
            {downloading === `${item.id}-tecnica` ? <ActivityIndicator size="small" color="#fff" /> : <><Ionicons name="document" size={16} color="#fff" /><Text style={s.pdfBtnText}>PDF Tecnica</Text></>}
          </TouchableOpacity>
        </View>

        <View style={s.cardActions}>
          {!isAprovada && (
            <TouchableOpacity onPress={() => handleEdit(item)} style={s.actionBtn} data-testid={`edit-proposal-${item.id}`}>
              <Ionicons name="pencil" size={20} color="#000000" />
            </TouchableOpacity>
          )}
          <TouchableOpacity onPress={() => handleDelete(item)} style={s.actionBtn} data-testid={`delete-proposal-${item.id}`}>
            <Ionicons name="trash" size={20} color="#d32f2f" />
          </TouchableOpacity>
        </View>
      </View>
    );
  };

  return (
    <SafeAreaView style={s.container}>
      {Platform.OS === 'web' && (
        <input
          type="file"
          ref={(r: any) => { fileInputRef.current = r; }}
          style={{ display: 'none' }}
          accept="image/*,.pdf"
          multiple
          onChange={handleFileSelected}
        />
      )}

      <View style={s.header}>
        <TouchableOpacity onPress={() => router.back()} style={s.backBtn}><Ionicons name="arrow-back" size={24} color="#000000" /></TouchableOpacity>
        <Text style={s.title}>Propostas</Text>
        <TouchableOpacity onPress={openAddModal} style={s.addBtn} data-testid="add-proposal-btn"><Ionicons name="add" size={24} color="#fff" /></TouchableOpacity>
      </View>

      <View style={s.filterBar}>
        <TouchableOpacity style={s.filterBtn} onPress={() => setFilterPickerVisible(true)} data-testid="filter-btn">
          <Ionicons name="calendar" size={18} color="#000000" />
          <Text style={s.filterLabel}>{getFilterLabel()}</Text>
          <Ionicons name="chevron-down" size={16} color="#000000" />
        </TouchableOpacity>
        <View style={s.statsRow}>
          <View style={[s.statBadge, { backgroundColor: '#FFF3E0' }]}><Text style={[s.statText, { color: '#e65100' }]}>{pendentesCount} Pend.</Text></View>
          <View style={[s.statBadge, { backgroundColor: '#E8F5E9' }]}><Text style={[s.statText, { color: '#2e7d32' }]}>{aprovadasCount} Aprov.</Text></View>
        </View>
      </View>

      {loading ? (
        <View style={s.center}><ActivityIndicator size="large" color="#000000" /></View>
      ) : (
        <FlatList data={proposals} renderItem={renderProposal} keyExtractor={(item) => item.id} contentContainerStyle={{ padding: 16 }}
          ListEmptyComponent={<View style={s.empty}><Ionicons name="briefcase-outline" size={64} color="#ccc" /><Text style={s.emptyText}>Nenhuma proposta encontrada</Text></View>} />
      )}

      {/* Filter Picker Modal */}
      <Modal visible={filterPickerVisible} animationType="fade" transparent onRequestClose={() => setFilterPickerVisible(false)}>
        <View style={s.modalOverlay}>
          <View style={[s.modalContent, { maxWidth: 340, alignSelf: 'center' }]}>
            <Text style={s.modalTitle}>Filtrar por Periodo</Text>
            <Text style={s.label}>Ano</Text>
            <View style={s.yearRow}>
              {[2025, 2026, 2027].map(y => (
                <TouchableOpacity key={y} style={[s.yearBtn, filterYear === y && s.yearBtnActive]} onPress={() => setFilterYear(y)}><Text style={[s.yearBtnText, filterYear === y && s.yearBtnTextActive]}>{y}</Text></TouchableOpacity>
              ))}
            </View>
            <Text style={[s.label, { marginTop: 12 }]}>Mes</Text>
            <View style={s.monthGrid}>
              {MONTHS.map(m => (
                <TouchableOpacity key={m.value} style={[s.monthBtn, filterMonth === m.value && s.monthBtnActive]} onPress={() => setFilterMonth(m.value)}><Text style={[s.monthBtnText, filterMonth === m.value && s.monthBtnTextActive]}>{m.label}</Text></TouchableOpacity>
              ))}
            </View>
            <TouchableOpacity style={[s.modalBtn, s.saveBtn, { marginTop: 16 }]} onPress={() => setFilterPickerVisible(false)}><Text style={s.saveText}>Aplicar</Text></TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* P.O. Modal */}
      <Modal visible={poModalVisible} animationType="fade" transparent onRequestClose={() => setPOModalVisible(false)}>
        <View style={s.modalOverlay}>
          <View style={[s.modalContent, { maxWidth: 400, alignSelf: 'center' }]}>
            <Text style={s.modalTitle}>Informar P.O.</Text>
            {poProposal && <View style={{ marginBottom: 16 }}><Text style={s.cardSub}>Proposta: <Text style={{ fontWeight: '700', color: '#000000' }}>{poProposal.numero_proposta}</Text></Text><Text style={s.cardSub}>{poProposal.empresa}</Text></View>}
            <Text style={s.label}>Numero da P.O. *</Text>
            <TextInput style={s.input} placeholder="Ex: PO-2026-001" value={poNumber} onChangeText={setPONumber} autoFocus data-testid="po-number-input" />
            <Text style={s.hintText}>Ao informar a P.O., a proposta sera aprovada e uma O.S. sera criada.</Text>
            <View style={s.modalBtns}>
              <TouchableOpacity style={[s.modalBtn, s.cancelBtn]} onPress={() => setPOModalVisible(false)}><Text style={s.cancelText}>Cancelar</Text></TouchableOpacity>
              <TouchableOpacity style={[s.modalBtn, s.saveBtn, submittingPO && { opacity: 0.6 }]} onPress={handleInformarPO} disabled={submittingPO} data-testid="confirm-po-btn">
                {submittingPO ? <ActivityIndicator size="small" color="#fff" /> : <Text style={s.saveText}>Confirmar</Text>}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Create/Edit Modal */}
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
              <TextInput style={s.input} placeholder="email@exemplo.com" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" />

              <Text style={s.label}>Embarcacao / Plataforma</Text>
              <TextInput style={s.input} placeholder="Ex: Plataforma P-71" value={embarcacao} onChangeText={setEmbarcacao} />

              <Text style={s.label}>Local</Text>
              <TextInput style={s.input} placeholder="Ex: Bacia de Santos" value={local} onChangeText={setLocal} data-testid="proposal-local-input" />

              <Text style={s.label}>Equipamento</Text>
              <TextInput style={s.input} placeholder="Ex: Turbina Principal" value={equipamento} onChangeText={setEquipamento} />

              <Text style={s.label}>Servico *</Text>
              <TextInput style={s.input} placeholder="Ex: Reparo de valvulas" value={servico} onChangeText={setServico} data-testid="proposal-servico-input" />

              {/* === INTRO TEXT PREVIEW === */}
              <View style={s.introContainer} data-testid="intro-text-preview">
                <Text style={s.introText}>
                  Prezados,{'\n'}Agradecemos a consulta e temos o prazer de apresentar nossa proposta comercial para o servico de{' '}
                  <Text style={s.introBold}>{servico || '____________________'}</Text>
                  {' '}a ser realizado na(o){' '}
                  <Text style={s.introBold}>{embarcacao || '____________________'}</Text>.
                </Text>
              </View>

              {/* === INDICE === */}
              <View style={s.indexSection} data-testid="proposal-index">
                <Text style={s.indexTitle}>Indice da Proposta</Text>
                <View style={s.indexList}>
                  {itens.map((item, idx) => (
                    <View key={item.id}>
                      <View style={s.indexItem}>
                        <View style={s.indexNumBadge}><Text style={s.indexNumText}>{idx + 1}</Text></View>
                        <Text style={s.indexItemText} numberOfLines={1}>{item.titulo || '(sem titulo)'}</Text>
                      </View>
                      {(item.subsections || []).map((sub, subIdx) => (
                        <View key={sub.id} style={[s.indexItem, { marginLeft: 24 }]}>
                          <View style={[s.indexNumBadge, { width: 28, height: 20, borderRadius: 10, backgroundColor: '#5C6BC0' }]}>
                            <Text style={[s.indexNumText, { fontSize: 9 }]}>{idx + 1}.{subIdx + 1}</Text>
                          </View>
                          <Text style={[s.indexItemText, { fontSize: 13, color: '#555' }]} numberOfLines={1}>{sub.titulo || '(sem titulo)'}</Text>
                        </View>
                      ))}
                    </View>
                  ))}
                  <View style={s.indexItem}>
                    <View style={[s.indexNumBadge, { backgroundColor: '#546E7A' }]}><Text style={s.indexNumText}>{termosNumber}</Text></View>
                    <Text style={[s.indexItemText, { fontStyle: 'italic', color: '#546E7A' }]}>Termos e Condicoes Gerais</Text>
                  </View>
                  {itens.length === 0 && <Text style={{ color: '#999', fontSize: 12, fontStyle: 'italic', marginTop: 4 }}>Adicione secoes ao escopo abaixo</Text>}
                </View>
              </View>

              {/* === ESCOPO SECTIONS === */}
              <View style={s.itemsHeader}>
                <Text style={s.sectionTitle}>Escopo dos Servicos</Text>
                <TouchableOpacity onPress={addItem} style={s.addItemBtn} data-testid="add-item-btn">
                  <Ionicons name="add-circle" size={28} color="#000000" />
                </TouchableOpacity>
              </View>

              {itens.map((item, idx) => {
                const sectionKey = String(idx);
                const isExpanded = expandedSection === item.id;
                return (
                  <View key={item.id} style={s.sectionCard}>
                    <TouchableOpacity style={s.sectionHeader} onPress={() => setExpandedSection(isExpanded ? null : item.id)}>
                      <View style={s.sectionNumBadge}><Text style={s.sectionNumText}>{idx + 1}</Text></View>
                      <Text style={s.sectionLabel} numberOfLines={1}>{item.titulo || `Secao ${idx + 1}`}</Text>
                      <View style={{ flex: 1 }} />
                      <TouchableOpacity onPress={() => moveItem(idx, 'up')} disabled={idx === 0} style={{ opacity: idx === 0 ? 0.3 : 1, padding: 4 }}><Ionicons name="arrow-up" size={18} color="#000000" /></TouchableOpacity>
                      <TouchableOpacity onPress={() => moveItem(idx, 'down')} disabled={idx === itens.length - 1} style={{ opacity: idx === itens.length - 1 ? 0.3 : 1, padding: 4 }}><Ionicons name="arrow-down" size={18} color="#000000" /></TouchableOpacity>
                      <TouchableOpacity onPress={() => removeItem(idx)} style={{ padding: 4 }} data-testid={`remove-item-${idx}`}><Ionicons name="close-circle" size={22} color="#d32f2f" /></TouchableOpacity>
                      <Ionicons name={isExpanded ? 'chevron-up' : 'chevron-down'} size={20} color="#000000" style={{ marginLeft: 4 }} />
                    </TouchableOpacity>

                    {isExpanded && (
                      <View style={{ marginTop: 8 }}>
                        <TextInput style={s.input} placeholder="Titulo da secao *" value={item.titulo} onChangeText={(v) => updateItem(idx, 'titulo', v)} data-testid={`item-titulo-${idx}`} />
                        <TextInput style={[s.input, { minHeight: 80, textAlignVertical: 'top' }]} placeholder="Descricao detalhada do escopo" value={item.descricao} onChangeText={(v) => updateItem(idx, 'descricao', v)} multiline data-testid={`item-descricao-${idx}`} />
                        <TextInput style={s.input} placeholder="Valor (R$)" value={item.valor ? String(item.valor) : ''} onChangeText={(v) => updateItem(idx, 'valor', parseFloat(v) || 0)} keyboardType="numeric" data-testid={`item-valor-${idx}`} />

                        {/* Section-level photos */}
                        {editingProposal && renderPhotoArea(sectionKey, idx)}
                        {!editingProposal && <Text style={s.hintText}>Salve a proposta primeiro para adicionar fotos</Text>}

                        {/* === SUBSECTIONS === */}
                        {(item.subsections || []).map((sub, subIdx) => {
                          const subKey = `${idx}.${subIdx}`;
                          return (
                            <View key={sub.id} style={s.subsectionCard}>
                              <View style={s.subsectionHeader}>
                                <View style={[s.sectionNumBadge, { width: 30, height: 22, backgroundColor: '#5C6BC0' }]}>
                                  <Text style={[s.sectionNumText, { fontSize: 10 }]}>{idx + 1}.{subIdx + 1}</Text>
                                </View>
                                <Text style={s.subsectionLabel}>Subsecao {idx + 1}.{subIdx + 1}</Text>
                                <View style={{ flex: 1 }} />
                                <TouchableOpacity onPress={() => removeSubsection(idx, subIdx)} style={{ padding: 4 }} data-testid={`remove-sub-${idx}-${subIdx}`}>
                                  <Ionicons name="close-circle" size={20} color="#d32f2f" />
                                </TouchableOpacity>
                              </View>
                              <TextInput
                                style={s.input}
                                placeholder="Titulo da subsecao"
                                value={sub.titulo}
                                onChangeText={(v) => updateSubsection(idx, subIdx, 'titulo', v)}
                                data-testid={`sub-titulo-${idx}-${subIdx}`}
                              />
                              <TextInput
                                style={[s.input, { minHeight: 60, textAlignVertical: 'top' }]}
                                placeholder="Descricao"
                                value={sub.descricao}
                                onChangeText={(v) => updateSubsection(idx, subIdx, 'descricao', v)}
                                multiline
                                data-testid={`sub-descricao-${idx}-${subIdx}`}
                              />
                              {/* Subsection photos */}
                              {editingProposal && renderPhotoArea(subKey, idx)}
                            </View>
                          );
                        })}

                        <TouchableOpacity style={s.addSubBtn} onPress={() => addSubsection(idx)} data-testid={`add-subsection-${idx}`}>
                          <Ionicons name="add-circle-outline" size={20} color="#5C6BC0" />
                          <Text style={s.addSubBtnText}>Adicionar Subsecao</Text>
                        </TouchableOpacity>
                      </View>
                    )}
                  </View>
                );
              })}

              {itens.length > 0 && (
                <View style={s.totalRow}>
                  <Text style={s.totalLabel}>Total:</Text>
                  <Text style={s.totalValue}>{formatCurrency(calcTotal(itens))}</Text>
                </View>
              )}

              {/* === TERMOS GERAIS === */}
              <TouchableOpacity style={s.termosToggle} onPress={() => setShowTermos(!showTermos)} data-testid="termos-toggle">
                <View style={[s.sectionNumBadge, { backgroundColor: '#546E7A' }]}><Text style={s.sectionNumText}>{termosNumber}</Text></View>
                <Text style={s.termosToggleText}>Termos e Condicoes Gerais</Text>
                <Ionicons name={showTermos ? 'chevron-up' : 'chevron-down'} size={20} color="#546E7A" />
              </TouchableOpacity>
              {showTermos && (
                <View style={s.termosContainer}>
                  <TextInput
                    style={[s.input, { minHeight: 260, textAlignVertical: 'top', fontSize: 12, lineHeight: 18 }]}
                    value={termosGerais}
                    onChangeText={setTermosGerais}
                    multiline
                    data-testid="termos-gerais-input"
                  />
                  <TouchableOpacity onPress={() => setTermosGerais(DEFAULT_TERMOS)} style={s.resetTermosBtn}>
                    <Ionicons name="refresh" size={16} color="#000000" />
                    <Text style={{ color: '#000000', fontSize: 12, fontWeight: '600' }}>Restaurar texto padrao</Text>
                  </TouchableOpacity>
                </View>
              )}

              <Text style={[s.label, { marginTop: 16 }]}>Observacoes</Text>
              <TextInput style={[s.input, { minHeight: 80, textAlignVertical: 'top' }]} placeholder="Observacoes gerais" value={observacoes} onChangeText={setObservacoes} multiline data-testid="proposal-observacoes-input" />

              <View style={s.modalBtns}>
                <TouchableOpacity style={[s.modalBtn, s.cancelBtn]} onPress={() => { setModalVisible(false); resetForm(); }}><Text style={s.cancelText}>Cancelar</Text></TouchableOpacity>
                <TouchableOpacity style={[s.modalBtn, s.saveBtn]} onPress={handleSave} data-testid="save-proposal-btn"><Text style={s.saveText}>Salvar</Text></TouchableOpacity>
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
  title: { fontSize: 20, fontWeight: '600', color: '#000000' },
  addBtn: { backgroundColor: '#2e7d32', width: 40, height: 40, borderRadius: 20, justifyContent: 'center', alignItems: 'center' },
  filterBar: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 10, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#e8e8e8' },
  filterBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: '#F0F0F0', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8 },
  filterLabel: { fontSize: 14, fontWeight: '600', color: '#000000' },
  statsRow: { flexDirection: 'row', gap: 8 },
  statBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  statText: { fontSize: 12, fontWeight: '600' },
  card: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.1, shadowRadius: 2, elevation: 2 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  headerRight: { alignItems: 'flex-end', gap: 4 },
  numberBadge: { backgroundColor: '#000000', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 6 },
  numberText: { color: '#fff', fontSize: 13, fontWeight: '700' },
  statusBadge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 10 },
  statusText: { fontSize: 11, fontWeight: '700' },
  dateText: { fontSize: 12, color: '#999' },
  cardTitle: { fontSize: 16, fontWeight: '600', color: '#212121', marginBottom: 4 },
  cardSub: { fontSize: 13, color: '#666', marginBottom: 2 },
  cardTotal: { fontSize: 14, fontWeight: '700', color: '#2e7d32', marginTop: 8 },
  approvedInfo: { marginTop: 8, paddingTop: 8, borderTopWidth: 1, borderTopColor: '#e8e8e8', gap: 4 },
  infoRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  infoText: { fontSize: 13, fontWeight: '600', color: '#333' },
  poBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, backgroundColor: '#ff6f00', paddingVertical: 10, borderRadius: 8, marginTop: 12 },
  poBtnText: { color: '#fff', fontSize: 14, fontWeight: '700' },
  pdfRow: { flexDirection: 'row', gap: 8, marginTop: 10 },
  pdfBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, paddingVertical: 10, borderRadius: 8 },
  pdfBtnText: { color: '#fff', fontSize: 13, fontWeight: '600' },
  cardActions: { flexDirection: 'row', gap: 8, marginTop: 8, justifyContent: 'flex-end' },
  actionBtn: { padding: 8 },
  empty: { alignItems: 'center', paddingVertical: 64 },
  emptyText: { fontSize: 16, color: '#999', marginTop: 16 },
  hintText: { fontSize: 12, color: '#888', marginTop: 4, fontStyle: 'italic' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', padding: 16 },
  modalContent: { backgroundColor: '#fff', borderRadius: 16, padding: 24, maxHeight: '95%' },
  modalTitle: { fontSize: 20, fontWeight: '600', color: '#000000', marginBottom: 16 },
  label: { fontSize: 14, fontWeight: '600', color: '#212121', marginBottom: 6, marginTop: 10 },
  input: { backgroundColor: '#f5f5f5', borderRadius: 8, padding: 14, fontSize: 15, borderWidth: 1, borderColor: '#e0e0e0', marginBottom: 4 },
  // Intro
  introContainer: { backgroundColor: '#FFF8E1', borderRadius: 10, padding: 14, marginTop: 12, borderWidth: 1, borderColor: '#FFE082' },
  introText: { fontSize: 13, color: '#555', lineHeight: 20 },
  introBold: { fontWeight: '700', color: '#000000' },
  // Index
  indexSection: { backgroundColor: '#F0F0F0', borderRadius: 10, padding: 14, marginTop: 16, borderWidth: 1, borderColor: '#d0d0d0' },
  indexTitle: { fontSize: 15, fontWeight: '700', color: '#000000', marginBottom: 10 },
  indexList: { gap: 6 },
  indexItem: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  indexNumBadge: { backgroundColor: '#000000', width: 24, height: 24, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  indexNumText: { color: '#fff', fontSize: 11, fontWeight: '700' },
  indexItemText: { fontSize: 14, color: '#333', flex: 1, fontWeight: '500' },
  // Section
  itemsHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 20, marginBottom: 8 },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: '#000000' },
  addItemBtn: { padding: 4 },
  sectionCard: { backgroundColor: '#fff', borderRadius: 10, padding: 12, marginBottom: 10, borderWidth: 1, borderColor: '#d0d0d0' },
  sectionHeader: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  sectionNumBadge: { backgroundColor: '#000000', width: 26, height: 26, borderRadius: 13, justifyContent: 'center', alignItems: 'center' },
  sectionNumText: { color: '#fff', fontSize: 12, fontWeight: '700' },
  sectionLabel: { fontSize: 13, fontWeight: '600', color: '#000000', maxWidth: '40%' },
  // Subsection
  subsectionCard: { backgroundColor: '#f8f9ff', borderRadius: 8, padding: 10, marginTop: 8, marginLeft: 8, borderWidth: 1, borderColor: '#D1D5F0', borderLeftWidth: 3, borderLeftColor: '#5C6BC0' },
  subsectionHeader: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 6 },
  subsectionLabel: { fontSize: 12, fontWeight: '600', color: '#5C6BC0' },
  addSubBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 8, paddingHorizontal: 12, marginTop: 8, backgroundColor: '#EDE7F6', borderRadius: 8, alignSelf: 'flex-start' },
  addSubBtnText: { fontSize: 13, fontWeight: '500', color: '#5C6BC0' },
  // Photos
  photosArea: { marginTop: 8, paddingTop: 8, borderTopWidth: 1, borderTopColor: '#e8e8e8' },
  photoItem: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 6, backgroundColor: '#f5f5f5', borderRadius: 8, padding: 6 },
  photoThumb: { width: 48, height: 48, borderRadius: 6, backgroundColor: '#ddd' },
  photoName: { flex: 1, fontSize: 12, color: '#333' },
  photoDeleteBtn: { padding: 6 },
  uploadBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 8, paddingHorizontal: 12, backgroundColor: '#f0f0f0', borderRadius: 8, alignSelf: 'flex-start', marginTop: 6 },
  uploadBtnText: { fontSize: 13, fontWeight: '500', color: '#000000' },
  // Total
  totalRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 12, paddingVertical: 10, backgroundColor: '#F0F0F0', borderRadius: 8, marginTop: 8 },
  totalLabel: { fontSize: 15, fontWeight: '700', color: '#000000' },
  totalValue: { fontSize: 15, fontWeight: '700', color: '#2e7d32' },
  // Termos
  termosToggle: { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: '#ECEFF1', borderRadius: 10, padding: 12, marginTop: 16, borderWidth: 1, borderColor: '#B0BEC5' },
  termosToggleText: { flex: 1, fontSize: 14, fontWeight: '600', color: '#546E7A' },
  termosContainer: { marginTop: 4, marginBottom: 8 },
  resetTermosBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, alignSelf: 'flex-end', padding: 8, marginTop: 4 },
  // Buttons
  modalBtns: { flexDirection: 'row', gap: 12, marginTop: 24, marginBottom: 16 },
  modalBtn: { flex: 1, height: 48, borderRadius: 8, justifyContent: 'center', alignItems: 'center' },
  cancelBtn: { backgroundColor: '#f5f5f5' },
  cancelText: { color: '#666', fontSize: 16, fontWeight: '600' },
  saveBtn: { backgroundColor: '#000000' },
  saveText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  yearRow: { flexDirection: 'row', gap: 8 },
  yearBtn: { flex: 1, paddingVertical: 10, borderRadius: 8, backgroundColor: '#f5f5f5', alignItems: 'center' },
  yearBtnActive: { backgroundColor: '#000000' },
  yearBtnText: { fontSize: 15, fontWeight: '600', color: '#666' },
  yearBtnTextActive: { color: '#fff' },
  monthGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 4 },
  monthBtn: { width: '22%', paddingVertical: 8, borderRadius: 6, backgroundColor: '#f5f5f5', alignItems: 'center' },
  monthBtnActive: { backgroundColor: '#000000' },
  monthBtnText: { fontSize: 13, fontWeight: '600', color: '#666' },
  monthBtnTextActive: { color: '#fff' },
});
