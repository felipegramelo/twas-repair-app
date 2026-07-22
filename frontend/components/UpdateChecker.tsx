import React, { useEffect, useState } from 'react';
import { View, Text, TouchableOpacity, Platform, StyleSheet, AppState, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Updates from 'expo-updates';

// Native-only (iOS/Android) OTA update banner via expo-updates.
// Web is excluded on purpose: browsers already get the latest deploy on refresh.
export const UpdateChecker = () => {
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [updating, setUpdating] = useState(false);

  const checkForUpdate = async () => {
    try {
      if (!Updates.isEnabled) return; // Expo Go / dev builds
      const result = await Updates.checkForUpdateAsync();
      if (result.isAvailable) setUpdateAvailable(true);
    } catch {}
  };

  useEffect(() => {
    if (Platform.OS === 'web') return;
    checkForUpdate();
    const sub = AppState.addEventListener('change', state => {
      if (state === 'active') checkForUpdate();
    });
    return () => sub.remove();
  }, []);

  if (Platform.OS === 'web' || !updateAvailable) return null;

  const doUpdate = async () => {
    setUpdating(true);
    try {
      await Updates.fetchUpdateAsync();
      await Updates.reloadAsync();
    } catch {
      setUpdating(false);
    }
  };

  return (
    <View style={styles.banner} data-testid="update-banner">
      <Ionicons name="cloud-download-outline" size={18} color="#fff" />
      <Text style={styles.text}>Nova versão disponível!</Text>
      <TouchableOpacity style={styles.btn} onPress={doUpdate} disabled={updating} data-testid="update-app-btn">
        {updating ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.btnText}>Atualizar</Text>}
      </TouchableOpacity>
      <TouchableOpacity onPress={() => setUpdateAvailable(false)} data-testid="update-dismiss-btn">
        <Ionicons name="close" size={18} color="#fff" />
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  banner: {
    position: 'absolute',
    bottom: 24,
    left: 16,
    right: 16,
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    zIndex: 9999,
    shadowColor: '#000',
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  text: { color: '#fff', fontSize: 13, fontWeight: '600', flex: 1 },
  btn: { backgroundColor: '#4caf50', paddingVertical: 6, paddingHorizontal: 14, borderRadius: 8, minWidth: 84, alignItems: 'center' },
  btnText: { color: '#fff', fontSize: 13, fontWeight: '700' },
});
