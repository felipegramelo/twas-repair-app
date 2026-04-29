import { Platform, Alert } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as FileSystem from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';

/**
 * Build a standardized PDF filename matching the backend's format:
 *   "{os_number} - {client} - {docType} - {service}.pdf"
 * Example: "04 - 2603 - 01 - Petrobras - TM - Turbina Principal.pdf"
 * docType should be: "OS" (Service Order), "TM" (Timesheet), "REL" (Report), "BM" (Boletim)
 */
export function buildPdfFilename(
  docType: 'OS' | 'TM' | 'REL' | 'BM',
  osNumber?: string | null,
  client?: string | null,
  service?: string | null,
): string {
  const safe = (s?: string | null) =>
    String(s || '').replace(/[<>:"/\\|?*]/g, '').trim();
  const parts = [safe(osNumber), safe(client), docType, safe(service)].filter(Boolean);
  const base = parts.join(' - ') || `${docType}_${Date.now()}`;
  return `${base}.pdf`;
}

/**
 * Download and open/share a PDF file.
 * On web: creates a download link.
 * On iOS/Android: downloads via expo-file-system and opens share sheet.
 */
export async function downloadAndSharePDF(
  fetchBlob: () => Promise<Blob>,
  nativeUrl: string,
  fileName: string,
): Promise<void> {
  if (Platform.OS === 'web') {
    const blob = await fetchBlob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } else {
    const token = await AsyncStorage.getItem('token');
    // Ensure URL has /api prefix
    let apiUrl = nativeUrl.includes('/api/') ? nativeUrl : nativeUrl.replace(/\/([^/]+\/[^/]+\/pdf)/, '/api/$1');
    // Only add token if not already present in URL
    if (token && !apiUrl.includes('token=')) {
      const separator = apiUrl.includes('?') ? '&' : '?';
      apiUrl = `${apiUrl}${separator}token=${encodeURIComponent(token)}`;
    }
    const fileUri = `${FileSystem.cacheDirectory}${fileName}`;
    try {
      const downloadResult = await FileSystem.downloadAsync(apiUrl, fileUri);
      if (downloadResult.status === 200) {
        const canShare = await Sharing.isAvailableAsync();
        if (canShare) {
          await Sharing.shareAsync(downloadResult.uri, {
            mimeType: 'application/pdf',
            dialogTitle: fileName,
          });
        } else {
          Alert.alert('Aviso', 'Compartilhamento não disponível neste dispositivo.');
        }
      } else {
        Alert.alert('Erro', `Falha ao baixar PDF (status: ${downloadResult.status}). Verifique sua conexão e tente novamente.`);
      }
    } catch (error: any) {
      const msg = error?.message || 'Erro desconhecido ao baixar PDF';
      Alert.alert('Erro ao baixar PDF', msg);
      throw error;
    }
  }
}
