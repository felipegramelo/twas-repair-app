import React, { useState, useEffect, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, TextInput, Alert, ActivityIndicator, Platform, Modal, Switch, Image } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import { reportAPI } from '../../services/api';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface Section {
  key: string;
  number: string;
  title: string;
  content: string;
  enabled: boolean;
  subsections: Section[];
}

interface Photo {
  id: string;
  section_key: string;
  storage_path: string;
  original_filename: string;
}

// Sections that should NOT have photo upload
const NO_PHOTO_SECTIONS = ['introduction', 'equipment', 'objective', 'service_description', 'daily_activities', 'observations'];

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
  const [showSectionsModal, setShowSectionsModal] = useState(false);
  const [editingSection, setEditingSection] = useState<string | null>(null);
  const [addingSectionTitle, setAddingSectionTitle] = useState('');
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [uploading, setUploading] = useState<string | null>(null);
  const [token, setToken] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [currentUploadSection, setCurrentUploadSection] = useState('cover');

  useEffect(() => {
    loadReport();
    AsyncStorage.getItem('token').then(t => t && setToken(t));
  }, []);

  const loadReport = async () => {
    try {
      const [data, photosData] = await Promise.all([
        reportAPI.getById(id!),
        reportAPI.getPhotos(id!),
      ]);
      setReport(data);
      setPeriodoInicio(data.periodo_inicio || '');
      setPeriodoFim(data.periodo_fim || '');
      setExecutadoPor(data.executado_por || '');
      setSections(data.sections || []);
      setPhotos(photosData);
    } catch (error) {
      Alert.alert('Erro', 'Erro ao carregar relatório');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await reportAPI.update(id!, {
        periodo_inicio: periodoInicio,
        periodo_fim: periodoFim,
        executado_por: executadoPor,
        sections,
      });
      if (Platform.OS === 'web') window.alert('Relatório salvo com sucesso!');
      else Alert.alert('Sucesso', 'Relatório salvo com sucesso!');
      router.push('/supervisor');
    } catch (error: any) {
      Alert.alert('Erro', 'Erro ao salvar: ' + (error.message || ''));
    } finally {
      setSaving(false);
    }
  };

  const handleOpenPDF = async () => {
    try {
      if (Platform.OS === 'web') {
        const blob = await reportAPI.downloadPDF(id!);
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank');
      }
    } catch { if (Platform.OS === 'web') window.alert('Erro ao gerar PDF'); }
  };

  const triggerFileUpload = (sectionKey: string) => {
    setCurrentUploadSection(sectionKey);
    if (Platform.OS === 'web' && fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleFileSelected = async (event: any) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(currentUploadSection);
    try {
      const result = await reportAPI.uploadPhoto(id!, file, currentUploadSection, file.name);
      const updatedPhotos = await reportAPI.getPhotos(id!);
      setPhotos(updatedPhotos);
      if (Platform.OS === 'web') window.alert('Foto enviada com sucesso!');
    } catch (error: any) {
      if (Platform.OS === 'web') window.alert('Erro ao enviar foto: ' + (error.message || ''));
    } finally {
      setUploading(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDeletePhoto = async (photoId: string) => {
    if (Platform.OS === 'web' && !window.confirm('Excluir esta foto?')) return;
    try {
      await reportAPI.deletePhoto(id!, photoId);
      setPhotos(prev => prev.filter(p => p.id !== photoId));
    } catch { if (Platform.OS === 'web') window.alert('Erro ao excluir foto'); }
  };

  const getPhotoUrl = (storagePath: string) => reportAPI.getPhotoUrl(storagePath, token);

  const getPhotosForSection = (sectionKey: string) => photos.filter(p => p.section_key === sectionKey);

  const canHavePhotos = (sectionKey: string) => !NO_PHOTO_SECTIONS.includes(sectionKey);

  const toggleSection = (sectionKey: string) => {
    setSections(prev => prev.map(s => {
      if (s.key === sectionKey) return { ...s, enabled: !s.enabled };
      return {
        ...s,
        subsections: s.subsections.map(sub => {
          if (sub.key === sectionKey) return { ...sub, enabled: !sub.enabled };
          return {
            ...sub,
            subsections: (sub.subsections || []).map(ss =>
              ss.key === sectionKey ? { ...ss, enabled: !ss.enabled } : ss
            ),
          };
        }),
      };
    }));
  };

  const updateSectionContent = (sectionKey: string, content: string) => {
    setSections(prev => prev.map(s => {
      if (s.key === sectionKey) return { ...s, content };
      return {
        ...s,
        subsections: s.subsections.map(sub => {
          if (sub.key === sectionKey) return { ...sub, content };
          return {
            ...sub,
            subsections: (sub.subsections || []).map(ss =>
              ss.key === sectionKey ? { ...ss, content } : ss
            ),
          };
        }),
      };
    }));
  };

  const addCustomSection = () => {
    if (!addingSectionTitle.trim()) return;
    const nextNum = String(sections.length + 1);
    const newSection: Section = {
      key: `custom_${Date.now()}`,
      number: nextNum,
      title: addingSectionTitle.trim().toUpperCase(),
      content: '',
      enabled: true,
      subsections: [],
    };
    setSections(prev => [...prev, newSection]);
    setAddingSectionTitle('');
  };

  const formatDateInput = (text: string, setter: (v: string) => void) => {
    const cleaned = text.replace(/\D/g, '');
    let formatted = cleaned;
    if (cleaned.length >= 3 && cleaned.length <= 4) formatted = cleaned.slice(0, 2) + '/' + cleaned.slice(2);
    else if (cleaned.length >= 5) formatted = cleaned.slice(0, 2) + '/' + cleaned.slice(2, 4) + '/' + cleaned.slice(4, 8);
    setter(formatted);
  };

  const renderPhotoSection = (sectionKey: string) => {
    if (!canHavePhotos(sectionKey)) return null;
    const sectionPhotos = getPhotosForSection(sectionKey);
    return (
      <View style={styles.photoArea}>
        <View style={styles.photoHeader}>
          <Ionicons name="camera-outline" size={16} color="#1a237e" />
          <Text style={styles.photoHeaderText}>Fotos ({sectionPhotos.length})</Text>
        </View>
        {sectionPhotos.length > 0 && (
          <View style={styles.photoGrid}>
            {sectionPhotos.map(photo => (
              <View key={photo.id} style={styles.photoItem}>
                {token ? (
                  <Image source={{ uri: getPhotoUrl(photo.storage_path) }} style={styles.photoImage} resizeMode="cover" />
                ) : (
                  <View style={[styles.photoImage, styles.photoPlaceholder]}>
                    <Ionicons name="image-outline" size={24} color="#999" />
                  </View>
                )}
                <TouchableOpacity style={styles.photoDeleteBtn} onPress={() => handleDeletePhoto(photo.id)}>
                  <Ionicons name="close-circle" size={20} color="#d32f2f" />
                </TouchableOpacity>
                <Text style={styles.photoName} numberOfLines={1}>{photo.original_filename}</Text>
              </View>
            ))}
          </View>
        )}
        <TouchableOpacity
          style={styles.uploadBtn}
          onPress={() => triggerFileUpload(sectionKey)}
          disabled={uploading === sectionKey}
        >
          {uploading === sectionKey ? (
            <ActivityIndicator size="small" color="#1a237e" />
          ) : (
            <>
              <Ionicons name="cloud-upload-outline" size={18} color="#1a237e" />
              <Text style={styles.uploadBtnText}>Adicionar Foto</Text>
            </>
          )}
        </TouchableOpacity>
      </View>
    );
  };

  if (loading) {
    return <SafeAreaView style={styles.container}><ActivityIndicator size="large" color="#1a237e" style={{ marginTop: 100 }} /></SafeAreaView>;
  }

  if (!report) {
    return <SafeAreaView style={styles.container}><Text style={{ padding: 20, textAlign: 'center' }}>Relatório não encontrado</Text></SafeAreaView>;
  }

  const isService = report.report_type === 'service';
  const coverPhotos = getPhotosForSection('cover');

  return (
    <SafeAreaView style={styles.container}>
      {/* Hidden file input for web */}
      {Platform.OS === 'web' && (
        <input
          ref={fileInputRef as any}
          type="file"
          accept="image/*"
          style={{ display: 'none' }}
          onChange={handleFileSelected}
        />
      )}
      <View style={styles.innerContainer}>
        <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={true}>
          {/* Header */}
          <View style={styles.headerRow}>
            <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
              <Ionicons name="arrow-back" size={24} color="#1a237e" />
            </TouchableOpacity>
            <Text style={styles.headerTitle} numberOfLines={1}>
              {isService ? 'Editar Rel. Serviço' : 'Editar Rel. Diário'}
            </Text>
            <TouchableOpacity onPress={handleOpenPDF} style={styles.pdfButton} data-testid="open-pdf-btn">
              <Ionicons name="document-text-outline" size={22} color="#1a237e" />
            </TouchableOpacity>
          </View>

          {/* Info Card */}
          <View style={styles.infoCard}>
            <View style={styles.infoBadge}>
              <Text style={styles.infoBadgeText}>{report.os_number}</Text>
            </View>
            <Text style={styles.infoClient}>{report.client}</Text>
            <Text style={styles.infoLocation}>{report.location} - {report.service}</Text>
          </View>

          {/* Cover Photo */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Foto de Capa</Text>
            {coverPhotos.length > 0 ? (
              <View style={styles.coverPhotoContainer}>
                {coverPhotos.map(photo => (
                  <View key={photo.id} style={styles.coverPhotoWrapper}>
                    {token ? (
                      <Image source={{ uri: getPhotoUrl(photo.storage_path) }} style={styles.coverPhoto} resizeMode="cover" />
                    ) : (
                      <View style={[styles.coverPhoto, styles.photoPlaceholder]}>
                        <Ionicons name="image-outline" size={40} color="#999" />
                      </View>
                    )}
                    <TouchableOpacity style={styles.coverDeleteBtn} onPress={() => handleDeletePhoto(photo.id)}>
                      <Ionicons name="trash-outline" size={16} color="#fff" />
                    </TouchableOpacity>
                  </View>
                ))}
              </View>
            ) : (
              <TouchableOpacity
                style={styles.coverUploadArea}
                onPress={() => triggerFileUpload('cover')}
                disabled={uploading === 'cover'}
                data-testid="upload-cover-photo-btn"
              >
                {uploading === 'cover' ? (
                  <ActivityIndicator size="large" color="#1a237e" />
                ) : (
                  <>
                    <Ionicons name="camera-outline" size={40} color="#bbb" />
                    <Text style={styles.coverUploadText}>Toque para adicionar foto de capa</Text>
                  </>
                )}
              </TouchableOpacity>
            )}
            {coverPhotos.length > 0 && (
              <TouchableOpacity style={styles.uploadBtn} onPress={() => triggerFileUpload('cover')} disabled={uploading === 'cover'}>
                {uploading === 'cover' ? <ActivityIndicator size="small" color="#1a237e" /> : (
                  <>
                    <Ionicons name="cloud-upload-outline" size={18} color="#1a237e" />
                    <Text style={styles.uploadBtnText}>Trocar Foto</Text>
                  </>
                )}
              </TouchableOpacity>
            )}
          </View>

          {/* Período */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Período e Informações</Text>
            <View style={styles.dateRow}>
              <View style={styles.dateField}>
                <Text style={styles.dateLabel}>Data Início</Text>
                <TextInput style={styles.dateInput} value={periodoInicio} onChangeText={(t) => formatDateInput(t, setPeriodoInicio)} placeholder="DD/MM/AAAA" keyboardType="numeric" maxLength={10} />
              </View>
              <View style={styles.dateField}>
                <Text style={styles.dateLabel}>Data Fim</Text>
                <TextInput style={styles.dateInput} value={periodoFim} onChangeText={(t) => formatDateInput(t, setPeriodoFim)} placeholder="DD/MM/AAAA" keyboardType="numeric" maxLength={10} />
              </View>
            </View>
            <Text style={[styles.fieldLabel, { marginTop: 12 }]}>Executado Por</Text>
            <TextInput style={styles.input} value={executadoPor} onChangeText={setExecutadoPor} placeholder="Ex: TWAS REPAIR" />
          </View>

          {/* Sections Management Button */}
          <TouchableOpacity style={styles.manageSectionsBtn} onPress={() => setShowSectionsModal(true)} data-testid="manage-sections-btn">
            <Ionicons name="settings-outline" size={20} color="#1a237e" />
            <Text style={styles.manageSectionsBtnText}>Gerenciar Seções</Text>
            <Ionicons name="chevron-forward" size={18} color="#999" />
          </TouchableOpacity>

          {/* Enabled Sections */}
          {sections.filter(s => s.enabled).map(sec => (
            <View key={sec.key} style={styles.section}>
              <TouchableOpacity onPress={() => setEditingSection(editingSection === sec.key ? null : sec.key)}>
                <View style={styles.sectionHeader}>
                  <Text style={styles.sectionNumber}>{sec.number}.</Text>
                  <Text style={styles.sectionTitle}>{sec.title}</Text>
                  <Ionicons name={editingSection === sec.key ? 'chevron-up' : 'chevron-down'} size={20} color="#1a237e" />
                </View>
              </TouchableOpacity>

              {editingSection === sec.key && (
                <View style={styles.sectionContent}>
                  {sec.key !== 'service_description' && sec.key !== 'daily_activities' && (
                    <TextInput
                      style={styles.textarea}
                      value={sec.content}
                      onChangeText={(t) => updateSectionContent(sec.key, t)}
                      placeholder={`Texto para ${sec.title}...`}
                      multiline
                      textAlignVertical="top"
                    />
                  )}

                  {/* Photo upload for this section */}
                  {renderPhotoSection(sec.key)}

                  {/* Subsections */}
                  {sec.subsections.filter(sub => sub.enabled).map(sub => (
                    <View key={sub.key} style={styles.subsectionBlock}>
                      <Text style={styles.subsectionTitle}>{sub.number}. {sub.title}</Text>
                      <TextInput
                        style={styles.textarea}
                        value={sub.content}
                        onChangeText={(t) => updateSectionContent(sub.key, t)}
                        placeholder={`Texto para ${sub.title}...`}
                        multiline
                        textAlignVertical="top"
                      />
                      {renderPhotoSection(sub.key)}
                      {(sub.subsections || []).filter((ss: Section) => ss.enabled).map((ss: Section) => (
                        <View key={ss.key} style={styles.subsubBlock}>
                          <Text style={styles.subsubTitle}>{ss.number}. {ss.title}</Text>
                          <TextInput
                            style={styles.textarea}
                            value={ss.content}
                            onChangeText={(t) => updateSectionContent(ss.key, t)}
                            placeholder={`Texto para ${ss.title}...`}
                            multiline
                            textAlignVertical="top"
                          />
                          {renderPhotoSection(ss.key)}
                        </View>
                      ))}
                    </View>
                  ))}
                </View>
              )}
            </View>
          ))}

          {/* Save Button */}
          <TouchableOpacity style={[styles.saveButton, saving && styles.saveButtonDisabled]} onPress={handleSave} disabled={saving} data-testid="save-report-btn">
            {saving ? <ActivityIndicator color="#fff" /> : (
              <>
                <Ionicons name="save" size={22} color="#fff" />
                <Text style={styles.saveButtonText}>Salvar Relatório</Text>
              </>
            )}
          </TouchableOpacity>
        </ScrollView>
      </View>

      {/* Sections Management Modal */}
      <Modal visible={showSectionsModal} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Gerenciar Seções</Text>
            <Text style={styles.modalSubtitle}>Ative ou desative as seções do relatório</Text>

            <ScrollView style={styles.modalScroll}>
              {sections.map(sec => (
                <View key={sec.key}>
                  <View style={styles.toggleRow}>
                    <Switch value={sec.enabled} onValueChange={() => toggleSection(sec.key)} trackColor={{ false: '#ddd', true: '#bbdefb' }} thumbColor={sec.enabled ? '#1a237e' : '#999'} />
                    <Text style={[styles.toggleText, !sec.enabled && styles.toggleTextDisabled]}>{sec.number}. {sec.title}</Text>
                  </View>
                  {sec.enabled && sec.subsections.map(sub => (
                    <View key={sub.key}>
                      <View style={[styles.toggleRow, { paddingLeft: 32 }]}>
                        <Switch value={sub.enabled} onValueChange={() => toggleSection(sub.key)} trackColor={{ false: '#ddd', true: '#bbdefb' }} thumbColor={sub.enabled ? '#1a237e' : '#999'} />
                        <Text style={[styles.toggleText, styles.toggleSubText, !sub.enabled && styles.toggleTextDisabled]}>{sub.number}. {sub.title}</Text>
                      </View>
                      {sub.enabled && (sub.subsections || []).map((ss: Section) => (
                        <View key={ss.key} style={[styles.toggleRow, { paddingLeft: 56 }]}>
                          <Switch value={ss.enabled} onValueChange={() => toggleSection(ss.key)} trackColor={{ false: '#ddd', true: '#bbdefb' }} thumbColor={ss.enabled ? '#1a237e' : '#999'} />
                          <Text style={[styles.toggleText, styles.toggleSubSubText, !ss.enabled && styles.toggleTextDisabled]}>{ss.number}. {ss.title}</Text>
                        </View>
                      ))}
                    </View>
                  ))}
                </View>
              ))}

              <View style={styles.addSectionRow}>
                <TextInput style={styles.addSectionInput} value={addingSectionTitle} onChangeText={setAddingSectionTitle} placeholder="Nova seção personalizada..." />
                <TouchableOpacity style={styles.addSectionBtn} onPress={addCustomSection}>
                  <Ionicons name="add-circle" size={28} color="#1a237e" />
                </TouchableOpacity>
              </View>
            </ScrollView>

            <TouchableOpacity style={styles.modalCloseBtn} onPress={() => setShowSectionsModal(false)}>
              <Text style={styles.modalCloseBtnText}>Fechar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  innerContainer: { flex: 1, ...(Platform.OS === 'web' ? { height: '100vh', overflow: 'hidden' } : {}) } as any,
  scrollContent: { padding: 16, paddingBottom: 32 },
  headerRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 16, gap: 8 },
  backButton: { padding: 8 },
  headerTitle: { fontSize: 20, fontWeight: 'bold', color: '#1a237e', flex: 1 },
  pdfButton: { padding: 8 },
  infoCard: { backgroundColor: '#e3f2fd', borderRadius: 12, padding: 16, marginBottom: 12 },
  infoBadge: { backgroundColor: '#1a237e', alignSelf: 'flex-start', paddingHorizontal: 12, paddingVertical: 4, borderRadius: 6, marginBottom: 8 },
  infoBadgeText: { color: '#fff', fontWeight: '600', fontSize: 12 },
  infoClient: { fontSize: 16, fontWeight: '600', color: '#1a237e' },
  infoLocation: { fontSize: 13, color: '#555', marginTop: 4 },
  section: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 10 },
  sectionHeader: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  sectionNumber: { fontSize: 16, fontWeight: '700', color: '#1a237e' },
  sectionTitle: { fontSize: 15, fontWeight: '700', color: '#1a237e', flex: 1 },
  sectionContent: { marginTop: 12 },
  subsectionBlock: { marginTop: 12, paddingLeft: 12, borderLeftWidth: 2, borderLeftColor: '#e3f2fd' },
  subsectionTitle: { fontSize: 14, fontWeight: '600', color: '#333', marginBottom: 6 },
  subsubBlock: { marginTop: 8, paddingLeft: 12 },
  subsubTitle: { fontSize: 13, fontWeight: '600', color: '#555', marginBottom: 4 },
  fieldLabel: { fontSize: 13, fontWeight: '600', color: '#333', marginBottom: 6 },
  input: { backgroundColor: '#f8f9fa', borderRadius: 8, borderWidth: 1, borderColor: '#e0e0e0', padding: 12, fontSize: 15, color: '#333' },
  textarea: { backgroundColor: '#f8f9fa', borderRadius: 8, borderWidth: 1, borderColor: '#e0e0e0', padding: 12, fontSize: 14, color: '#333', minHeight: 80 },
  dateRow: { flexDirection: 'row', gap: 12 },
  dateField: { flex: 1 },
  dateLabel: { fontSize: 12, color: '#666', marginBottom: 4 },
  dateInput: { backgroundColor: '#f8f9fa', borderRadius: 8, borderWidth: 1, borderColor: '#e0e0e0', padding: 12, fontSize: 15, textAlign: 'center' },
  manageSectionsBtn: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 12, gap: 8 },
  manageSectionsBtnText: { flex: 1, fontSize: 15, fontWeight: '600', color: '#1a237e' },
  saveButton: { backgroundColor: '#1a237e', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', padding: 16, borderRadius: 12, gap: 8, marginBottom: 32 },
  saveButtonDisabled: { opacity: 0.6 },
  saveButtonText: { color: '#fff', fontSize: 18, fontWeight: '600' },
  // Cover Photo
  coverPhotoContainer: { marginTop: 8 },
  coverPhotoWrapper: { position: 'relative', marginBottom: 8 },
  coverPhoto: { width: '100%', height: 200, borderRadius: 8 } as any,
  coverDeleteBtn: { position: 'absolute', top: 8, right: 8, backgroundColor: 'rgba(211,47,47,0.85)', borderRadius: 16, padding: 6 },
  coverUploadArea: { alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: '#e0e0e0', borderStyle: 'dashed', borderRadius: 12, padding: 32, marginTop: 8, backgroundColor: '#fafafa' } as any,
  coverUploadText: { fontSize: 14, color: '#999', marginTop: 8 },
  // Photo in sections
  photoArea: { marginTop: 12, paddingTop: 12, borderTopWidth: 1, borderTopColor: '#f0f0f0' },
  photoHeader: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 8 },
  photoHeaderText: { fontSize: 13, fontWeight: '600', color: '#1a237e' },
  photoGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 8 },
  photoItem: { width: 100, position: 'relative' },
  photoImage: { width: 100, height: 80, borderRadius: 6 },
  photoPlaceholder: { backgroundColor: '#f0f0f0', alignItems: 'center', justifyContent: 'center' },
  photoDeleteBtn: { position: 'absolute', top: -6, right: -6 },
  photoName: { fontSize: 10, color: '#999', marginTop: 2 },
  uploadBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 8, paddingHorizontal: 12, backgroundColor: '#e3f2fd', borderRadius: 8, alignSelf: 'flex-start', marginTop: 8 },
  uploadBtnText: { fontSize: 13, fontWeight: '500', color: '#1a237e' },
  // Modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modalContent: { backgroundColor: '#fff', borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: 20, maxHeight: '80%' },
  modalTitle: { fontSize: 20, fontWeight: '700', color: '#1a237e', textAlign: 'center' },
  modalSubtitle: { fontSize: 13, color: '#666', textAlign: 'center', marginTop: 4, marginBottom: 16 },
  modalScroll: { maxHeight: 400 },
  toggleRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 8, gap: 12 },
  toggleText: { fontSize: 14, fontWeight: '600', color: '#333', flex: 1 },
  toggleSubText: { fontSize: 13, fontWeight: '500' },
  toggleSubSubText: { fontSize: 12, fontWeight: '400' },
  toggleTextDisabled: { color: '#aaa', textDecorationLine: 'line-through' },
  addSectionRow: { flexDirection: 'row', alignItems: 'center', marginTop: 16, gap: 8 },
  addSectionInput: { flex: 1, backgroundColor: '#f8f9fa', borderRadius: 8, borderWidth: 1, borderColor: '#e0e0e0', padding: 10, fontSize: 14 },
  addSectionBtn: { padding: 4 },
  modalCloseBtn: { backgroundColor: '#1a237e', borderRadius: 12, padding: 14, alignItems: 'center', marginTop: 16 },
  modalCloseBtnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
