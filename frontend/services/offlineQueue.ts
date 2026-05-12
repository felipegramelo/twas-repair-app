/**
 * Offline-first queue for supervisor write operations.
 *
 * When the device is offline, create-timesheet/create-report calls are
 * stored locally in AsyncStorage. When connectivity returns, items are
 * flushed sequentially to the backend.
 *
 * The drafts are also stored locally so the supervisor can see them in
 * the dashboard list (with a "pendente sincronização" badge) before
 * they are sent.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';
import { timesheetAPI, reportAPI } from './api';

const QUEUE_KEY = 'offline_queue_v1';

export type QueueOperation =
  | {
      id: string;
      type: 'create_timesheet';
      payload: {
        os_id: string;
        entries: any[];
        observations?: string;
        supervisor_function?: string;
      };
      // Snapshot for display in the dashboard while offline
      snapshot: {
        id: string;
        os_id: string;
        os_number: string;
        client: string;
        service: string;
        entries: any[];
        observations?: string;
        status: 'draft';
        is_offline: true;
        created_at: string;
      };
      created_at: string;
      retries: number;
      last_error?: string;
    }
  | {
      id: string;
      type: 'create_report';
      payload: {
        report_type: string;
        os_id: string;
        periodo_inicio?: string;
        periodo_fim?: string;
        executado_por?: string;
      };
      snapshot: {
        id: string;
        os_id: string;
        os_number: string;
        client: string;
        report_type: string;
        periodo_inicio?: string;
        periodo_fim?: string;
        status: 'draft';
        is_offline: true;
        created_at: string;
      };
      created_at: string;
      retries: number;
      last_error?: string;
    };

type Listener = (state: { isOnline: boolean; pendingCount: number }) => void;

class OfflineQueue {
  private listeners: Set<Listener> = new Set();
  private isOnline: boolean = true;
  private isSyncing: boolean = false;
  private netInfoUnsub: (() => void) | null = null;

  init() {
    if (this.netInfoUnsub) return;
    this.netInfoUnsub = NetInfo.addEventListener(state => {
      const wasOffline = !this.isOnline;
      this.isOnline = !!(state.isConnected && state.isInternetReachable !== false);
      this.emit();
      if (wasOffline && this.isOnline) {
        // Auto-sync after connectivity returns (small delay so the network
        // stabilizes before issuing requests)
        setTimeout(() => this.flush(), 800);
      }
    });
    // Initial state
    NetInfo.fetch().then(state => {
      this.isOnline = !!(state.isConnected && state.isInternetReachable !== false);
      this.emit();
    });
  }

  subscribe(listener: Listener) {
    this.listeners.add(listener);
    // Push current state immediately
    this.getPendingCount().then(count => {
      listener({ isOnline: this.isOnline, pendingCount: count });
    });
    return () => {
      this.listeners.delete(listener);
    };
  }

  private async emit() {
    const count = await this.getPendingCount();
    this.listeners.forEach(l => l({ isOnline: this.isOnline, pendingCount: count }));
  }

  async getQueue(): Promise<QueueOperation[]> {
    try {
      const raw = await AsyncStorage.getItem(QUEUE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }

  async getPendingCount(): Promise<number> {
    const q = await this.getQueue();
    return q.length;
  }

  private async setQueue(q: QueueOperation[]) {
    await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(q));
  }

  /** Enqueue and return the local snapshot so the UI can show it immediately. */
  async enqueue(op: Omit<QueueOperation, 'id' | 'created_at' | 'retries'>): Promise<QueueOperation> {
    const queue = await this.getQueue();
    const newOp: QueueOperation = {
      ...op,
      id: `local_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      created_at: new Date().toISOString(),
      retries: 0,
    } as QueueOperation;
    queue.push(newOp);
    await this.setQueue(queue);
    this.emit();
    return newOp;
  }

  /** Remove a queued op (called after successful sync or manual cancel). */
  async remove(opId: string) {
    const queue = await this.getQueue();
    const filtered = queue.filter(o => o.id !== opId);
    await this.setQueue(filtered);
    this.emit();
  }

  /** Get the offline-only snapshots to render in dashboard lists. */
  async getOfflineTimesheets() {
    const q = await this.getQueue();
    return q
      .filter(o => o.type === 'create_timesheet')
      .map(o => ({ ...(o as any).snapshot, _queueId: o.id, _lastError: o.last_error }));
  }

  async getOfflineReports() {
    const q = await this.getQueue();
    return q
      .filter(o => o.type === 'create_report')
      .map(o => ({ ...(o as any).snapshot, _queueId: o.id, _lastError: o.last_error }));
  }

  /** Try to push everything in the queue. Returns counts. */
  async flush(): Promise<{ ok: number; failed: number }> {
    if (this.isSyncing) return { ok: 0, failed: 0 };
    this.isSyncing = true;
    let ok = 0;
    let failed = 0;
    try {
      const queue = await this.getQueue();
      for (const op of queue) {
        try {
          if (op.type === 'create_timesheet') {
            await timesheetAPI.create(
              op.payload.os_id,
              op.payload.entries,
              op.payload.observations,
              op.payload.supervisor_function,
            );
          } else if (op.type === 'create_report') {
            await reportAPI.create(op.payload);
          }
          await this.remove(op.id);
          ok++;
        } catch (e: any) {
          failed++;
          // Update retries / last_error in place
          const cur = await this.getQueue();
          const idx = cur.findIndex(x => x.id === op.id);
          if (idx >= 0) {
            cur[idx].retries = (cur[idx].retries || 0) + 1;
            cur[idx].last_error = e?.response?.data?.detail || e?.message || 'Erro de sincronização';
            await this.setQueue(cur);
          }
        }
      }
    } finally {
      this.isSyncing = false;
      this.emit();
    }
    return { ok, failed };
  }

  isConnected(): boolean {
    return this.isOnline;
  }
}

export const offlineQueue = new OfflineQueue();
