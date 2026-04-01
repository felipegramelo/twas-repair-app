import React, { useState, useEffect } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, ScrollView,
  ActivityIndicator, Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import api from '../../services/api';

const showMsg = (msg: string) => {
  if (Platform.OS === 'web') window.alert(msg);
};

const formatCurrency = (v: number) =>
  v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

interface DashboardData {
  bm_by_month: { month: string; total: number; count: number }[];
  proposals_by_status: Record<string, number>;
  totals: {
    bm_total_value: number;
    bm_count: number;
    proposals_count: number;
    os_count: number;
    timesheets_count: number;
  };
  top_clients: { client: string; total: number; count: number }[];
}

const STATUS_LABELS: Record<string, string> = {
  pendente: 'Pendente',
  aprovada: 'Aprovada',
  rejeitada: 'Rejeitada',
  cancelada: 'Cancelada',
};
const STATUS_COLORS: Record<string, string> = {
  pendente: '#FF9800',
  aprovada: '#4CAF50',
  rejeitada: '#F44336',
  cancelada: '#9E9E9E',
};

export default function DashboardScreen() {
  const router = useRouter();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const resp = await api.get('/dashboard/summary');
      setData(resp.data);
    } catch {
      showMsg('Erro ao carregar dashboard');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <View style={s.center}><ActivityIndicator size="large" color="#1a237e" /></View>;
  if (!data) return <View style={s.center}><Text>Erro ao carregar dados</Text></View>;

  const maxBmValue = Math.max(...data.bm_by_month.map(m => m.total), 1);
  const totalProposals = Object.values(data.proposals_by_status).reduce((a, b) => a + b, 0) || 1;
  const maxClientValue = Math.max(...data.top_clients.map(c => c.total), 1);

  return (
    <SafeAreaView style={s.container}>
      <View style={s.header}>
        <TouchableOpacity onPress={() => router.replace('/admin')} style={s.backBtn} data-testid="dashboard-back-btn">
          <Ionicons name="arrow-back" size={24} color="#1a237e" />
        </TouchableOpacity>
        <Text style={s.title}>Dashboard Financeiro</Text>
        <TouchableOpacity onPress={loadDashboard} style={s.backBtn} data-testid="dashboard-refresh-btn">
          <Ionicons name="refresh" size={22} color="#1a237e" />
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={s.scrollContent}>
        {/* Summary Cards */}
        <View style={s.summaryRow} data-testid="summary-cards">
          <View style={[s.summaryCard, { borderLeftColor: '#1a237e' }]}>
            <Ionicons name="cash-outline" size={28} color="#1a237e" />
            <Text style={s.summaryValue}>{formatCurrency(data.totals.bm_total_value)}</Text>
            <Text style={s.summaryLabel}>Total BMs</Text>
          </View>
          <View style={[s.summaryCard, { borderLeftColor: '#4CAF50' }]}>
            <Ionicons name="document-text-outline" size={28} color="#4CAF50" />
            <Text style={s.summaryValue}>{data.totals.proposals_count}</Text>
            <Text style={s.summaryLabel}>Propostas</Text>
          </View>
          <View style={[s.summaryCard, { borderLeftColor: '#FF9800' }]}>
            <Ionicons name="clipboard-outline" size={28} color="#FF9800" />
            <Text style={s.summaryValue}>{data.totals.os_count}</Text>
            <Text style={s.summaryLabel}>Ordens de Serv.</Text>
          </View>
          <View style={[s.summaryCard, { borderLeftColor: '#7B1FA2' }]}>
            <Ionicons name="time-outline" size={28} color="#7B1FA2" />
            <Text style={s.summaryValue}>{data.totals.timesheets_count}</Text>
            <Text style={s.summaryLabel}>Timesheets</Text>
          </View>
        </View>

        {/* BM by Month Chart */}
        <View style={s.chartCard} data-testid="bm-by-month-chart">
          <Text style={s.chartTitle}>Boletins de Medicao por Mes</Text>
          <Text style={s.chartSubtitle}>{data.totals.bm_count} boletins | {formatCurrency(data.totals.bm_total_value)}</Text>
          <View style={s.barChart}>
            {data.bm_by_month.map((m, i) => {
              const barHeight = m.total > 0 ? Math.max((m.total / maxBmValue) * 140, 4) : 2;
              const isActive = m.total > 0;
              return (
                <View key={i} style={s.barGroup}>
                  {isActive && (
                    <Text style={s.barValue}>{formatCurrency(m.total)}</Text>
                  )}
                  <View style={[s.bar, { height: barHeight, backgroundColor: isActive ? '#1a237e' : '#E0E0E0' }]} />
                  <Text style={s.barLabel}>{m.month.substring(0, 5)}</Text>
                  {isActive && <Text style={s.barCount}>{m.count} BM{m.count > 1 ? 's' : ''}</Text>}
                </View>
              );
            })}
          </View>
        </View>

        {/* Proposals by Status */}
        <View style={s.chartCard} data-testid="proposals-status-chart">
          <Text style={s.chartTitle}>Propostas por Status</Text>
          <View style={s.statusContainer}>
            {/* Horizontal stacked bar */}
            <View style={s.stackedBar}>
              {Object.entries(data.proposals_by_status).map(([status, count], i) => (
                <View
                  key={status}
                  style={[s.stackedSegment, {
                    flex: count,
                    backgroundColor: STATUS_COLORS[status] || '#9E9E9E',
                    borderTopLeftRadius: i === 0 ? 8 : 0,
                    borderBottomLeftRadius: i === 0 ? 8 : 0,
                    borderTopRightRadius: i === Object.keys(data.proposals_by_status).length - 1 ? 8 : 0,
                    borderBottomRightRadius: i === Object.keys(data.proposals_by_status).length - 1 ? 8 : 0,
                  }]}
                />
              ))}
            </View>
            {/* Legend */}
            <View style={s.legendRow}>
              {Object.entries(data.proposals_by_status).map(([status, count]) => (
                <View key={status} style={s.legendItem}>
                  <View style={[s.legendDot, { backgroundColor: STATUS_COLORS[status] || '#9E9E9E' }]} />
                  <Text style={s.legendText}>
                    {STATUS_LABELS[status] || status}: {count} ({Math.round((count / totalProposals) * 100)}%)
                  </Text>
                </View>
              ))}
            </View>
          </View>
        </View>

        {/* Top Clients */}
        {data.top_clients.length > 0 && (
          <View style={s.chartCard} data-testid="top-clients-chart">
            <Text style={s.chartTitle}>Top Clientes (por valor BM)</Text>
            {data.top_clients.map((client, i) => (
              <View key={i} style={s.clientRow}>
                <View style={s.clientInfo}>
                  <Text style={s.clientRank}>#{i + 1}</Text>
                  <View style={{ flex: 1 }}>
                    <Text style={s.clientName}>{client.client}</Text>
                    <Text style={s.clientMeta}>{client.count} BM{client.count > 1 ? 's' : ''}</Text>
                  </View>
                  <Text style={s.clientValue}>{formatCurrency(client.total)}</Text>
                </View>
                <View style={s.clientBar}>
                  <View style={[s.clientBarFill, { width: `${(client.total / maxClientValue) * 100}%` }]} />
                </View>
              </View>
            ))}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f0f2f5' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 12, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#e0e0e0' },
  backBtn: { padding: 8 },
  title: { fontSize: 20, fontWeight: '700', color: '#1a237e' },
  scrollContent: { padding: 16, gap: 16 },
  // Summary cards
  summaryRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  summaryCard: { flex: 1, minWidth: 150, backgroundColor: '#fff', borderRadius: 12, padding: 16, borderLeftWidth: 4, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.08, shadowRadius: 3, elevation: 2 },
  summaryValue: { fontSize: 18, fontWeight: '700', color: '#1a237e', marginTop: 8 },
  summaryLabel: { fontSize: 12, color: '#666', marginTop: 2 },
  // Chart cards
  chartCard: { backgroundColor: '#fff', borderRadius: 12, padding: 20, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.08, shadowRadius: 3, elevation: 2 },
  chartTitle: { fontSize: 16, fontWeight: '700', color: '#1a237e', marginBottom: 4 },
  chartSubtitle: { fontSize: 12, color: '#666', marginBottom: 16 },
  // Bar chart
  barChart: { flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between', height: 200, paddingTop: 40 },
  barGroup: { alignItems: 'center', flex: 1, justifyContent: 'flex-end' },
  bar: { width: 24, borderRadius: 4, marginBottom: 4 },
  barValue: { fontSize: 8, color: '#1a237e', fontWeight: '600', marginBottom: 2, textAlign: 'center' },
  barLabel: { fontSize: 9, color: '#666', marginTop: 2 },
  barCount: { fontSize: 8, color: '#999' },
  // Proposals status
  statusContainer: { gap: 16 },
  stackedBar: { flexDirection: 'row', height: 32, borderRadius: 8, overflow: 'hidden' },
  stackedSegment: { justifyContent: 'center', alignItems: 'center' },
  legendRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 16 },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  legendDot: { width: 12, height: 12, borderRadius: 6 },
  legendText: { fontSize: 13, color: '#333' },
  // Top clients
  clientRow: { marginBottom: 16 },
  clientInfo: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 6 },
  clientRank: { fontSize: 14, fontWeight: '700', color: '#1a237e', width: 28 },
  clientName: { fontSize: 14, fontWeight: '600', color: '#333' },
  clientMeta: { fontSize: 11, color: '#999' },
  clientValue: { fontSize: 14, fontWeight: '700', color: '#1a237e' },
  clientBar: { height: 8, backgroundColor: '#E8EAF6', borderRadius: 4, overflow: 'hidden' },
  clientBarFill: { height: '100%', backgroundColor: '#1a237e', borderRadius: 4 },
});
