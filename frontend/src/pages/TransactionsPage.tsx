import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import { Upload, Search } from 'lucide-react';
import { useState } from 'react';
import type { Transaction, PaginatedResponse } from '../types';

export default function TransactionsPage() {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState('');
  const [search, setSearch] = useState('');

  const { data } = useQuery<PaginatedResponse<Transaction>>({
    queryKey: ['transactions', page, status],
    queryFn: () => api.get('/transactions', { params: { page, page_size: 20, ...(status ? { status } : {}) } }).then(r => r.data),
  });

  const handleCSVImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    await api.post('/transactions/import', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
    window.location.reload();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h1 className="text-2xl font-bold text-white">Transactions</h1>
        <label className="flex items-center gap-2 bg-cyan-500 hover:bg-cyan-600 text-white px-4 py-2 rounded-lg cursor-pointer transition text-sm font-medium">
          <Upload size={16} /> Import CSV
          <input type="file" accept=".csv" className="hidden" onChange={handleCSVImport} />
        </label>
      </div>

      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 max-w-xs">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search..."
            className="w-full bg-gray-800/50 border border-gray-700 rounded-lg pl-9 pr-4 py-2 text-white text-sm focus:outline-none focus:border-cyan-500" />
        </div>
        <select value={status} onChange={e => setStatus(e.target.value)}
          className="bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-cyan-500">
          <option value="">All Status</option>
          <option value="pending">Pending</option>
          <option value="categorized">Categorized</option>
          <option value="posted">Posted</option>
          <option value="flagged">Flagged</option>
        </select>
      </div>

      <div className="bg-[#1a1a2e] rounded-xl border border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-gray-400">
              <th className="text-left px-4 py-3 font-medium">Date</th>
              <th className="text-left px-4 py-3 font-medium">Description</th>
              <th className="text-left px-4 py-3 font-medium">Counterparty</th>
              <th className="text-right px-4 py-3 font-medium">Amount</th>
              <th className="text-left px-4 py-3 font-medium">Category</th>
              <th className="text-left px-4 py-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {data?.items?.map(txn => (
              <tr key={txn.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                <td className="px-4 py-3 text-gray-300">{txn.txn_date}</td>
                <td className="px-4 py-3 text-white">{txn.description || '—'}</td>
                <td className="px-4 py-3 text-gray-300">{txn.counterparty || '—'}</td>
                <td className="px-4 py-3 text-right text-white font-medium">
                  {parseFloat(txn.amount) >= 0 ? '+' : ''}{parseFloat(txn.amount).toLocaleString()} {txn.currency}
                </td>
                <td className="px-4 py-3"><span className="bg-gray-800 text-gray-300 px-2 py-1 rounded text-xs">{txn.ai_category || 'Uncategorized'}</span></td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${txn.status === 'posted' ? 'bg-green-500/10 text-green-400' : txn.status === 'flagged' ? 'bg-red-500/10 text-red-400' : 'bg-amber-500/10 text-amber-400'}`}>
                    {txn.status}
                  </span>
                </td>
              </tr>
            ))}
            {(!data?.items || data.items.length === 0) && (
              <tr><td colSpan={6} className="px-4 py-12 text-center text-gray-500">No transactions yet. Import a CSV to get started.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {data && data.pages > 1 && (
        <div className="flex justify-center gap-2">
          {Array.from({ length: data.pages }, (_, i) => i + 1).map(p => (
            <button key={p} onClick={() => setPage(p)} className={`px-3 py-1 rounded text-sm ${p === page ? 'bg-cyan-500 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}>{p}</button>
          ))}
        </div>
      )}
    </div>
  );
}
