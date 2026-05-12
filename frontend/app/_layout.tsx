import { Stack } from 'expo-router';
import { AuthProvider } from '../contexts/AuthContext';
import { OfflineProvider } from '../contexts/OfflineContext';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import React from 'react';

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <OfflineProvider>
          <AuthProvider>
            <Stack screenOptions={{ headerShown: false }} />
          </AuthProvider>
        </OfflineProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
