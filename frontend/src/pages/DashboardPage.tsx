import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Wallet,
  AlertTriangle,
  Bot,
  ArrowRight,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import { motion } from 'framer-motion';
import {
  fetchDashboardSummary,
  fetchHealthScore,
  fetchMonthlyFinancials,
  fetchRecentTransactions,
  fetchAlerts,
} from '../lib/api';
import MetricCard, { formatTZS } from '../components/MetricCard';
import HealthScoreGauge from '../components/HealthScoreGauge';
import TransactionList from '../components/TransactionList';
import type { DashboardSummary, HealthScoreData, MonthlyFinancials, Alert, Transaction } from '../types';

export default function DashboardPage() {
  const navigate = useNavigate();

  const { data: summary } = useQuery<DashboardSummary>({
    queryKey: ['dashboard'],
    queryFn: fetchDashboardSummary,
  });

  const { data: healthScore } = useQuery<HealthScoreData>({
    queryKey: ['health-score'],
    queryFn: fetchHealthScore,
  });

  const { data: monthlyFinancials } = useQuery<MonthlyFinancials[]>({
    queryKey: ['monthly-financials'],
    queryFn: fetchMonthlyFinancials,
  });

  const { data: transactions } = useQuery<Transaction[]>({
    queryKey: ['recent-transactions'],
    queryFn: () => fetchRecentTransactions(10),
  });

  const { data: alerts } = useQuery<Alert[]>({
    queryKey: ['alerts'],
    queryFn: fetchAlerts,
  });

  const s = summary;

  // Fallback health score calculation if API doesn't provide one
  const computedScore = s
    ? Math.min(
        100,
        Math.max(
          0,
          (parseFloat(s.net_income) > 0 ? 30 : 0) +
            (parseFloat(s.cash_balance) > 0 ? 25 : 0) +
            (s.overdue_invoices === 0 ? 25 : 10) +
            (s.active_alerts === 0 ? 20 : 5)
        )
      )
    : 50;

  const displayScore = healthScore?.overall_score ?? computedScore;

  // Chart data
  const chartData = monthlyFinancials?.map((m) => ({
    month: m.month,
    Revenue: m.revenue,
    Expenses: m.expenses,
  })) ?? [
    { month: 'Jan', Revenue: 0, Expenses: 0 },
    { month: 'Feb', Revenue: 0, Expenses: 0 },
    { month: 'Mar', Revenue: 0, Expenses: 0 },
    { month: 'Apr', Revenue: 0, Expenses: 0 },
    { month: 'May', Revenue: 0, Expenses: 0 },
    { month: 'Jun', Revenue: 0, Expenses: 0 },
  ];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const customTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload) return null;
    return (
      <div className="bg-[#1a1a2e] border border-gray-700 rounded-lg px-4 py-3 shadow-xl">
        <p className="text-gray-400 text-xs mb-2">{label}</p>
        {payload.map((entry: { name: string; value: number; color: string }, i: number) => (
          <p key={i} className="text-sm" style={{ color: entry.color }}>
            {entry.name}: {formatTZS(entry.value)}
          </p>
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-gray-500 text-sm mt-1">
            {s?.period_label ?? 'This month'} · {s?.currency ?? 'TZS'}
          </p>
        </div>
        <button
          onClick={() => navigate('/ai-cfo')}
          className="flex items-center gap-2 bg-gradient-to-r from-cyan-500 to-blue-500 text-white px-4 py-2.5 rounded-lg text-sm font-medium hover:opacity-90 transition-opacity shadow-lg shadow-cyan-500/20"
        >
          <Bot size={18} />
          Ask AI CFO
        </button>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          icon={TrendingUp}
          label="Revenue"
          value={formatTZS(s?.total_revenue ?? '0')}
          color="text-green-400"
          change={s ? `+${s.transaction_count} txns` : undefined}
          trend="up"
          delay={0}
        />
        <MetricCard
          icon={TrendingDown}
          label="Expenses"
          value={formatTZS(s?.total_expenses ?? '0')}
          color="text-red-400"
          trend="down"
          delay={0.05}
        />
        <MetricCard
          icon={DollarSign}
          label="Net Profit"
          value={formatTZS(s?.net_income ?? '0')}
          color="text-cyan-400"
          trend={parseFloat(s?.net_income ?? '0') >= 0 ? 'up' : 'down'}
          delay={0.1}
        />
        <MetricCard
          icon={Wallet}
          label="Cash Balance"
          value={formatTZS(s?.cash_balance ?? '0')}
          color="text-blue-400"
          trend="flat"
          delay={0.15}
        />
      </div>

      {/* Chart + Health Score */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="lg:col-span-2 bg-[#1a1a2e] rounded-xl p-5 border border-gray-800"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-white font-semibold">Revenue vs Expenses</h3>
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
                Revenue
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-400" />
                Expenses
              </span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="revenueGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="expenseGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#f43f5e" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#f43f5e" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3e" />
              <XAxis dataKey="month" stroke="#666" fontSize={12} />
              <YAxis stroke="#666" fontSize={12} tickFormatter={(v: number) => `${(v / 1_000_000).toFixed(0)}M`} />
              <Tooltip content={customTooltip} />
              <Area type="monotone" dataKey="Revenue" stroke="#22d3ee" fill="url(#revenueGrad)" strokeWidth={2} />
              <Area type="monotone" dataKey="Expenses" stroke="#f43f5e" fill="url(#expenseGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <HealthScoreGauge
            score={displayScore}
            breakdown={healthScore?.breakdown}
            trend={healthScore?.trend}
            previousScore={healthScore?.previous_score}
          />
        </motion.div>
      </div>

      {/* Bottom row: Alerts + Transactions + AI CFO */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Attention Needed */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.35 }}
          className="bg-[#1a1a2e] rounded-xl p-5 border border-gray-800"
        >
          <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
            <AlertTriangle size={18} className="text-amber-400" />
            Attention Needed
          </h3>
          {alerts && alerts.length > 0 ? (
            <div className="space-y-2">
              {alerts.slice(0, 5).map((a) => (
                <div
                  key={a.id}
                  className={`p-3 rounded-lg text-sm ${
                    a.severity === 'critical'
                      ? 'bg-red-500/10 border border-red-500/30 text-red-400'
                      : a.severity === 'warning'
                        ? 'bg-amber-500/10 border border-amber-500/30 text-amber-400'
                        : 'bg-blue-500/10 border border-blue-500/30 text-blue-400'
                  }`}
                >
                  <div className="font-medium">{a.title}</div>
                  <div className="text-xs opacity-70 mt-1">{a.detail}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {/* Cash warning fallback */}
              {s && parseFloat(s.cash_balance) < 1_000_000 && (
                <div className="p-3 rounded-lg text-sm bg-amber-500/10 border border-amber-500/30 text-amber-400">
                  <div className="font-medium">Low Cash Balance</div>
                  <div className="text-xs opacity-70 mt-1">Cash balance is below TZS 1,000,000</div>
                </div>
              )}
              {s && s.overdue_invoices > 0 && (
                <div className="p-3 rounded-lg text-sm bg-red-500/10 border border-red-500/30 text-red-400">
                  <div className="font-medium">{s.overdue_invoices} Overdue Invoice(s)</div>
                  <div className="text-xs opacity-70 mt-1">Follow up on outstanding payments</div>
                </div>
              )}
              {s && s.pending_invoices > 5 && (
                <div className="p-3 rounded-lg text-sm bg-blue-500/10 border border-blue-500/30 text-blue-400">
                  <div className="font-medium">{s.pending_invoices} Pending Invoices</div>
                  <div className="text-xs opacity-70 mt-1">Review and process pending invoices</div>
                </div>
              )}
              {(!s || (parseFloat(s.cash_balance) >= 1_000_000 && s.overdue_invoices === 0 && s.pending_invoices <= 5)) && (
                <p className="text-gray-500 text-sm">No critical alerts — looking good! ✓</p>
              )}
            </div>
          )}
        </motion.div>

        {/* Recent Transactions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.4 }}
          className="bg-[#1a1a2e] rounded-xl p-5 border border-gray-800"
        >
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-white font-semibold">Recent Transactions</h3>
            <button
              onClick={() => navigate('/transactions')}
              className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors flex items-center gap-1"
            >
              View all <ArrowRight size={12} />
            </button>
          </div>
          <TransactionList transactions={transactions ?? []} limit={6} />
        </motion.div>

        {/* AI CFO Summary */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.45 }}
          className="bg-gradient-to-br from-[#1a1a2e] to-[#1a2a3e] rounded-xl p-5 border border-gray-800 flex flex-col"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center">
              <Bot size={22} className="text-white" />
            </div>
            <div>
              <h3 className="text-white font-semibold">AI CFO</h3>
              <p className="text-gray-400 text-xs">Your financial advisor</p>
            </div>
          </div>
          <div className="flex-1 space-y-3">
            <div className="bg-black/20 rounded-lg p-3 border border-gray-800/50">
              <p className="text-gray-300 text-sm leading-relaxed">
                {s
                  ? `Your net income is ${formatTZS(s.net_income)} with ${s.overdue_invoices} overdue invoice${s.overdue_invoices !== 1 ? 's' : ''}. Cash balance stands at ${formatTZS(s.cash_balance)}.`
                  : 'Loading financial overview...'}
              </p>
            </div>
            {s && parseFloat(s.net_income) < 0 && (
              <div className="bg-red-500/5 border border-red-500/20 rounded-lg p-3">
                <p className="text-red-400 text-xs font-medium">⚠ Net income is negative this period. Consider reviewing expenses.</p>
              </div>
            )}
          </div>
          <button
            onClick={() => navigate('/ai-cfo')}
            className="mt-4 w-full flex items-center justify-center gap-2 bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-cyan-500/20 transition-colors"
          >
            <Bot size={16} />
            Ask AI CFO
            <ArrowRight size={14} />
          </button>
        </motion.div>
      </div>
    </div>
  );
}
