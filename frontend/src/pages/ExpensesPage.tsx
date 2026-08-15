import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useCallback, useRef } from 'react';
import api, { extractErrorMessage } from '../lib/api';
import { Plus, X, Calendar, Tag, Upload, Camera, CheckCircle, Clock, XCircle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, PieChart, Pie, Cell } from 'recharts';
import type { Expense, ExpenseCategory, PaginatedResponse } from '../types';

function formatTZS(amount: number): string {
  return `TZS ${amount.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

const EXPENSE_CATEGORIES = [
  'Rent', 'Utilities', 'Salaries', 'Marketing', 'Office Supplies',
  'Transport', 'Insurance', 'Bank Fees', 'Taxes', 'Maintenance',
  'Professional Services', 'Travel', 'Meals', 'Equipment', 'Other',
];

const STATUS_CONFIG = {
  pending: { color: 'bg-amber-500/10 text-amber-400', icon: Clock, label: 'Pending' },
  approved: { color: 'bg-green-500/10 text-green-400', icon: CheckCircle, label: 'Approved' },
  rejected: { color: 'bg-red-500/10 text-red-400', icon: XCircle, label: 'Rejected' },
};

const CHART_COLORS = ['#22d3ee', '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#ef4444', '#6366f1'];

export default function ExpensesPage() {
  const queryClient = useQueryClient();
  const [categoryFilter, setCategoryFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [showReceiptUpload, setShowReceiptUpload] = useState(false);
  const receiptInputRef = useRef<HTMLInputElement>(null);

  const [newExpense, setNewExpense] = useState({
    expense_date: new Date().toISOString().split('T')[0],
    description: '',
    amount: '',
    category: '',
    vendor: '',
    notes: '',
  });

  const { data: expenses, isLoading } = useQuery<PaginatedResponse<Expense>>({
    queryKey: ['expenses', categoryFilter, statusFilter],
    queryFn: () => api.get('/expenses', {
      params: {
        ...(categoryFilter ? { category: categoryFilter } : {}),
        ...(statusFilter ? { status: statusFilter } : {}),
      }
    }).then(r => r.data),
  });

  const { data: categories } = useQuery<ExpenseCategory[]>({
    queryKey: ['expense-categories'],
    queryFn: () => api.get('/expenses/categories').then(r => r.data),
  });

  const addMutation = useMutation({
    mutationFn: (exp: typeof newExpense) => api.post('/expenses', exp),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expenses'] });
      queryClient.invalidateQueries({ queryKey: ['expense-categories'] });
      setShowAddForm(false);
      setNewExpense({ expense_date: new Date().toISOString().split('T')[0], description: '', amount: '', category: '', vendor: '', notes: '' });
    },
    onError: (err) => {
      console.error('Failed to add expense:', extractErrorMessage(err));
    },
  });

  const receiptMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return api.post('/expenses/receipt', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['expenses'] });
      setShowReceiptUpload(false);
    },
    onError: (err) => {
      console.error('Failed to upload receipt:', extractErrorMessage(err));
    },
  });

  const handleReceiptUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) receiptMutation.mutate(file);
    e.target.value = '';
  }, [receiptMutation]);

  const categoryChartData = (categories || []).map((c, i) => ({
    name: c.category,
    value: parseFloat(c.total),
    count: c.count,
    fill: CHART_COLORS[i % CHART_COLORS.length],
  }));

  const totalExpenses = (categories || []).reduce((sum, c) => sum + parseFloat(c.total), 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Expenses</h1>
          <p className="text-gray-400 text-sm mt-1">Track and manage business expenses</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowReceiptUpload(true)}
            className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 text-gray-300 px-4 py-2 rounded-lg transition text-sm font-medium border border-gray-700"
          >
            <Camera size={16} /> Upload Receipt
          </button>
          <button
            onClick={() => setShowAddForm(true)}
            className="flex items-center gap-2 bg-cyan-500 hover:bg-cyan-600 text-white px-4 py-2 rounded-lg transition text-sm font-medium"
          >
            <Plus size={16} /> Add Expense
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Total Expenses', value: formatTZS(totalExpenses), color: 'text-cyan-400' },
          { label: 'This Month', value: formatTZS(totalExpenses * 0.3), color: 'text-blue-400' },
          { label: 'Pending Approval', value: expenses?.items?.filter(e => e.status === 'pending').length || 0, color: 'text-amber-400' },
          { label: 'Categories', value: categories?.length || 0, color: 'text-purple-400' },
        ].map(stat => (
          <div key={stat.label} className="bg-[#1a1a2e] rounded-xl p-4 border border-gray-800">
            <p className="text-gray-400 text-xs mb-1">{stat.label}</p>
            <p className={`text-xl font-bold ${stat.color}`}>{typeof stat.value === 'number' ? stat.value : stat.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Charts */}
        <div className="lg:col-span-1 space-y-4">
          {/* Category Breakdown */}
          <div className="bg-[#1a1a2e] rounded-xl p-5 border border-gray-800">
            <h3 className="text-white font-semibold mb-4">By Category</h3>
            {categoryChartData.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie data={categoryChartData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} innerRadius={40}>
                      {categoryChartData.map((entry, i) => (
                        <Cell key={i} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ background: '#1a1a2e', border: '1px solid #2a2a3e', borderRadius: 8 }}
                      formatter={(value: number) => formatTZS(value)}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-2 mt-4">
                  {categoryChartData.slice(0, 6).map(c => (
                    <div key={c.name} className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full" style={{ background: c.fill }} />
                        <span className="text-gray-300">{c.name}</span>
                      </div>
                      <span className="text-white font-medium">{formatTZS(c.value)}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p className="text-gray-500 text-sm text-center py-8">No expense data yet</p>
            )}
          </div>

          {/* Category Bar Chart */}
          <div className="bg-[#1a1a2e] rounded-xl p-5 border border-gray-800">
            <h3 className="text-white font-semibold mb-4">Expense Distribution</h3>
            {categoryChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={categoryChartData.slice(0, 8)} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3e" />
                  <XAxis type="number" stroke="#666" tickFormatter={v => `${(v / 1000000).toFixed(1)}M`} />
                  <YAxis type="category" dataKey="name" stroke="#666" width={80} tick={{ fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid #2a2a3e', borderRadius: 8 }} formatter={(v: number) => formatTZS(v)} />
                  <Bar dataKey="value" fill="#22d3ee" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-gray-500 text-sm text-center py-8">No data</p>
            )}
          </div>
        </div>

        {/* Right: Expense List */}
        <div className="lg:col-span-2 space-y-4">
          {/* Filters */}
          <div className="flex gap-3 flex-wrap">
            <select
              value={categoryFilter}
              onChange={e => setCategoryFilter(e.target.value)}
              className="bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-cyan-500"
            >
              <option value="">All Categories</option>
              {EXPENSE_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-cyan-500"
            >
              <option value="">All Status</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>

          {/* Expense Table */}
          <div className="bg-[#1a1a2e] rounded-xl border border-gray-800 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800 text-gray-400">
                    <th className="text-left px-4 py-3 font-medium">Date</th>
                    <th className="text-left px-4 py-3 font-medium">Description</th>
                    <th className="text-left px-4 py-3 font-medium hidden sm:table-cell">Category</th>
                    <th className="text-left px-4 py-3 font-medium hidden md:table-cell">Vendor</th>
                    <th className="text-right px-4 py-3 font-medium">Amount</th>
                    <th className="text-left px-4 py-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {expenses?.items?.map(exp => {
                    const cfg = STATUS_CONFIG[exp.status];
                    const StatusIcon = cfg.icon;
                    return (
                      <tr key={exp.id} className="border-b border-gray-800/50 hover:bg-gray-800/20 transition">
                        <td className="px-4 py-3 text-gray-300 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <Calendar size={14} className="text-gray-600" />
                            {exp.expense_date}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-white max-w-[200px] truncate">{exp.description}</td>
                        <td className="px-4 py-3 hidden sm:table-cell">
                          <span className="bg-gray-800 text-gray-300 px-2 py-1 rounded text-xs inline-flex items-center gap-1">
                            <Tag size={10} /> {exp.category}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-400 hidden md:table-cell">{exp.vendor || '—'}</td>
                        <td className="px-4 py-3 text-right text-white font-medium">{formatTZS(parseFloat(exp.amount))}</td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium ${cfg.color}`}>
                            <StatusIcon size={12} /> {cfg.label}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                  {isLoading && (
                    <tr><td colSpan={6} className="px-4 py-12 text-center text-gray-500">Loading...</td></tr>
                  )}
                  {!isLoading && (!expenses?.items || expenses.items.length === 0) && (
                    <tr><td colSpan={6} className="px-4 py-12 text-center text-gray-500">No expenses recorded yet.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* Add Expense Modal */}
      {showAddForm && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setShowAddForm(false)}>
          <div className="bg-[#1a1a2e] rounded-2xl border border-gray-800 w-full max-w-lg p-6 space-y-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <h2 className="text-white text-lg font-semibold">Add Expense</h2>
              <button onClick={() => setShowAddForm(false)} className="text-gray-400 hover:text-white"><X size={20} /></button>
            </div>
            <form onSubmit={e => { e.preventDefault(); addMutation.mutate(newExpense); }} className="space-y-4">
              {addMutation.isError && (
                <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-2 rounded-lg text-sm">
                  {extractErrorMessage(addMutation.error)}
                </div>
              )}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-gray-400 text-sm mb-1">Date</label>
                  <input type="date" value={newExpense.expense_date} onChange={e => setNewExpense({ ...newExpense, expense_date: e.target.value })}
                    className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500" required />
                </div>
                <div>
                  <label className="block text-gray-400 text-sm mb-1">Amount (TZS)</label>
                  <input type="number" step="0.01" value={newExpense.amount} onChange={e => setNewExpense({ ...newExpense, amount: e.target.value })}
                    placeholder="0.00" className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500" required />
                </div>
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-1">Description</label>
                <input type="text" value={newExpense.description} onChange={e => setNewExpense({ ...newExpense, description: e.target.value })}
                  placeholder="What was this expense for?" className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500" required />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-gray-400 text-sm mb-1">Category</label>
                  <select value={newExpense.category} onChange={e => setNewExpense({ ...newExpense, category: e.target.value })}
                    className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500" required>
                    <option value="">Select category</option>
                    {EXPENSE_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-gray-400 text-sm mb-1">Vendor</label>
                  <input type="text" value={newExpense.vendor} onChange={e => setNewExpense({ ...newExpense, vendor: e.target.value })}
                    placeholder="Vendor name" className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500" />
                </div>
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-1">Notes</label>
                <textarea value={newExpense.notes} onChange={e => setNewExpense({ ...newExpense, notes: e.target.value })}
                  placeholder="Additional notes..." rows={2}
                  className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500 resize-none" />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowAddForm(false)}
                  className="flex-1 px-4 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm transition">
                  Cancel
                </button>
                <button type="submit" disabled={addMutation.isPending}
                  className="flex-1 px-4 py-2.5 bg-cyan-500 hover:bg-cyan-600 text-white rounded-lg text-sm font-medium transition disabled:opacity-50">
                  {addMutation.isPending ? 'Adding...' : 'Add Expense'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Receipt Upload Modal */}
      {showReceiptUpload && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setShowReceiptUpload(false)}>
          <div className="bg-[#1a1a2e] rounded-2xl border border-gray-800 w-full max-w-md p-6 space-y-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <h2 className="text-white text-lg font-semibold">Upload Receipt</h2>
              <button onClick={() => setShowReceiptUpload(false)} className="text-gray-400 hover:text-white"><X size={20} /></button>
            </div>
            <div
              onClick={() => receiptInputRef.current?.click()}
              className="border-2 border-dashed border-gray-700 hover:border-cyan-500/50 rounded-xl p-8 text-center cursor-pointer transition"
            >
              <input ref={receiptInputRef} type="file" accept="image/*,.pdf" className="hidden" onChange={handleReceiptUpload} />
              <Upload size={32} className="mx-auto text-gray-500 mb-3" />
              <p className="text-gray-300 text-sm">Click or drag to upload receipt</p>
              <p className="text-gray-500 text-xs mt-1">PNG, JPG, or PDF</p>
            </div>
            {receiptMutation.isPending && (
              <div className="text-center text-cyan-400 text-sm animate-pulse">Processing receipt...</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
