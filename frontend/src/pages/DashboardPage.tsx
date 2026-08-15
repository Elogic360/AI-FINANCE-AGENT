import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import StatCard from '../components/StatCard';
import HealthScore from '../components/HealthScore';
import { DollarSign, TrendingUp, TrendingDown, Wallet, AlertTriangle, FileText } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import type { DashboardSummary, Alert } from '../types';

export default function DashboardPage() {
  const { data: summary } = useQuery<DashboardSummary>({ queryKey: ['dashboard'], queryFn: () => api.get('/dashboard/summary').then(r => r.data) });
  const { data: alerts } = useQuery<Alert[]>({ queryKey: ['alerts'], queryFn: () => api.get('/alerts').then(r => r.data) });

  const s = summary;
  const chartData = s ? [
    { name: 'Revenue', value: parseFloat(s.total_revenue) },
    { name: 'Expenses', value: parseFloat(s.total_expenses) },
    { name: 'Net Income', value: parseFloat(s.net_income) },
  ] : [];

  const healthScore = s ? Math.min(100, Math.max(0,
    (parseFloat(s.net_income) > 0 ? 30 : 0) +
    (parseFloat(s.cash_balance) > 0 ? 25 : 0) +
    (s.overdue_invoices === 0 ? 25 : 10) +
    (s.active_alerts === 0 ? 20 : 5)
  )) : 50;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Dashboard</h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={TrendingUp} label="Revenue" value={`${s?.currency || 'TZS'} ${parseFloat(s?.total_revenue || '0').toLocaleString()}`} color="text-green-400" />
        <StatCard icon={TrendingDown} label="Expenses" value={`${s?.currency || 'TZS'} ${parseFloat(s?.total_expenses || '0').toLocaleString()}`} color="text-red-400" />
        <StatCard icon={DollarSign} label="Net Income" value={`${s?.currency || 'TZS'} ${parseFloat(s?.net_income || '0').toLocaleString()}`} color="text-cyan-400" />
        <StatCard icon={Wallet} label="Cash Balance" value={`${s?.currency || 'TZS'} ${parseFloat(s?.cash_balance || '0').toLocaleString()}`} color="text-blue-400" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 bg-[#1a1a2e] rounded-xl p-5 border border-gray-800">
          <h3 className="text-white font-semibold mb-4">Financial Overview</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3e" />
              <XAxis dataKey="name" stroke="#666" />
              <YAxis stroke="#666" />
              <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid #2a2a3e', borderRadius: 8 }} />
              <Bar dataKey="value" fill="#22d3ee" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <HealthScore score={healthScore} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-[#1a1a2e] rounded-xl p-5 border border-gray-800">
          <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
            <AlertTriangle size={18} className="text-amber-400" /> Alerts
          </h3>
          {alerts && alerts.length > 0 ? (
            <div className="space-y-2">
              {alerts.slice(0, 5).map(a => (
                <div key={a.id} className={`p-3 rounded-lg text-sm ${a.severity === 'critical' ? 'bg-red-500/10 border border-red-500/30 text-red-400' : a.severity === 'warning' ? 'bg-amber-500/10 border border-amber-500/30 text-amber-400' : 'bg-blue-500/10 border border-blue-500/30 text-blue-400'}`}>
                  <div className="font-medium">{a.title}</div>
                  <div className="text-xs opacity-70 mt-1">{a.detail}</div>
                </div>
              ))}
            </div>
          ) : <p className="text-gray-500 text-sm">No alerts</p>}
        </div>
        <div className="bg-[#1a1a2e] rounded-xl p-5 border border-gray-800">
          <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
            <FileText size={18} className="text-cyan-400" /> Quick Stats
          </h3>
          <div className="space-y-3">
            {[
              ['Transactions', s?.transaction_count || 0],
              ['Pending Invoices', s?.pending_invoices || 0],
              ['Overdue Invoices', s?.overdue_invoices || 0],
              ['Active Alerts', s?.active_alerts || 0],
            ].map(([label, value]) => (
              <div key={String(label)} className="flex justify-between items-center py-2 border-b border-gray-800 last:border-0">
                <span className="text-gray-400 text-sm">{label}</span>
                <span className="text-white font-medium">{String(value)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
