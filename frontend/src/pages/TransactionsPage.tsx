import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api, { extractErrorMessage } from '../lib/api';
import { Upload, Search, Plus, Filter, X, Eye, Calendar, Tag } from 'lucide-react';
import { useState, useMemo } from 'react';
import type { Transaction, PaginatedResponse } from '../types';

const CATEGORIES = [
  'Sales Revenue', 'Service Revenue', 'Cost of Goods', 'Rent', 'Utilities',
  'Salaries', 'Marketing', 'Office Supplies', 'Transport', 'Insurance',
  'Bank Fees', 'Taxes', 'Maintenance', 'Professional Services', 'Other',
];

function formatTZS(amount: number): string {
  return `TZS ${amount.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

export default function TransactionsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState('');
  const [category, setCategory] = useState('');
  const [search, setSearch] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [amountMin, setAmountMin] = useState('');
  const [amountMax, setAmountMax] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedTxn, setSelectedTxn] = useState<Transaction | null>(null);
  const [importError, setImportError] = useState<string>('');
  const [importSuccess, setImportSuccess] = useState<string>('');

  // Add transaction form state
  const [newTxn, setNewTxn] = useState({
    txn_date: new Date().toISOString().split('T')[0],
    description: '',
    amount: '',
    counterparty: '',
    ai_category: '',
  });

  const { data, isLoading } = useQuery<PaginatedResponse<Transaction>>({
    queryKey: ['transactions', page, status, category, dateFrom, dateTo, amountMin, amountMax],
    queryFn: () => api.get('/transactions', {
      params: {
        page, page_size: 20,
        ...(status ? { status } : {}),
        ...(category ? { category } : {}),
        ...(dateFrom ? { date_from: dateFrom } : {}),
        ...(dateTo ? { date_to: dateTo } : {}),
        ...(amountMin ? { amount_min: amountMin } : {}),
        ...(amountMax ? { amount_max: amountMax } : {}),
      }
    }).then(r => r.data),
  });

  const addMutation = useMutation({
    mutationFn: (txn: typeof newTxn) => api.post('/transactions', txn),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      setShowAddForm(false);
      setNewTxn({ txn_date: new Date().toISOString().split('T')[0], description: '', amount: '', counterparty: '', ai_category: '' });
    },
  });

  const handleCSVImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImportError('');
    setImportSuccess('');
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await api.post('/transactions/import', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      const result = res.data;
      setImportSuccess(`Imported ${result.imported} of ${result.total_found} transactions (${result.skipped} skipped)`);
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
    } catch (err) {
      setImportError(extractErrorMessage(err, 'Failed to import CSV'));
    }
    // Reset file input
    e.target.value = '';
  };

  const filteredItems = useMemo(() => {
    if (!data?.items) return [];
    if (!search) return data.items;
    const q = search.toLowerCase();
    return data.items.filter(t =>
      (t.description || '').toLowerCase().includes(q) ||
      (t.counterparty || '').toLowerCase().includes(q) ||
      (t.ai_category || '').toLowerCase().includes(q)
    );
  }, [data?.items, search]);

  const hasActiveFilters = status || category || dateFrom || dateTo || amountMin || amountMax;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Transactions</h1>
          <p className="text-gray-400 text-sm mt-1">{data?.total || 0} total transactions</p>
        </div>
        <div className="flex gap-2">
          <label className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 text-gray-300 px-4 py-2 rounded-lg cursor-pointer transition text-sm font-medium border border-gray-700">
            <Upload size={16} /> Import CSV
            <input type="file" accept=".csv" className="hidden" onChange={handleCSVImport} />
          </label>
          <button
            onClick={() => setShowAddForm(true)}
            className="flex items-center gap-2 bg-cyan-500 hover:bg-cyan-600 text-white px-4 py-2 rounded-lg transition text-sm font-medium"
          >
            <Plus size={16} /> Add Transaction
          </button>
        </div>
      </div>

      {/* Import feedback */}
      {importError && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg text-sm flex items-center justify-between">
          <span>{importError}</span>
          <button onClick={() => setImportError('')} className="text-red-400 hover:text-red-300"><X size={16} /></button>
        </div>
      )}
      {importSuccess && (
        <div className="bg-green-500/10 border border-green-500/30 text-green-400 px-4 py-3 rounded-lg text-sm flex items-center justify-between">
          <span>{importSuccess}</span>
          <button onClick={() => setImportSuccess('')} className="text-green-400 hover:text-green-300"><X size={16} /></button>
        </div>
      )}

      {/* Search & Filters */}
      <div className="space-y-3">
        <div className="flex gap-3 flex-wrap">
          <div className="relative flex-1 min-w-[200px] max-w-md">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search transactions..."
              className="w-full bg-gray-800/50 border border-gray-700 rounded-lg pl-9 pr-4 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500 transition"
            />
          </div>
          <select
            value={status}
            onChange={e => { setStatus(e.target.value); setPage(1); }}
            className="bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500 transition"
          >
            <option value="">All Status</option>
            <option value="pending">Pending</option>
            <option value="categorized">Categorized</option>
            <option value="posted">Posted</option>
            <option value="flagged">Flagged</option>
          </select>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm transition border ${
              hasActiveFilters ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400' : 'bg-gray-800/50 border-gray-700 text-gray-400 hover:text-white'
            }`}
          >
            <Filter size={16} />
            Filters
            {hasActiveFilters && (
              <span className="w-5 h-5 rounded-full bg-cyan-500 text-white text-xs flex items-center justify-center">
                {[status, category, dateFrom, dateTo, amountMin, amountMax].filter(Boolean).length}
              </span>
            )}
          </button>
        </div>

        {/* Extended filters */}
        {showFilters && (
          <div className="bg-[#1a1a2e] rounded-xl border border-gray-800 p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-white text-sm font-medium">Advanced Filters</h3>
              {hasActiveFilters && (
                <button
                  onClick={() => { setStatus(''); setCategory(''); setDateFrom(''); setDateTo(''); setAmountMin(''); setAmountMax(''); setPage(1); }}
                  className="text-gray-400 hover:text-white text-xs flex items-center gap-1"
                >
                  <X size={12} /> Clear all
                </button>
              )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <div>
                <label className="block text-gray-400 text-xs mb-1.5">Category</label>
                <select
                  value={category}
                  onChange={e => { setCategory(e.target.value); setPage(1); }}
                  className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-cyan-500"
                >
                  <option value="">All Categories</option>
                  {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-gray-400 text-xs mb-1.5">Date From</label>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={e => { setDateFrom(e.target.value); setPage(1); }}
                  className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-cyan-500"
                />
              </div>
              <div>
                <label className="block text-gray-400 text-xs mb-1.5">Date To</label>
                <input
                  type="date"
                  value={dateTo}
                  onChange={e => { setDateTo(e.target.value); setPage(1); }}
                  className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-cyan-500"
                />
              </div>
              <div>
                <label className="block text-gray-400 text-xs mb-1.5">Min Amount (TZS)</label>
                <input
                  type="number"
                  value={amountMin}
                  onChange={e => { setAmountMin(e.target.value); setPage(1); }}
                  placeholder="0"
                  className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-cyan-500"
                />
              </div>
              <div>
                <label className="block text-gray-400 text-xs mb-1.5">Max Amount (TZS)</label>
                <input
                  type="number"
                  value={amountMax}
                  onChange={e => { setAmountMax(e.target.value); setPage(1); }}
                  placeholder="No limit"
                  className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Transaction Table */}
      <div className="bg-[#1a1a2e] rounded-xl border border-gray-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400">
                <th className="text-left px-4 py-3 font-medium">Date</th>
                <th className="text-left px-4 py-3 font-medium">Description</th>
                <th className="text-left px-4 py-3 font-medium hidden md:table-cell">Counterparty</th>
                <th className="text-right px-4 py-3 font-medium">Amount</th>
                <th className="text-left px-4 py-3 font-medium hidden sm:table-cell">Category</th>
                <th className="text-left px-4 py-3 font-medium">Status</th>
                <th className="text-right px-4 py-3 font-medium w-10"></th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map(txn => (
                <tr key={txn.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition cursor-pointer" onClick={() => setSelectedTxn(txn)}>
                  <td className="px-4 py-3 text-gray-300 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <Calendar size={14} className="text-gray-600" />
                      {txn.txn_date}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-white max-w-[200px] truncate">{txn.description || '—'}</td>
                  <td className="px-4 py-3 text-gray-300 hidden md:table-cell">{txn.counterparty || '—'}</td>
                  <td className="px-4 py-3 text-right font-medium whitespace-nowrap">
                    <span className={parseFloat(txn.amount) >= 0 ? 'text-green-400' : 'text-red-400'}>
                      {parseFloat(txn.amount) >= 0 ? '+' : ''}{formatTZS(Math.abs(parseFloat(txn.amount)))}
                    </span>
                  </td>
                  <td className="px-4 py-3 hidden sm:table-cell">
                    <span className="bg-gray-800 text-gray-300 px-2 py-1 rounded text-xs inline-flex items-center gap-1">
                      <Tag size={10} />
                      {txn.ai_category || 'Uncategorized'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      txn.status === 'posted' ? 'bg-green-500/10 text-green-400' :
                      txn.status === 'flagged' ? 'bg-red-500/10 text-red-400' :
                      txn.status === 'categorized' ? 'bg-blue-500/10 text-blue-400' :
                      'bg-amber-500/10 text-amber-400'
                    }`}>
                      {txn.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={(e) => { e.stopPropagation(); setSelectedTxn(txn); }} className="text-gray-500 hover:text-cyan-400 transition">
                      <Eye size={16} />
                    </button>
                  </td>
                </tr>
              ))}
              {isLoading && (
                <tr><td colSpan={7} className="px-4 py-12 text-center text-gray-500">Loading...</td></tr>
              )}
              {!isLoading && filteredItems.length === 0 && (
                <tr><td colSpan={7} className="px-4 py-12 text-center text-gray-500">No transactions found. Import a CSV or add one manually.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {data && data.pages > 1 && (
        <div className="flex justify-center gap-2">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 rounded text-sm bg-gray-800 text-gray-400 hover:bg-gray-700 disabled:opacity-30 transition"
          >
            Previous
          </button>
          {Array.from({ length: Math.min(data.pages, 7) }, (_, i) => {
            const p = i + 1;
            return (
              <button key={p} onClick={() => setPage(p)}
                className={`px-3 py-1.5 rounded text-sm transition ${p === page ? 'bg-cyan-500 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}>
                {p}
              </button>
            );
          })}
          <button
            onClick={() => setPage(p => Math.min(data.pages, p + 1))}
            disabled={page === data.pages}
            className="px-3 py-1.5 rounded text-sm bg-gray-800 text-gray-400 hover:bg-gray-700 disabled:opacity-30 transition"
          >
            Next
          </button>
        </div>
      )}

      {/* Add Transaction Modal */}
      {showAddForm && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setShowAddForm(false)}>
          <div className="bg-[#1a1a2e] rounded-2xl border border-gray-800 w-full max-w-lg p-6 space-y-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <h2 className="text-white text-lg font-semibold">Add Transaction</h2>
              <button onClick={() => setShowAddForm(false)} className="text-gray-400 hover:text-white"><X size={20} /></button>
            </div>
            <form onSubmit={e => { e.preventDefault(); addMutation.mutate(newTxn); }} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-gray-400 text-sm mb-1">Date</label>
                  <input type="date" value={newTxn.txn_date} onChange={e => setNewTxn({ ...newTxn, txn_date: e.target.value })}
                    className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500" required />
                </div>
                <div>
                  <label className="block text-gray-400 text-sm mb-1">Amount (TZS)</label>
                  <input type="number" step="0.01" value={newTxn.amount} onChange={e => setNewTxn({ ...newTxn, amount: e.target.value })}
                    placeholder="0.00" className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500" required />
                </div>
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-1">Description</label>
                <input type="text" value={newTxn.description} onChange={e => setNewTxn({ ...newTxn, description: e.target.value })}
                  placeholder="Payment for..." className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500" />
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-1">Counterparty</label>
                <input type="text" value={newTxn.counterparty} onChange={e => setNewTxn({ ...newTxn, counterparty: e.target.value })}
                  placeholder="Vendor or customer name" className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500" />
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-1">Category</label>
                <select value={newTxn.ai_category} onChange={e => setNewTxn({ ...newTxn, ai_category: e.target.value })}
                  className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500">
                  <option value="">Auto-detect (AI)</option>
                  {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowAddForm(false)}
                  className="flex-1 px-4 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm transition">
                  Cancel
                </button>
                <button type="submit" disabled={addMutation.isPending}
                  className="flex-1 px-4 py-2.5 bg-cyan-500 hover:bg-cyan-600 text-white rounded-lg text-sm font-medium transition disabled:opacity-50">
                  {addMutation.isPending ? 'Adding...' : 'Add Transaction'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Transaction Detail Modal */}
      {selectedTxn && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setSelectedTxn(null)}>
          <div className="bg-[#1a1a2e] rounded-2xl border border-gray-800 w-full max-w-lg p-6 space-y-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <h2 className="text-white text-lg font-semibold">Transaction Details</h2>
              <button onClick={() => setSelectedTxn(null)} className="text-gray-400 hover:text-white"><X size={20} /></button>
            </div>
            <div className="space-y-3">
              {[
                { label: 'Date', value: selectedTxn.txn_date },
                { label: 'Description', value: selectedTxn.description || '—' },
                { label: 'Counterparty', value: selectedTxn.counterparty || '—' },
                { label: 'Amount', value: formatTZS(parseFloat(selectedTxn.amount)), color: parseFloat(selectedTxn.amount) >= 0 ? 'text-green-400' : 'text-red-400' },
                { label: 'Currency', value: selectedTxn.currency },
                { label: 'Category', value: selectedTxn.ai_category || 'Uncategorized' },
                { label: 'Status', value: selectedTxn.status },
                { label: 'Source', value: selectedTxn.source },
              ].map(item => (
                <div key={item.label} className="flex justify-between items-center py-2 border-b border-gray-800/50">
                  <span className="text-gray-400 text-sm">{item.label}</span>
                  <span className={`text-sm font-medium ${item.color || 'text-white'}`}>{item.value}</span>
                </div>
              ))}
            </div>
            <button onClick={() => setSelectedTxn(null)}
              className="w-full px-4 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm transition">
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
