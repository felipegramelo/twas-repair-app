import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as FileSystem from 'expo-file-system';
import * as Sharing from 'expo-sharing';

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
    const apiUrl = nativeUrl.includes('/api/') ? nativeUrl : nativeUrl.replace(/\/([^/]+\/[^/]+\/pdf)/, '/api/$1');
    const separator = apiUrl.includes('?') ? '&' : '?';
    const authUrl = token ? `${apiUrl}${separator}token=${encodeURIComponent(token)}` : apiUrl;
    const fileUri = `${FileSystem.cacheDirectory}${fileName}`;
    const downloadResult = await FileSystem.downloadAsync(authUrl, fileUri);
    if (downloadResult.status === 200) {
      const canShare = await Sharing.isAvailableAsync();
      if (canShare) {
        await Sharing.shareAsync(downloadResult.uri, {
          mimeType: 'application/pdf',
          dialogTitle: fileName,
        });
      }
    } else {
      throw new Error('Erro ao baixar PDF');
    }
  }
}
