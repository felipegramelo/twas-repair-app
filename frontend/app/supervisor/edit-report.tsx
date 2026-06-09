import React, { useState, useEffect, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, TextInput, ActivityIndicator, Platform, Modal, Image, Alert } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { reportAPI } from '../../services/api';
import { BACKEND_URL } from '../../services/config';
import { buildPdfFilename } from '../../utils/pdfHelper';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as ImagePicker from 'expo-image-picker';
import * as DocumentPicker from 'expo-document-picker';
import { downloadAndSharePDF } from '../../utils/pdfHelper';

interface Section {
  key: string; number: string; title: string; content: string; enabled: boolean; subsections: Section[];
}
interface Photo {
  id: string; section_key: string; storage_path: string; original_filename: string; caption?: string;
}

const NO_PHOTO_SECTIONS = ['introduction', 'equipment', 'objective', 'service_description', 'daily_activities', 'observations', 'disassembly', 'assembly', 'ndt'];
const NO_BULLET_SECTIONS = ['introduction', 'equipment', 'objective'];
const NO_TEXT_SECTIONS = ['ndt'];
const IMAGE_ONLY_SECTIONS = ['pressure_test', 'certificate', 'propeller_shaft', 'pinion_shaft', 'input_shaft', 'coupling', 'swivel_pinion', 'propeller', 'reduction_gear'];
const PDF_UPLOAD_SECTIONS = new Set(['ndt', 'pressure_test', 'certificate']);
const isPhotoOnlySection = (key: string) => key.endsWith('_photos') || key.includes('fotos') || IMAGE_ONLY_SECTIONS.includes(key);
const showMsg = (msg: string) => { if (Platform.OS === 'web') window.alert(msg); else Alert.alert('Aviso', msg); };

const PlainTextArea = ({ value, onChangeText, placeholder, style: cs }: { value: string; onChangeText: (t: string) => void; placeholder?: string; style?: any; }) => {
  if (Platform.OS === 'web') {
    return <textarea value={value} onChange={(e: any) => onChangeText(e.target.value)} placeholder={placeholder}
      style={{ width: '100%', minHeight: 100, padding: 12, fontSize: 14, borderRadius: 10, border: '1px solid #e0e0e0', backgroundColor: '#f8f9fa', color: '#333', fontFamily: 'inherit', lineHeight: '1.6', resize: 'vertical', boxSizing: 'border-box', ...(cs || {}) }} />;
  }
  return <TextInput style={[{ backgroundColor: '#f8f9fa', borderRadius: 10, borderWidth: 1, borderColor: '#e0e0e0', padding: 12, fontSize: 14, color: '#333', minHeight: 100 }, cs]} value={value} onChangeText={onChangeText} placeholder={placeholder} multiline textAlignVertical="top" />;
};

const BulletTextArea = ({ value, onChangeText, placeholder, style: cs }: { value: string; onChangeText: (t: string) => void; placeholder?: string; style?: any; }) => {
  const ensureBullet = (v: string) => {
    if (!v) return '• ';
    if (!v.startsWith('• ')) return '• ' + v;
    return v;
  };
  if (Platform.OS === 'web') {
    const handleKeyDown = (e: any) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const ta = e.target; const s = ta.selectionStart; const end = ta.selectionEnd;
        const nv = ta.value.substring(0, s) + '\n• ' + ta.value.substring(end);
        onChangeText(nv);
        setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + 3; }, 0);
      }
    };
    const handleFocus = (e: any) => {
      if (!e.target.value || !e.target.value.startsWith('• ')) {
        const nv = ensureBullet(e.target.value);
        onChangeText(nv);
        setTimeout(() => { e.target.selectionStart = e.target.selectionEnd = nv.length; }, 0);
      }
    };
    return <textarea value={value} onChange={(e: any) => onChangeText(e.target.value)} onKeyDown={handleKeyDown} onFocus={handleFocus} placeholder={placeholder}
      style={{ width: '100%', minHeight: 100, padding: 12, fontSize: 13, borderRadius: 10, border: '1px solid #e0e0e0', backgroundColor: '#f8f9fa', color: '#333', fontFamily: 'inherit', lineHeight: '1.6', resize: 'vertical', boxSizing: 'border-box', ...(cs || {}) }} />;
  }
  // Native: auto-add bullets on new lines (Enter key)
  const handleNativeChange = (newText: string) => {
    const currentValue = value || '';
    const isAddition = newText.length >= currentValue.length;

    // Ensure first bullet
    if (!newText.startsWith('• ')) {
      newText = '• ' + newText;
    }

    // On addition, add bullets after newlines that don't have them
    if (isAddition) {
      newText = newText.replace(/\n(?!• )/g, '\n• ');
    }

    onChangeText(newText);
  };

  return <TextInput style={[{ backgroundColor: '#f8f9fa', borderRadius: 10, borderWidth: 1, borderColor: '#e0e0e0', padding: 12, fontSize: 13, color: '#333', minHeight: 100 }, cs]} value={value} onChangeText={handleNativeChange} onFocus={() => { if (!value || !value.startsWith('• ')) onChangeText(ensureBullet(value || '')); }} placeholder={placeholder} multiline textAlignVertical="top" />;
};

const SectionTextArea = ({ sectionKey, value, onChangeText, placeholder, style }: { sectionKey: string; value: string; onChangeText: (t: string) => void; placeholder?: string; style?: any; }) => {
  if (NO_BULLET_SECTIONS.includes(sectionKey)) {
    return <PlainTextArea value={value} onChangeText={onChangeText} placeholder={placeholder} style={style} />;
  }
  return <BulletTextArea value={value} onChangeText={onChangeText} placeholder={placeholder} style={style} />;
};

export default function EditReportScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [report, setReport] = useState<any>(null);
  const [sections, setSections] = useState<Section[]>([]);
  const [periodoInicio, setPeriodoInicio] = useState('');
  const [periodoFim, setPeriodoFim] = useState('');
  const [executadoPor, setExecutadoPor] = useState('');
  const [ocWo, setOcWo] = useState('');
  const [representanteTwas, setRepresentanteTwas] = useState('');
  const [representanteCliente, setRepresentanteCliente] = useState('');
  const [showSectionsModal, setShowSectionsModal] = useState(false);
  const [editingSection, setEditingSection] = useState<string | null>(null);
  const [addingSectionTitle, setAddingSectionTitle] = useState('');
  const [addingSubsectionTitle, setAddingSubsectionTitle] = useState<Record<string, string>>({});
  const [showAddSubsection, setShowAddSubsection] = useState<string | null>(null);
  const [customSectionMode, setCustomSectionMode] = useState<Record<string, Set<string>>>({});
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [uploading, setUploading] = useState<string | null>(null);
  const [token, setToken] = useState('');
  const [captions, setCaptions] = useState<Record<string, string>>({});
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [currentUploadSection, setCurrentUploadSection] = useState('cover');
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfSuccess, setPdfSuccess] = useState(false);
  const [dailyEntries, setDailyEntries] = useState<Array<{id: string; date: string; description: string}>>([]);
  const [expandedDay, setExpandedDay] = useState<string | null>(null);
  const [pdfSelectedDays, setPdfSelectedDays] = useState<Set<string>>(new Set());
  const [hiddenTextAreas, setHiddenTextAreas] = useState<Set<string>>(new Set());

  useEffect(() => { loadReport(); AsyncStorage.getItem('token').then(t => t && setToken(t)); }, []);

  const loadReport = async () => {
    try {
      const [data, photosData] = await Promise.all([reportAPI.getById(id!), reportAPI.getPhotos(id!)]);
      setReport(data); setPeriodoInicio(data.periodo_inicio || ''); setPeriodoFim(data.periodo_fim || '');
      setExecutadoPor(data.executado_por || ''); setOcWo(data.oc_wo || ''); setSections(data.sections || []); setPhotos(photosData);
      setRepresentanteTwas(data.representante_twas || ''); setRepresentanteCliente(data.representante_cliente || '');
      setDailyEntries(data.daily_entries || []);
      setPdfSelectedDays(new Set((data.daily_entries || []).map((e: any) => e.id)));
      // Initialize captions from backend data
      const initialCaptions: Record<string, string> = {};
      photosData.forEach((p: any) => { if (p.caption) initialCaptions[p.id] = p.caption; });
      setCaptions(initialCaptions);
    } catch { showMsg('Erro ao carregar relatório'); } finally { setLoading(false); }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // Save all edited captions first
      const captionPromises = Object.entries(captions).map(([photoId, caption]) =>
        reportAPI.updateCaption(id!, photoId, caption)
      );
      await Promise.all(captionPromises);
      await reportAPI.update(id!, { periodo_inicio: periodoInicio, periodo_fim: periodoFim, executado_por: executadoPor, oc_wo: ocWo, representante_twas: representanteTwas, representante_cliente: representanteCliente, sections, daily_entries: dailyEntries });
      showMsg('Relatório salvo com sucesso!'); router.push('/supervisor');
    } catch (e: any) { showMsg('Erro ao salvar: ' + (e.message || '')); } finally { setSaving(false); }
  };

  const getPdfUrl = () => {
    const baseUrl = BACKEND_URL || process.env.EXPO_PUBLIC_REPORT_API_URL?.replace('/api', '');
    // Token included for web (window.open needs it in URL). On native, pdfHelper adds it if missing.
    return `${baseUrl}/api/reports/${id}/pdf?token=${encodeURIComponent(token)}&t=${Date.now()}`;
  };

  const handleOpenPDF = async () => {
    let url = getPdfUrl();
    if (report?.report_type === 'daily' && pdfSelectedDays.size > 0) {
      const dayIds = Array.from(pdfSelectedDays).join(',');
      url += `&day_ids=${encodeURIComponent(dayIds)}`;
    }
    if (Platform.OS === 'web') {
      window.open(url, '_blank');
      setPdfSuccess(true);
      setTimeout(() => setPdfSuccess(false), 4000);
    } else {
      setPdfLoading(true);
      try {
        const fileName = buildPdfFilename('REL', report?.os_number, report?.client, report?.service);
        await downloadAndSharePDF(
          () => reportAPI.downloadPDF(id!),
          url,
          fileName,
        );
        setPdfSuccess(true);
        setTimeout(() => setPdfSuccess(false), 4000);
      } catch (e: any) {
        showMsg('Erro ao abrir PDF: ' + (e.message || ''));
      } finally {
        setPdfLoading(false);
      }
    }
  };

  const handleSharePDF = async () => {
    const url = getPdfUrl();
    if (Platform.OS === 'web') {
      window.location.href = url;
    } else {
      try {
        const fileName = buildPdfFilename('REL', report?.os_number, report?.client, report?.service);
        await downloadAndSharePDF(
          () => reportAPI.downloadPDF(id!),
          url,
          fileName,
        );
      } catch (e: any) {
        showMsg('Erro ao compartilhar PDF: ' + (e.message || ''));
      }
    }
  };

  const triggerFileUpload = async (sectionKey: string) => {
    setCurrentUploadSection(sectionKey);
    if (Platform.OS === 'web') {
      if (fileInputRef.current) fileInputRef.current.click();
    } else {
      // iOS/Android native: show action sheet with camera/library/file options
      const isPDF = PDF_UPLOAD_SECTIONS.has(sectionKey);

      if (isPDF) {
        // For PDF sections, show document picker directly (accepts images + PDFs)
        try {
          const result = await DocumentPicker.getDocumentAsync({ type: ['image/*', 'application/pdf'], multiple: true });
          if (!result.canceled && result.assets) {
            setUploading(sectionKey);
            for (const asset of result.assets) {
              const file = { uri: asset.uri, name: asset.name, type: asset.mimeType || 'application/octet-stream' };
              await reportAPI.uploadPhoto(id!, file as any, sectionKey, asset.name);
            }
            setPhotos(await reportAPI.getPhotos(id!));
          }
        } catch (e: any) {
          showMsg('Erro ao enviar arquivo: ' + (e.message || ''));
        } finally {
          setUploading(null);
        }
      } else {
        // For image sections: show action sheet with Camera / Photo Library / File options
        Alert.alert(
          'Adicionar Imagem',
          'Escolha a origem da imagem:',
          [
            {
              text: 'Tirar Foto',
              onPress: async () => {
                try {
                  const { status } = await ImagePicker.requestCameraPermissionsAsync();
                  if (status !== 'granted') {
                    Alert.alert('Permissão necessária', 'Permita o acesso à câmera nas configurações do app.');
                    return;
                  }
                  const result = await ImagePicker.launchCameraAsync({ mediaTypes: ['images'], quality: 0.8 });
                  if (!result.canceled && result.assets) {
                    setUploading(sectionKey);
                    for (const asset of result.assets) {
                      const name = asset.fileName || `photo_${Date.now()}.jpg`;
                      const file = { uri: asset.uri, name, type: asset.mimeType || 'image/jpeg' };
                      await reportAPI.uploadPhoto(id!, file as any, sectionKey, name);
                    }
                    setPhotos(await reportAPI.getPhotos(id!));
                  }
                } catch (e: any) {
                  showMsg('Erro ao tirar foto: ' + (e.message || ''));
                } finally {
                  setUploading(null);
                }
              },
            },
            {
              text: 'Fototeca',
              onPress: async () => {
                try {
                  const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], allowsMultipleSelection: true, quality: 0.8 });
                  if (!result.canceled && result.assets) {
                    setUploading(sectionKey);
                    for (const asset of result.assets) {
                      const name = asset.fileName || `photo_${Date.now()}.jpg`;
                      const file = { uri: asset.uri, name, type: asset.mimeType || 'image/jpeg' };
                      await reportAPI.uploadPhoto(id!, file as any, sectionKey, name);
                    }
                    setPhotos(await reportAPI.getPhotos(id!));
                  }
                } catch (e: any) {
                  showMsg('Erro ao selecionar foto: ' + (e.message || ''));
                } finally {
                  setUploading(null);
                }
              },
            },
            {
              text: 'Arquivo',
              onPress: async () => {
                try {
                  const result = await DocumentPicker.getDocumentAsync({ type: ['image/*'], multiple: true });
                  if (!result.canceled && result.assets) {
                    setUploading(sectionKey);
                    for (const asset of result.assets) {
                      const file = { uri: asset.uri, name: asset.name, type: asset.mimeType || 'image/jpeg' };
                      await reportAPI.uploadPhoto(id!, file as any, sectionKey, asset.name);
                    }
                    setPhotos(await reportAPI.getPhotos(id!));
                  }
                } catch (e: any) {
                  showMsg('Erro ao selecionar arquivo: ' + (e.message || ''));
                } finally {
                  setUploading(null);
                }
              },
            },
            { text: 'Cancelar', style: 'cancel' },
          ],
        );
      }
    }
  };

  const handleFileSelected = async (event: any) => {
    const files = event.target.files; if (!files || files.length === 0) return;
    setUploading(currentUploadSection);
    try {
      for (let i = 0; i < files.length; i++) {
        await reportAPI.uploadPhoto(id!, files[i], currentUploadSection, files[i].name);
      }
      setPhotos(await reportAPI.getPhotos(id!));
    } catch (e: any) { showMsg('Erro ao enviar arquivo: ' + (e.message || '')); }
    finally { setUploading(null); if (fileInputRef.current) fileInputRef.current.value = ''; }
  };

  const handleDeletePhoto = async (photoId: string) => {
    const doDelete = async () => {
      try { await reportAPI.deletePhoto(id!, photoId); setPhotos(prev => prev.filter(p => p.id !== photoId)); showMsg('Foto excluida'); } catch { showMsg('Erro ao excluir foto'); }
    };
    if (Platform.OS === 'web') {
      if (window.confirm('Excluir esta foto?')) await doDelete();
    } else {
      Alert.alert('Confirmar', 'Excluir esta foto?', [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Excluir', style: 'destructive', onPress: doDelete },
      ]);
    }
  };

  const handleSaveCaption = async (photoId: string) => {
    const caption = captions[photoId];
    if (caption === undefined) return;
    try { await reportAPI.updateCaption(id!, photoId, caption); } catch { showMsg('Erro ao salvar legenda'); }
  };

  const getPhotoUrl = (sp: string) => reportAPI.getPhotoUrl(sp, token);
  const getPhotosForSection = (sk: string) => photos.filter(p => p.section_key === sk);
  const canHavePhotos = (sk: string) => !NO_PHOTO_SECTIONS.includes(sk) || sk.startsWith('daily_');

  const toggleSection = (sectionKey: string) => {
    setSections(prev => prev.map(s => {
      if (s.key === sectionKey) return { ...s, enabled: !s.enabled };
      return { ...s, subsections: s.subsections.map(sub => {
        if (sub.key === sectionKey) return { ...sub, enabled: !sub.enabled };
        return { ...sub, subsections: (sub.subsections || []).map(ss => ss.key === sectionKey ? { ...ss, enabled: !ss.enabled } : ss) };
      })};
    }));
  };

  const updateSectionContent = (sectionKey: string, content: string) => {
    setSections(prev => prev.map(s => {
      if (s.key === sectionKey) return { ...s, content };
      return { ...s, subsections: s.subsections.map(sub => {
        if (sub.key === sectionKey) return { ...sub, content };
        return { ...sub, subsections: (sub.subsections || []).map(ss => ss.key === sectionKey ? { ...ss, content } : ss) };
      })};
    }));
  };

  const updateSectionTitle = (sectionKey: string, title: string) => {
    setSections(prev => prev.map(s => {
      if (s.key === sectionKey) return { ...s, title };
      return { ...s, subsections: s.subsections.map(sub => {
        if (sub.key === sectionKey) return { ...sub, title };
        return { ...sub, subsections: (sub.subsections || []).map(ss => ss.key === sectionKey ? { ...ss, title } : ss) };
      })};
    }));
  };

  const addCustomSection = () => {
    if (!addingSectionTitle.trim()) return;
    const key = `custom_${Date.now()}`;
    setSections(prev => [...prev, { key, number: '', title: addingSectionTitle.trim().toUpperCase(), content: '', enabled: true, subsections: [] }]);
    setAddingSectionTitle('');
    setCustomSectionMode(prev => ({ ...prev, [key]: new Set(['text', 'photos']) }));
  };

  const deleteCustomSection = (sectionKey: string) => {
    const doDelete = () => setSections(prev => prev.filter(s => s.key !== sectionKey));
    if (Platform.OS === 'web') {
      if (window.confirm('Excluir esta seção?')) doDelete();
    } else {
      Alert.alert('Confirmar', 'Excluir esta seção?', [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Excluir', style: 'destructive', onPress: doDelete },
      ]);
    }
  };

  const toggleCustomMode = (sectionKey: string, mode: string) => {
    setCustomSectionMode(prev => {
      const current = prev[sectionKey] || new Set<string>();
      const updated = new Set(current);
      if (updated.has(mode)) updated.delete(mode);
      else updated.add(mode);
      return { ...prev, [sectionKey]: updated };
    });
  };

  const toggleHideTextArea = (key: string) => {
    setHiddenTextAreas(prev => {
      const updated = new Set(prev);
      if (updated.has(key)) updated.delete(key);
      else { updated.add(key); updateSectionContent(key, ''); }
      return updated;
    });
  };

  const togglePlainText = (key: string) => {
    // Find the section content
    const allSections = sections.flatMap(s => [s, ...s.subsections, ...s.subsections.flatMap(sub => sub.subsections || [])]);
    const current = allSections.find(s => s.key === key);
    const content = current?.content || '';
    
    // Check if most lines already have bullets
    const lines = content.split('\n');
    const bulletLines = lines.filter(l => l.startsWith('• ')).length;
    const hasMostBullets = bulletLines > lines.length / 2;
    
    if (hasMostBullets) {
      // Remove ALL bullets
      const cleaned = content.replace(/^• /gm, '');
      updateSectionContent(key, cleaned);
    } else {
      // Add bullets to lines that don't have them
      const bulleted = lines.map(l => l.startsWith('• ') ? l : '• ' + l).join('\n');
      updateSectionContent(key, bulleted);
    }
  };

  const renderTextAreaControls = (sectionKey: string, isHidden: boolean) => {
    // Check actual content for bullet state
    const allSections = sections.flatMap(s => [s, ...s.subsections, ...s.subsections.flatMap(sub => sub.subsections || [])]);
    const current = allSections.find(s => s.key === sectionKey);
    const content = current?.content || '';
    const lines = content.split('\n').filter(l => l.trim().length > 0);
    const bulletLines = lines.filter(l => l.startsWith('• ')).length;
    const hasBullets = lines.length > 0 && bulletLines > lines.length / 2;
    
    return (
      <View style={{ flexDirection: 'row', gap: 8, marginBottom: isHidden ? 0 : 6, marginTop: 4 }}>
        <TouchableOpacity
          onPress={() => toggleHideTextArea(sectionKey)}
          style={{ flexDirection: 'row', alignItems: 'center', paddingVertical: 4, paddingHorizontal: 8, backgroundColor: isHidden ? '#ffebee' : '#e8f5e9', borderRadius: 6 }}
          data-testid={`toggle-text-${sectionKey}`}
        >
          <Ionicons name={isHidden ? 'add-circle-outline' : 'remove-circle-outline'} size={16} color={isHidden ? '#d32f2f' : '#2e7d32'} />
          <Text style={{ fontSize: 11, marginLeft: 4, color: isHidden ? '#d32f2f' : '#2e7d32', fontWeight: '500' }}>
            {isHidden ? 'Adicionar Texto' : 'Remover Texto'}
          </Text>
        </TouchableOpacity>
        {!isHidden && !NO_BULLET_SECTIONS.includes(sectionKey) && (
          <TouchableOpacity
            onPress={() => togglePlainText(sectionKey)}
            style={{ flexDirection: 'row', alignItems: 'center', paddingVertical: 4, paddingHorizontal: 8, backgroundColor: hasBullets ? '#f0f0f0' : '#fff3e0', borderRadius: 6 }}
            data-testid={`toggle-bullets-${sectionKey}`}
          >
            <Ionicons name={hasBullets ? 'list' : 'list-outline'} size={16} color={hasBullets ? '#000000' : '#e65100'} />
            <Text style={{ fontSize: 11, marginLeft: 4, color: hasBullets ? '#000000' : '#e65100', fontWeight: '500' }}>
              {hasBullets ? 'Remover Marcadores' : 'Adicionar Marcadores'}
            </Text>
          </TouchableOpacity>
        )}
      </View>
    );
  };

  const renderSmartTextArea = (sectionKey: string, content: string, placeholder: string) => {
    if (hiddenTextAreas.has(sectionKey)) return null;
    // Always use PlainTextArea - user freely edits text and toggles bullets via button
    return <PlainTextArea value={content} onChangeText={(t) => updateSectionContent(sectionKey, t)} placeholder={placeholder} />;
  };

  const addSubsection = (parentKey: string) => {
    const title = (addingSubsectionTitle[parentKey] || '').trim();
    if (!title) return;
    setSections(prev => prev.map(s => {
      if (s.key === parentKey) {
        return { ...s, subsections: [...s.subsections, { key: `sub_${Date.now()}`, number: '', title: title.toUpperCase(), content: '', enabled: true, subsections: [] }] };
      }
      return { ...s, subsections: s.subsections.map(sub => {
        if (sub.key === parentKey) {
          return { ...sub, subsections: [...(sub.subsections || []), { key: `subsub_${Date.now()}`, number: '', title: title.toUpperCase(), content: '', enabled: true, subsections: [] }] };
        }
        return sub;
      })};
    }));
    setAddingSubsectionTitle(prev => ({ ...prev, [parentKey]: '' }));
    setShowAddSubsection(null);
  };

  const getDisplayNumber = (secs: Section[]): Map<string, string> => {
    const map = new Map<string, string>(); let mi = 0;
    for (const s of secs) { if (!s.enabled) continue; mi++; map.set(s.key, String(mi)); let si = 0;
      for (const sub of s.subsections) { if (!sub.enabled) continue; si++; map.set(sub.key, `${mi}.${si}`); let ssi = 0;
        for (const ss of (sub.subsections || [])) { if (!ss.enabled) continue; ssi++; map.set(ss.key, `${mi}.${si}.${ssi}`); }
      }
    }; return map;
  };

  const numberMap = getDisplayNumber(sections);
  const enabledCount = sections.filter(s => s.enabled).length;

  const htmlDateToBR = (h: string): string => { if (!h) return ''; const [y, m, d] = h.split('-'); return `${d}/${m}/${y}`; };
  const brDateToHtml = (b: string): string => { if (!b || b.length < 10) return ''; const [d, m, y] = b.split('/'); return `${y}-${m}-${d}`; };

  const renderPhotoGrid = (sectionKey: string, isPhotoOnly: boolean = false) => {
    if (!canHavePhotos(sectionKey) && !isPhotoOnly) return null;
    const sp = getPhotosForSection(sectionKey);
    return (
      <View style={styles.photoArea}>
        {!isPhotoOnly && <View style={styles.photoHeader}><Ionicons name="camera-outline" size={16} color="#000000" /><Text style={styles.photoHeaderText}>Fotos ({sp.length})</Text></View>}
        {sp.length > 0 && (
          <View style={styles.photoGridRow}>
            {sp.map(photo => (
              <View key={photo.id} style={styles.photoGridItem}>
                <View style={styles.photoImageWrapper}>
                  {token ? <Image source={{ uri: getPhotoUrl(photo.storage_path) }} style={styles.gridPhoto} resizeMode="cover" /> : <View style={[styles.gridPhoto, styles.photoPlaceholder]}><Ionicons name="image-outline" size={32} color="#999" /></View>}
                  <TouchableOpacity style={styles.photoDeleteBtn} onPress={() => handleDeletePhoto(photo.id)}><Ionicons name="close-circle" size={22} color="#d32f2f" /></TouchableOpacity>
                </View>
                <TextInput style={styles.captionInput} value={captions[photo.id] !== undefined ? captions[photo.id] : (photo.caption || '')} onChangeText={(t) => setCaptions(prev => ({ ...prev, [photo.id]: t }))} onBlur={() => handleSaveCaption(photo.id)} placeholder="Legenda..." multiline />
              </View>
            ))}
          </View>
        )}
        <TouchableOpacity style={styles.uploadBtn} onPress={() => triggerFileUpload(sectionKey)} disabled={uploading === sectionKey}>
          {uploading === sectionKey ? <ActivityIndicator size="small" color="#000000" /> : <><Ionicons name="cloud-upload-outline" size={18} color="#000000" /><Text style={styles.uploadBtnText}>Adicionar Foto</Text></>}
        </TouchableOpacity>
      </View>
    );
  };

  if (loading) return <SafeAreaView style={styles.container}><ActivityIndicator size="large" color="#000000" style={{ marginTop: 100 }} /></SafeAreaView>;
  if (!report) return <SafeAreaView style={styles.container}><Text style={{ padding: 20, textAlign: 'center' }}>Relatório não encontrado</Text></SafeAreaView>;

  const coverPhotos = getPhotosForSection('cover');

  return (
    <SafeAreaView style={styles.container}>
      {Platform.OS === 'web' && <input ref={fileInputRef as any} type="file" accept="image/*,application/pdf" multiple style={{ display: 'none' }} onChange={handleFileSelected} />}
      <View style={styles.innerContainer}>
        <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={true}>
          {/* Header */}
          <TouchableOpacity onPress={() => router.back()} style={styles.backRow}>
            <Ionicons name="arrow-back" size={22} color="#000000" />
            <Text style={styles.backText}>Voltar</Text>
          </TouchableOpacity>

          {/* Service Info */}
          <View style={styles.serviceInfo}>
            <View style={styles.serviceRow}>
              <Ionicons name="construct-outline" size={18} color="#666" />
              <Text style={styles.serviceText} numberOfLines={1}>{report.os_number}</Text>
            </View>
          </View>

          {/* Cover Photo */}
          <View style={styles.card}>
            <Text style={styles.cardLabel}>{report.service || 'Serviço'}</Text>
            {coverPhotos.length > 0 ? (
              <View>
                {coverPhotos.map(p => (
                  <View key={p.id} style={styles.coverPhotoWrapper}>
                    {token ? <Image source={{ uri: getPhotoUrl(p.storage_path) }} style={styles.coverPhoto} resizeMode="cover" /> : <View style={[styles.coverPhoto, styles.photoPlaceholder]}><Ionicons name="image-outline" size={40} color="#999" /></View>}
                    <TouchableOpacity style={styles.coverDeleteBtn} onPress={() => handleDeletePhoto(p.id)}><Ionicons name="trash-outline" size={16} color="#fff" /></TouchableOpacity>
                  </View>
                ))}
                <Text style={styles.vesselLabel}>{report.location || 'Embarcação'}</Text>
                <TouchableOpacity style={styles.uploadBtn} onPress={() => triggerFileUpload('cover')} disabled={uploading === 'cover'}>
                  {uploading === 'cover' ? <ActivityIndicator size="small" color="#000000" /> : <><Ionicons name="cloud-upload-outline" size={18} color="#000000" /><Text style={styles.uploadBtnText}>Trocar Foto</Text></>}
                </TouchableOpacity>
              </View>
            ) : (
              <View>
                <TouchableOpacity style={styles.coverUploadArea} onPress={() => triggerFileUpload('cover')} disabled={uploading === 'cover'}>
                  {uploading === 'cover' ? <ActivityIndicator size="large" color="#000000" /> : <><Ionicons name="image-outline" size={48} color="#c0c0c0" /><Text style={styles.coverUploadText}>Toque para adicionar foto da capa</Text></>}
                </TouchableOpacity>
                <Text style={styles.vesselLabel}>{report.location || 'Embarcação'}</Text>
              </View>
            )}
          </View>

          {/* PDF Action Buttons */}
          {pdfSuccess && (
            <View style={{ backgroundColor: '#e8f5e9', padding: 12, borderRadius: 8, marginBottom: 8, flexDirection: 'row', alignItems: 'center' }} data-testid="pdf-success-toast">
              <Ionicons name="checkmark-circle" size={20} color="#4caf50" />
              <Text style={{ color: '#2e7d32', fontSize: 14, fontWeight: '500', marginLeft: 8 }}>PDF aberto com sucesso!</Text>
            </View>
          )}
          <TouchableOpacity style={[styles.pdfOutlinedBtn, pdfLoading && { opacity: 0.6 }]} onPress={handleOpenPDF} disabled={pdfLoading}>
            {pdfLoading ? <ActivityIndicator size="small" color="#000000" /> : <><Ionicons name="eye-outline" size={20} color="#000000" /><Text style={styles.pdfOutlinedText}>Visualizar PDF</Text></>}
          </TouchableOpacity>

          {/* Campo OC/WO (opcional) */}
          <View style={{ marginBottom: 12 }}>
            <Text style={{ fontSize: 13, fontWeight: '600', color: '#444', marginBottom: 4 }}>OC / WO (opcional)</Text>
            <TextInput style={[styles.textInput, { height: 40 }]} value={ocWo} onChangeText={setOcWo} placeholder="Ex: 12345" placeholderTextColor="#aaa" />
          </View>

          {/* Representante TWAS (opcional) */}
          <View style={{ marginBottom: 12 }}>
            <Text style={{ fontSize: 13, fontWeight: '600', color: '#444', marginBottom: 4 }}>Representante TWAS (opcional)</Text>
            <TextInput
              style={[styles.textInput, { height: 40 }]}
              value={representanteTwas}
              onChangeText={setRepresentanteTwas}
              placeholder="Nome do representante TWAS"
              placeholderTextColor="#aaa"
              data-testid="representante-twas-input"
            />
          </View>

          {/* Representante Cliente (opcional) */}
          <View style={{ marginBottom: 12 }}>
            <Text style={{ fontSize: 13, fontWeight: '600', color: '#444', marginBottom: 4 }}>Representante Cliente (opcional)</Text>
            <TextInput
              style={[styles.textInput, { height: 40 }]}
              value={representanteCliente}
              onChangeText={setRepresentanteCliente}
              placeholder="Nome do representante do cliente"
              placeholderTextColor="#aaa"
              data-testid="representante-cliente-input"
            />
          </View>

          {/* Índice do Relatório */}
          <View style={styles.indexHeader}>
            <Ionicons name="list-outline" size={24} color="#000000" />
            <View style={{ marginLeft: 10 }}>
              <Text style={styles.indexTitle}>Índice do Relatório</Text>
              <Text style={styles.indexCount}>{enabledCount} seções</Text>
            </View>
          </View>

          <TouchableOpacity style={styles.selectSectionsBtn} onPress={() => setShowSectionsModal(true)}>
            <Ionicons name="checkbox-outline" size={22} color="#000000" />
            <Text style={styles.selectSectionsText}>Selecionar Seções do Índice</Text>
            <Ionicons name="chevron-forward" size={20} color="#000000" />
          </TouchableOpacity>

          {/* Enabled Sections */}
          {sections.filter(s => s.enabled).map(sec => {
            const num = numberMap.get(sec.key) || '';
            const isCustom = sec.key.startsWith('custom_');
            const modes = customSectionMode[sec.key] || new Set(['text', 'photos']);
            return (
              <View key={sec.key} style={styles.card}>
                <TouchableOpacity onPress={() => setEditingSection(editingSection === sec.key ? null : sec.key)} style={styles.sectionHeaderRow}>
                  <Text style={styles.sectionNum}>{num}.</Text>
                  <Text style={[styles.sectionTitleText, { flex: 1 }]}>{sec.title}</Text>
                  {isCustom && (
                    <TouchableOpacity onPress={() => deleteCustomSection(sec.key)} style={{ padding: 4, marginRight: 8 }} data-testid={`delete-section-${sec.key}`}>
                      <Ionicons name="trash-outline" size={20} color="#d32f2f" />
                    </TouchableOpacity>
                  )}
                  <Ionicons name={editingSection === sec.key ? 'chevron-up' : 'chevron-down'} size={20} color="#000000" />
                </TouchableOpacity>
                {editingSection === sec.key && (
                  <View style={{ marginTop: 12 }}>
                    {isCustom && (
                      <View style={{ flexDirection: 'row', gap: 8, marginBottom: 12 }}>
                        <TouchableOpacity
                          style={[styles.modeBtn, modes.has('text') && styles.modeBtnActive]}
                          onPress={() => toggleCustomMode(sec.key, 'text')}
                        >
                          <Ionicons name="document-text-outline" size={18} color={modes.has('text') ? '#fff' : '#000000'} />
                          <Text style={[styles.modeBtnText, modes.has('text') && styles.modeBtnTextActive]}>Descricao</Text>
                        </TouchableOpacity>
                        <TouchableOpacity
                          style={[styles.modeBtn, modes.has('photos') && styles.modeBtnActive]}
                          onPress={() => toggleCustomMode(sec.key, 'photos')}
                        >
                          <Ionicons name="camera-outline" size={18} color={modes.has('photos') ? '#fff' : '#000000'} />
                          <Text style={[styles.modeBtnText, modes.has('photos') && styles.modeBtnTextActive]}>Fotos / Arquivo</Text>
                        </TouchableOpacity>
                      </View>
                    )}
                    {(!isCustom && !isPhotoOnlySection(sec.key) && !NO_TEXT_SECTIONS.includes(sec.key)) && (
                      <>
                        {renderTextAreaControls(sec.key, hiddenTextAreas.has(sec.key))}
                        {renderSmartTextArea(sec.key, sec.content, `Texto para ${sec.title}...`)}
                      </>
                    )}
                    {(!isCustom && isPhotoOnlySection(sec.key)) && renderPhotoGrid(sec.key, true)}
                    {isCustom && modes.has('text') && (
                      <>
                        {renderTextAreaControls(sec.key, hiddenTextAreas.has(sec.key))}
                        {renderSmartTextArea(sec.key, sec.content, `Texto para ${sec.title}...`)}
                      </>
                    )}
                    {isCustom && modes.has('photos') && renderPhotoGrid(sec.key, true)}
                    {sec.subsections.filter(sub => sub.enabled).map(sub => {
                      const subNum = numberMap.get(sub.key) || '';
                      const isPhotos = isPhotoOnlySection(sub.key);
                      const isCustomSub = sub.key.startsWith('sub_') || sub.key.startsWith('custom_') || sub.key.startsWith('subsub_');
                      const showPhotoUpload = PDF_UPLOAD_SECTIONS.has(sec.key) || isPhotos || isCustomSub;
                      return (
                        <View key={sub.key} style={styles.subsectionBlock}>
                          <TextInput
                            style={styles.subsectionTitleInput}
                            value={sub.title}
                            onChangeText={(t) => updateSectionTitle(sub.key, t)}
                            placeholder="Nome da subseção..."
                            data-testid={`subsection-title-${sub.key}`}
                          />
                          {!isPhotos && (!showPhotoUpload || isCustomSub) && (
                            <>
                              {renderTextAreaControls(sub.key, hiddenTextAreas.has(sub.key))}
                              {renderSmartTextArea(sub.key, sub.content, `Texto para ${sub.title}...`)}
                            </>
                          )}
                          {showPhotoUpload ? renderPhotoGrid(sub.key, true) : (canHavePhotos(sub.key) && renderPhotoGrid(sub.key))}
                          {(sub.subsections || []).filter((ss: Section) => ss.enabled).map((ss: Section) => {
                            const ssNum = numberMap.get(ss.key) || '';
                            const isSP = isPhotoOnlySection(ss.key);
                            const isCustomSubSub = ss.key.startsWith('sub_') || ss.key.startsWith('custom_') || ss.key.startsWith('subsub_');
                            return (
                              <View key={ss.key} style={styles.subsubBlock}>
                                <TextInput
                                  style={styles.subsubTitleInput}
                                  value={ss.title}
                                  onChangeText={(t) => updateSectionTitle(ss.key, t)}
                                  placeholder="Nome da subseção..."
                                />
                                {!isSP && (
                                  <>
                                    {renderTextAreaControls(ss.key, hiddenTextAreas.has(ss.key))}
                                    {renderSmartTextArea(ss.key, ss.content, `Texto para ${ss.title}...`)}
                                  </>
                                )}
                                {(isSP || isCustomSubSub) ? renderPhotoGrid(ss.key, true) : (canHavePhotos(ss.key) && renderPhotoGrid(ss.key))}
                              </View>);
                          })}
                        </View>);
                    })}
                    {/* Add subsection button */}
                    {showAddSubsection === sec.key ? (
                      <View style={styles.addSubRow}>
                        <TextInput style={styles.addSubInput} value={addingSubsectionTitle[sec.key] || ''} onChangeText={(t) => setAddingSubsectionTitle(prev => ({ ...prev, [sec.key]: t }))} placeholder="Nome da subseção..." autoFocus />
                        <TouchableOpacity style={styles.addSubConfirmBtn} onPress={() => addSubsection(sec.key)}><Ionicons name="checkmark-circle" size={26} color="#000000" /></TouchableOpacity>
                        <TouchableOpacity onPress={() => setShowAddSubsection(null)}><Ionicons name="close-circle" size={26} color="#999" /></TouchableOpacity>
                      </View>
                    ) : (
                      <TouchableOpacity style={styles.addSubBtn} onPress={() => setShowAddSubsection(sec.key)}>
                        <Ionicons name="add-circle-outline" size={18} color="#000000" />
                        <Text style={styles.addSubBtnText}>Adicionar Subseção</Text>
                      </TouchableOpacity>
                    )}
                  </View>
                )}
              </View>);
          })}

          {/* Daily Entries - only for daily reports */}
          {report?.report_type === 'daily' && (
            <>
              <View style={styles.indexHeader}>
                <Ionicons name="calendar-outline" size={24} color="#2e7d32" />
                <View style={{ marginLeft: 10, flex: 1 }}>
                  <Text style={[styles.indexTitle, { color: '#2e7d32' }]}>Entradas Diárias</Text>
                  <Text style={styles.indexCount}>{dailyEntries.length} dia(s)</Text>
                </View>
                <TouchableOpacity
                  style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: '#2e7d32', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20, gap: 6 }}
                  onPress={() => {
                    const today = new Date().toLocaleDateString('pt-BR');
                    const newEntry = { id: `day_${Date.now()}`, date: today, description: '' };
                    setDailyEntries(prev => [...prev, newEntry]);
                    setPdfSelectedDays(prev => new Set([...prev, newEntry.id]));
                    setExpandedDay(newEntry.id);
                  }}
                  data-testid="add-day-btn"
                >
                  <Ionicons name="add-circle-outline" size={18} color="#fff" />
                  <Text style={{ color: '#fff', fontSize: 13, fontWeight: '600' }}>Adicionar Dia</Text>
                </TouchableOpacity>
              </View>

              {dailyEntries.length === 0 && (
                <View style={{ alignItems: 'center', paddingVertical: 24 }}>
                  <Ionicons name="calendar-outline" size={48} color="#ccc" />
                  <Text style={{ color: '#999', marginTop: 8, fontSize: 13 }}>Nenhuma entrada diária ainda</Text>
                </View>
              )}

              {dailyEntries.length > 0 && (
                <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8, paddingHorizontal: 4 }}>
                  <Text style={{ fontSize: 12, color: '#666' }}>Incluir no PDF: {pdfSelectedDays.size}/{dailyEntries.length} dia(s)</Text>
                  <TouchableOpacity onPress={() => {
                    if (pdfSelectedDays.size === dailyEntries.length) {
                      setPdfSelectedDays(new Set());
                    } else {
                      setPdfSelectedDays(new Set(dailyEntries.map(e => e.id)));
                    }
                  }} data-testid="toggle-all-days-pdf">
                    <Text style={{ fontSize: 12, color: '#000000', fontWeight: '600' }}>
                      {pdfSelectedDays.size === dailyEntries.length ? 'Desmarcar Todos' : 'Selecionar Todos'}
                    </Text>
                  </TouchableOpacity>
                </View>
              )}

              {dailyEntries.map((entry, idx) => (
                <View key={entry.id} style={[styles.card, { borderLeftWidth: 3, borderLeftColor: pdfSelectedDays.has(entry.id) ? '#2e7d32' : '#ccc' }]}>
                  <TouchableOpacity
                    onPress={() => setExpandedDay(expandedDay === entry.id ? null : entry.id)}
                    style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}
                    data-testid={`day-entry-header-${idx}`}
                  >
                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, flex: 1 }}>
                      <TouchableOpacity onPress={(e) => {
                        e.stopPropagation && e.stopPropagation();
                        setPdfSelectedDays(prev => {
                          const next = new Set(prev);
                          if (next.has(entry.id)) next.delete(entry.id); else next.add(entry.id);
                          return next;
                        });
                      }} data-testid={`day-pdf-check-${idx}`}>
                        <Ionicons name={pdfSelectedDays.has(entry.id) ? 'checkbox' : 'square-outline'} size={22} color={pdfSelectedDays.has(entry.id) ? '#2e7d32' : '#999'} />
                      </TouchableOpacity>
                      <Text style={{ fontSize: 14, fontWeight: '700', color: '#333' }}>4.{idx + 1} - DIA</Text>
                      {Platform.OS === 'web' ? (
                        <input
                          type="date"
                          value={entry.date ? entry.date.split('/').reverse().join('-') : ''}
                          onChange={(e: any) => {
                            const val = e.target.value;
                            if (val) {
                              const [y, m, d] = val.split('-');
                              setDailyEntries(prev => prev.map(de => de.id === entry.id ? { ...de, date: `${d}/${m}/${y}` } : de));
                            }
                          }}
                          onClick={(e: any) => e.stopPropagation()}
                          style={{ border: '1px solid #ddd', borderRadius: 6, padding: '4px 8px', fontSize: 13, width: 140 } as any}
                          data-testid={`day-date-${idx}`}
                        />
                      ) : (
                        <TextInput
                          style={{ borderWidth: 1, borderColor: '#ddd', borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4, fontSize: 13, width: 110 }}
                          value={entry.date}
                          onChangeText={(t) => setDailyEntries(prev => prev.map(de => de.id === entry.id ? { ...de, date: t } : de))}
                          placeholder="DD/MM/AAAA"
                        />
                      )}
                    </View>
                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                      <TouchableOpacity
                        onPress={(e) => { e.stopPropagation && e.stopPropagation(); if (Platform.OS === 'web' && !window.confirm('Excluir esta entrada?')) return; setDailyEntries(prev => prev.filter(de => de.id !== entry.id)); }}
                        data-testid={`day-delete-${idx}`}
                      >
                        <Ionicons name="trash-outline" size={18} color="#d32f2f" />
                      </TouchableOpacity>
                      <Ionicons name={expandedDay === entry.id ? 'chevron-up' : 'chevron-down'} size={20} color="#666" />
                    </View>
                  </TouchableOpacity>

                  {expandedDay === entry.id && (
                    <View style={{ marginTop: 12 }}>
                      <Text style={{ fontSize: 12, fontWeight: '600', color: '#555', marginBottom: 6 }}>Descrição das Atividades</Text>
                      <View style={{ flexDirection: 'row', gap: 8, marginBottom: 6 }}>
                        <TouchableOpacity
                          onPress={() => {
                            const content = entry.description || '';
                            const lines = content.split('\n');
                            const bulletLines = lines.filter(l => l.startsWith('• ')).length;
                            const hasMost = lines.filter(l => l.trim().length > 0).length > 0 && bulletLines > lines.filter(l => l.trim().length > 0).length / 2;
                            if (hasMost) {
                              const cleaned = content.replace(/^• /gm, '');
                              setDailyEntries(prev => prev.map(de => de.id === entry.id ? { ...de, description: cleaned } : de));
                            } else {
                              const bulleted = lines.map(l => l.startsWith('• ') ? l : '• ' + l).join('\n');
                              setDailyEntries(prev => prev.map(de => de.id === entry.id ? { ...de, description: bulleted } : de));
                            }
                          }}
                          style={{ flexDirection: 'row', alignItems: 'center', paddingVertical: 4, paddingHorizontal: 8, backgroundColor: '#f0f0f0', borderRadius: 6 }}
                          data-testid={`toggle-bullets-daily-${entry.id}`}
                        >
                          <Ionicons name="list" size={16} color="#000" />
                          <Text style={{ fontSize: 11, marginLeft: 4, color: '#000', fontWeight: '500' }}>
                            {(entry.description || '').split('\n').filter(l => l.startsWith('• ')).length > (entry.description || '').split('\n').filter(l => l.trim().length > 0).length / 2 ? 'Remover Marcadores' : 'Adicionar Marcadores'}
                          </Text>
                        </TouchableOpacity>
                      </View>
                      <PlainTextArea
                        value={entry.description}
                        onChangeText={(t) => setDailyEntries(prev => prev.map(de => de.id === entry.id ? { ...de, description: t } : de))}
                        placeholder="Descreva as atividades realizadas neste dia..."
                      />
                      {renderPhotoGrid(`daily_${entry.id}`, false)}
                    </View>
                  )}
                </View>
              ))}
            </>
          )}

          {/* Save */}
          <TouchableOpacity style={[styles.saveButton, saving && { opacity: 0.6 }]} onPress={handleSave} disabled={saving}>
            {saving ? <ActivityIndicator color="#fff" /> : <><Ionicons name="save" size={22} color="#fff" /><Text style={styles.saveButtonText}>Salvar Relatório</Text></>}
          </TouchableOpacity>
        </ScrollView>
      </View>

      {/* Section Selection Modal */}
      <Modal visible={showSectionsModal} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            {/* Modal Header */}
            <View style={styles.modalHeader}>
              <TouchableOpacity onPress={() => setShowSectionsModal(false)}><Ionicons name="arrow-back" size={22} color="#000000" /></TouchableOpacity>
              <Text style={styles.modalHeaderTitle}>Selecionar Seções</Text>
              <View style={{ width: 22 }} />
            </View>

            <View style={styles.modalIconRow}><Ionicons name="list-outline" size={32} color="#000000" /></View>
            <Text style={styles.modalMainTitle}>Selecione as Seções do Relatório</Text>
            <Text style={styles.modalSubtitle}>Marque as caixas das seções que deseja incluir</Text>

            <ScrollView style={styles.modalScroll}>
              {sections.map(sec => {
                const num = numberMap.get(sec.key) || '-';
                return (
                  <View key={sec.key}>
                    <TouchableOpacity style={styles.checkRow} onPress={() => toggleSection(sec.key)}>
                      <View style={[styles.checkbox, sec.enabled && styles.checkboxChecked]}>
                        {sec.enabled && <Ionicons name="checkmark" size={14} color="#fff" />}
                      </View>
                      <Text style={styles.checkNum}>{sec.enabled ? num : '-'}</Text>
                      <Text style={styles.checkTitle}>{sec.title}</Text>
                      {sec.subsections.length > 0 && <Ionicons name="add-circle-outline" size={22} color="#bbb" />}
                    </TouchableOpacity>
                    {sec.enabled && sec.subsections.map(sub => {
                      const subNum = numberMap.get(sub.key) || '-';
                      return (
                        <View key={sub.key}>
                          <TouchableOpacity style={[styles.checkRow, { paddingLeft: 40 }]} onPress={() => toggleSection(sub.key)}>
                            <View style={[styles.checkbox, sub.enabled && styles.checkboxChecked]}>{sub.enabled && <Ionicons name="checkmark" size={14} color="#fff" />}</View>
                            <Text style={styles.checkNumSub}>{sub.enabled ? subNum : '-'}</Text>
                            <Text style={styles.checkTitleSub}>{sub.title}</Text>
                            {(sub.subsections || []).length > 0 && <Ionicons name="add-circle-outline" size={20} color="#bbb" />}
                          </TouchableOpacity>
                          {sub.enabled && (sub.subsections || []).map((ss: Section) => {
                            const ssNum = numberMap.get(ss.key) || '-';
                            return (
                              <TouchableOpacity key={ss.key} style={[styles.checkRow, { paddingLeft: 70 }]} onPress={() => toggleSection(ss.key)}>
                                <View style={[styles.checkbox, ss.enabled && styles.checkboxChecked]}>{ss.enabled && <Ionicons name="checkmark" size={14} color="#fff" />}</View>
                                <Text style={styles.checkNumSub}>{ss.enabled ? ssNum : '-'}</Text>
                                <Text style={styles.checkTitleSub}>{ss.title}</Text>
                              </TouchableOpacity>);
                          })}
                        </View>);
                    })}
                  </View>);
              })}

              <View style={styles.addSectionRow}>
                <TextInput style={styles.addSectionInput} value={addingSectionTitle} onChangeText={setAddingSectionTitle} placeholder="Nova seção personalizada..." />
                <TouchableOpacity style={styles.addSectionBtn} onPress={addCustomSection}><Ionicons name="add-circle" size={28} color="#000000" /></TouchableOpacity>
              </View>
            </ScrollView>

            <View style={styles.modalActions}>
              <TouchableOpacity style={styles.modalCancelBtn} onPress={() => setShowSectionsModal(false)}>
                <Text style={styles.modalCancelText}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.modalSaveBtn} onPress={() => setShowSectionsModal(false)}>
                <Ionicons name="checkmark-circle" size={20} color="#fff" />
                <Text style={styles.modalSaveText}>Salvar Seleção</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  innerContainer: { flex: 1, ...(Platform.OS === 'web' ? { height: '100vh', overflow: 'hidden' } : {}) } as any,
  scrollContent: { padding: 16, paddingBottom: 40 },
  backRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 },
  backText: { fontSize: 17, fontWeight: '600', color: '#000000' },
  serviceInfo: { marginBottom: 16 },
  serviceRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 4 },
  serviceText: { fontSize: 14, color: '#666' },
  serviceName: { fontSize: 14, color: '#666' },
  card: { backgroundColor: '#fff', borderRadius: 14, padding: 18, marginBottom: 12, ...(Platform.OS === 'web' ? { boxShadow: '0 1px 4px rgba(0,0,0,0.06)' } : { elevation: 1 }) } as any,
  cardLabel: { fontSize: 16, fontWeight: '700', color: '#222', marginBottom: 10 },
  // Cover photo
  coverPhotoWrapper: { position: 'relative', marginBottom: 8 },
  coverPhoto: { width: '100%', height: 200, borderRadius: 10 } as any,
  coverDeleteBtn: { position: 'absolute', top: 8, right: 8, backgroundColor: 'rgba(211,47,47,0.85)', borderRadius: 16, padding: 6 },
  coverUploadArea: { alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: '#ddd', borderStyle: 'dashed', borderRadius: 14, padding: 36, backgroundColor: '#fafafa' } as any,
  coverUploadText: { fontSize: 14, color: '#aaa', marginTop: 10 },
  vesselLabel: { fontSize: 13, fontWeight: '600', color: '#555', textAlign: 'center', marginTop: 8, marginBottom: 4 },
  // PDF buttons
  pdfOutlinedBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: '#000000', borderRadius: 12, padding: 14, marginBottom: 10, gap: 10, backgroundColor: '#fff' },
  pdfOutlinedText: { fontSize: 16, fontWeight: '700', color: '#000000' },
  pdfSolidBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#000000', borderRadius: 12, padding: 14, marginBottom: 16, gap: 10 },
  pdfSolidText: { fontSize: 16, fontWeight: '700', color: '#fff' },
  // Índice
  indexHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 10, paddingHorizontal: 4 },
  indexTitle: { fontSize: 18, fontWeight: '700', color: '#222' },
  indexCount: { fontSize: 13, color: '#999', marginTop: 2 },
  selectSectionsBtn: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#e8edf8', borderRadius: 12, padding: 14, marginBottom: 16, gap: 10 },
  selectSectionsText: { flex: 1, fontSize: 15, fontWeight: '600', color: '#000000' },
  // Period
  dateRow: { flexDirection: 'row', gap: 12 },
  dateField: { flex: 1 },
  dateLabel: { fontSize: 12, color: '#666', marginBottom: 4 },
  dateInput: { backgroundColor: '#f8f9fa', borderRadius: 10, borderWidth: 1, borderColor: '#e0e0e0', padding: 12, fontSize: 15, textAlign: 'center' },
  fieldLabel: { fontSize: 13, fontWeight: '600', color: '#333', marginBottom: 6 },
  input: { backgroundColor: '#f8f9fa', borderRadius: 10, borderWidth: 1, borderColor: '#e0e0e0', padding: 12, fontSize: 15, color: '#333' },
  // Sections
  sectionHeaderRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  sectionNum: { fontSize: 14, fontWeight: '700', color: '#000000' },
  sectionTitleText: { fontSize: 13, fontWeight: '700', color: '#000000', flex: 1 },
  subsectionBlock: { marginTop: 14, paddingLeft: 14, borderLeftWidth: 2, borderLeftColor: '#f0f0f0' },
  subsectionTitle: { fontSize: 12, fontWeight: '600', color: '#333', marginBottom: 6 },
  subsectionTitleInput: { fontSize: 13, fontWeight: '600', color: '#333', marginBottom: 6, borderBottomWidth: 1, borderBottomColor: '#e0e0e0', paddingVertical: 4, paddingHorizontal: 0, backgroundColor: 'transparent' },
  subsubBlock: { marginTop: 10, paddingLeft: 14 },
  subsubTitle: { fontSize: 11, fontWeight: '600', color: '#555', marginBottom: 4 },
  subsubTitleInput: { fontSize: 12, fontWeight: '600', color: '#555', marginBottom: 4, borderBottomWidth: 1, borderBottomColor: '#e0e0e0', paddingVertical: 2, paddingHorizontal: 0, backgroundColor: 'transparent' },
  // Add subsection
  addSubBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 12, paddingVertical: 8, paddingHorizontal: 12, backgroundColor: '#f0f4ff', borderRadius: 8, alignSelf: 'flex-start', borderWidth: 1, borderColor: '#d0d9f0', borderStyle: 'dashed' } as any,
  addSubBtnText: { fontSize: 13, fontWeight: '500', color: '#000000' },
  addSubRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 12 },
  addSubInput: { flex: 1, backgroundColor: '#f8f9fa', borderRadius: 10, borderWidth: 1, borderColor: '#000000', padding: 10, fontSize: 14, color: '#333' },
  addSubConfirmBtn: { padding: 2 },
  // Mode buttons for custom sections
  modeBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, flex: 1, paddingVertical: 10, paddingHorizontal: 12, borderRadius: 8, borderWidth: 1.5, borderColor: '#000000', justifyContent: 'center', backgroundColor: '#fff' },
  modeBtnActive: { backgroundColor: '#000000', borderColor: '#000000' },
  modeBtnText: { fontSize: 13, fontWeight: '600', color: '#000000' },
  modeBtnTextActive: { color: '#fff' },
  // Photos
  photoArea: { marginTop: 12, paddingTop: 12, borderTopWidth: 1, borderTopColor: '#f0f0f0' },
  photoHeader: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 8 },
  photoHeaderText: { fontSize: 13, fontWeight: '600', color: '#000000' },
  photoGridRow: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between' },
  photoGridItem: { width: '48%', marginBottom: 12 } as any,
  photoImageWrapper: { position: 'relative', width: '100%' },
  gridPhoto: { width: '100%', height: 140, borderRadius: 8 } as any,
  photoPlaceholder: { backgroundColor: '#f0f0f0', alignItems: 'center', justifyContent: 'center' },
  photoDeleteBtn: { position: 'absolute', top: -6, right: -6 },
  captionInput: { backgroundColor: '#f8f9fa', borderRadius: 6, borderWidth: 1, borderColor: '#e0e0e0', padding: 8, fontSize: 12, color: '#333', marginTop: 4, textAlign: 'center' },
  uploadBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 8, paddingHorizontal: 12, backgroundColor: '#f0f0f0', borderRadius: 8, alignSelf: 'flex-start', marginTop: 8 },
  uploadBtnText: { fontSize: 13, fontWeight: '500', color: '#000000' },
  // Save
  saveButton: { backgroundColor: '#000000', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', padding: 16, borderRadius: 12, gap: 8, marginBottom: 32 },
  saveButtonText: { color: '#fff', fontSize: 18, fontWeight: '600' },
  // Modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)', justifyContent: 'flex-end' },
  modalContent: { backgroundColor: '#fff', borderTopLeftRadius: 24, borderTopRightRadius: 24, paddingHorizontal: 20, paddingTop: 16, paddingBottom: 20, maxHeight: '90%' },
  modalHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 },
  modalHeaderTitle: { fontSize: 17, fontWeight: '700', color: '#222' },
  modalIconRow: { alignItems: 'center', marginBottom: 8 },
  modalMainTitle: { fontSize: 18, fontWeight: '700', color: '#222', textAlign: 'center', marginBottom: 4 },
  modalSubtitle: { fontSize: 13, color: '#888', textAlign: 'center', marginBottom: 16 },
  modalScroll: { maxHeight: 400 },
  checkRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, paddingHorizontal: 8, borderBottomWidth: 1, borderBottomColor: '#f2f2f2', gap: 12 },
  checkbox: { width: 24, height: 24, borderRadius: 4, borderWidth: 2, borderColor: '#ccc', alignItems: 'center', justifyContent: 'center', backgroundColor: '#fff' },
  checkboxChecked: { backgroundColor: '#000000', borderColor: '#000000' },
  checkNum: { fontSize: 16, fontWeight: '700', color: '#000000', width: 30 },
  checkTitle: { fontSize: 14, fontWeight: '700', color: '#333', flex: 1 },
  checkNumSub: { fontSize: 14, fontWeight: '600', color: '#000000', width: 40 },
  checkTitleSub: { fontSize: 13, fontWeight: '500', color: '#555', flex: 1 },
  addSectionRow: { flexDirection: 'row', alignItems: 'center', marginTop: 16, gap: 8, paddingHorizontal: 8 },
  addSectionInput: { flex: 1, backgroundColor: '#f8f9fa', borderRadius: 10, borderWidth: 1, borderColor: '#e0e0e0', padding: 10, fontSize: 14 },
  addSectionBtn: { padding: 4 },
  modalActions: { flexDirection: 'row', gap: 12, marginTop: 16 },
  modalCancelBtn: { flex: 1, padding: 14, borderRadius: 12, alignItems: 'center', backgroundColor: '#f5f5f5' },
  modalCancelText: { fontSize: 16, color: '#666', fontWeight: '600' },
  modalSaveBtn: { flex: 1.2, padding: 14, borderRadius: 12, alignItems: 'center', backgroundColor: '#2563eb', flexDirection: 'row', justifyContent: 'center', gap: 8 },
  modalSaveText: { fontSize: 16, color: '#fff', fontWeight: '700' },
});
