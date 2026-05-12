import React from 'react';
import { View, Text, TouchableOpacity, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useOffline } from '../contexts/OfflineContext';

export function OfflineBanner() {
  const { isOnline, pendingCount, syncing, syncNow } = useOffline();

  // Hide banner only when fully online and no pending items
  if (isOnline && pendingCount === 0) return null;

  // Determine state
  const state = !isOnline ? 'offline' : pendingCount > 0 ? 'pending' : 'online';

  const bg = state === 'offline' ? '#d32f2f' : state === 'pending' ? '#f57c00' : '#2e7d32';
  const icon = state === 'offline' ? 'cloud-offline' : state === 'pending' ? 'sync' : 'cloud-done';
  const text =
    state === 'offline'
      ? `Você está offline${pendingCount > 0 ? ` — ${pendingCount} pendente(s)` : ''}`
      : `${pendingCount} item(ns) aguardando sincronização`;

  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: bg,
        paddingVertical: 8,
        paddingHorizontal: 14,
        gap: 8,
      }}
      testID="offline-banner"
    >
      <Ionicons name={icon as any} size={18} color="#fff" />
      <Text style={{ color: '#fff', flex: 1, fontSize: 13, fontWeight: '600' }}>{text}</Text>
      {state === 'pending' && (
        <TouchableOpacity
          onPress={() => syncNow()}
          disabled={syncing}
          style={{
            paddingVertical: 4,
            paddingHorizontal: 10,
            borderRadius: 14,
            backgroundColor: 'rgba(255,255,255,0.25)',
            flexDirection: 'row',
            alignItems: 'center',
            gap: 4,
          }}
          testID="offline-sync-now"
        >
          {syncing ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Ionicons name="refresh" size={14} color="#fff" />
          )}
          <Text style={{ color: '#fff', fontSize: 12, fontWeight: '600' }}>
            {syncing ? 'Sincronizando...' : 'Sincronizar'}
          </Text>
        </TouchableOpacity>
      )}
    </View>
  );
}
