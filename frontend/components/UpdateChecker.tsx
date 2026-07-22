import React, { useEffect, useState } from 'react';
import { View, Text, TouchableOpacity, Platform, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { BACKEND_URL } from '../services/config';
import { APP_VERSION } from '../constants/appVersion';

export const UpdateChecker = () => {
  const [updateAvailable, setUpdateAvailable] = useState(false);

  const checkVersion = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/version?t=${Date.now()}`);
      if (!res.ok) return;
      const data = await res.json();
      if (data?.version && data.version !== APP_VERSION) setUpdateAvailable(true);
    } catch {}
  };

  useEffect(() => {
    if (Platform.OS !== 'web') return;
    checkVersion();
    const interval = setInterval(checkVersion, 5 * 60 * 1000);
    const onFocus = () => checkVersion();
    window.addEventListener('focus', onFocus);
    return () => {
      clearInterval(interval);
      window.removeEventListener('focus', onFocus);
    };
  }, []);

  if (!updateAvailable || Platform.OS !== 'web') return null;

  const doUpdate = async () => {
    try {
      if ('caches' in window) {
        const keys = await caches.keys();
        await Promise.all(keys.map(k => caches.delete(k)));
      }
    } catch {}
    window.location.reload();
  };

  return (
    <View style={styles.banner} data-testid="update-banner">
      <Ionicons name="cloud-download-outline" size={18} color="#fff" />
      <Text style={styles.text}>Nova versão disponível!</Text>
      <TouchableOpacity style={styles.btn} onPress={doUpdate} data-testid="update-app-btn">
        <Text style={styles.btnText}>Atualizar</Text>
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
    bottom: 16,
    left: 16,
    right: 16,
    maxWidth: 480,
    alignSelf: 'center',
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
  btn: { backgroundColor: '#4caf50', paddingVertical: 6, paddingHorizontal: 14, borderRadius: 8 },
  btnText: { color: '#fff', fontSize: 13, fontWeight: '700' },
});
