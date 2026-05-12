import React, { createContext, useContext, useEffect, useState } from 'react';
import { offlineQueue } from '../services/offlineQueue';

interface OfflineState {
  isOnline: boolean;
  pendingCount: number;
  syncing: boolean;
  syncNow: () => Promise<{ ok: number; failed: number }>;
  refreshCount: () => void;
}

const OfflineContext = createContext<OfflineState | null>(null);

export function OfflineProvider({ children }: { children: React.ReactNode }) {
  const [isOnline, setIsOnline] = useState(true);
  const [pendingCount, setPendingCount] = useState(0);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    offlineQueue.init();
    const unsub = offlineQueue.subscribe(({ isOnline, pendingCount }) => {
      setIsOnline(isOnline);
      setPendingCount(pendingCount);
    });
    return unsub;
  }, []);

  const syncNow = async () => {
    setSyncing(true);
    try {
      return await offlineQueue.flush();
    } finally {
      setSyncing(false);
      const c = await offlineQueue.getPendingCount();
      setPendingCount(c);
    }
  };

  const refreshCount = () => {
    offlineQueue.getPendingCount().then(setPendingCount);
  };

  return (
    <OfflineContext.Provider value={{ isOnline, pendingCount, syncing, syncNow, refreshCount }}>
      {children}
    </OfflineContext.Provider>
  );
}

export function useOffline(): OfflineState {
  const ctx = useContext(OfflineContext);
  if (!ctx) {
    // Safe defaults when used outside provider (shouldn't happen, but defensive)
    return {
      isOnline: true,
      pendingCount: 0,
      syncing: false,
      syncNow: async () => ({ ok: 0, failed: 0 }),
      refreshCount: () => {},
    };
  }
  return ctx;
}
