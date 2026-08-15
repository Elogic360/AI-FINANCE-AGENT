import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import type { PnLData, BalanceSheetData } from '../types';

type Tab = 'pnl' | 'balance-sheet' | 'cash-flow' | 'trial-balance';

export default function ReportsPage() {
  const [tab, setTab] = useState<Tab>('pnl');
  const today = new Date().toISOString().split('T')[0];
  const startDate = '2026-01-01';

  const { data: pnl } = useQuery<PnLData>({ queryKey: ['pnl'], queryFn: () => api.get('/reports/pnl', { params: { start_date: startDate, end_date: today } }).then(r => r.data), enabled: tab === 'pnl' });
  const { data: bs } = useQuery<BalanceSheetData>({ queryKey: ['bs'], queryFn: () => api.get('/reports/balance-sheet', { params: { as_of_date: today } }).then(r => r.data), enabled: tab === 'balance-sheet' });
  const { data: tb } = useQuery({ queryKey: ['tb'], queryFn: () => api.get('/reports/trial-balance').then(r => r.data), enabled: tab === 'trial-balance' });

  const tabs: { key: Tab; label: string }[] = [
    { key: 'pnl', label: 'Profit & Loss' },
    { key: 'balance-sheet', label: 'Balance Sheet' },
    { key: 'trial-balance', label: 'Trial Balance' },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Reports</h1>

      <div className="flex gap-2 border-b border-gray-800 pb-2">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition ${tab === t.key ? 'bg-[#1a1a2e] text-cyan-400 border-b-2 border-cyan-400' : 'text-gray-400 hover:text-white'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'pnl' && pnl && (
        <div className="bg-[#1a1a2e] rounded-xl p-6 border border-gray-800 space-y-4">
          <h2 className="text-white font-semibold">Profit & Loss Statement</h2>
          <p className="text-gray-400 text-sm">{pnl.period_start} to {pnl.period_end}</p>
          <div className="space-y-2">
            <div className="text-green-400 font-medium">Revenue</div>
            {pnl.revenue.map(r => (
              <div key={r.account_id} className="flex justify-between pl-4 text-sm">
                <span className="text-gray-300">{r.account_code} - {r.account_name}</span>
                <span className="text-white">{parseFloat(r.balance).toLocaleString()} {pnl.currency}</span>
              </div>
            ))}
            <div className="flex justify-between font-semibold border-t border-gray-700 pt-2">
              <span className="text-green-400">Total Revenue</span>
              <span className="text-green-400">{parseFloat(pnl.total_revenue).toLocaleString()} {pnl.currency}</span>
            </div>
          </div>
          <div className="space-y-2">
            <div className="text-red-400 font-medium">Expenses</div>
            {pnl.expenses.map(e => (
              <div key={e.account_id} className="flex justify-between pl-4 text-sm">
                <span className="text-gray-300">{e.account_code} - {e.account_name}</span>
                <span className="text-white">{parseFloat(e.balance).toLocaleString()} {pnl.currency}</span>
              </div>
            ))}
            <div className="flex justify-between font-semibold border-t border-gray-700 pt-2">
              <span className="text-red-400">Total Expenses</span>
              <span className="text-red-400">{parseFloat(pnl.total_expenses).toLocaleString()} {pnl.currency}</span>
            </div>
          </div>
          <div className="flex justify-between font-bold text-lg border-t border-gray-600 pt-3">
            <span className="text-white">Net Income</span>
            <span className={parseFloat(pnl.net_income) >= 0 ? 'text-green-400' : 'text-red-400'}>
              {parseFloat(pnl.net_income).toLocaleString()} {pnl.currency}
            </span>
          </div>
        </div>
      )}

      {tab === 'balance-sheet' && bs && (
        <div className="bg-[#1a1a2e] rounded-xl p-6 border border-gray-800 space-y-4">
          <h2 className="text-white font-semibold">Balance Sheet</h2>
          <p className="text-gray-400 text-sm">As of {bs.as_of_date}</p>
          {[
            { title: 'Assets', items: bs.assets, total: bs.total_assets, color: 'text-blue-400' },
            { title: 'Liabilities', items: bs.liabilities, total: bs.total_liabilities, color: 'text-amber-400' },
            { title: 'Equity', items: bs.equity, total: bs.total_equity, color: 'text-purple-400' },
          ].map(section => (
            <div key={section.title} className="space-y-2">
              <div className={`font-medium ${section.color}`}>{section.title}</div>
              {section.items.map(i => (
                <div key={i.account_id} className="flex justify-between pl-4 text-sm">
                  <span className="text-gray-300">{i.account_code} - {i.account_name}</span>
                  <span className="text-white">{parseFloat(i.balance).toLocaleString()} {bs.currency}</span>
                </div>
              ))}
              <div className="flex justify-between font-semibold border-t border-gray-700 pt-2">
                <span className={section.color}>Total {section.title}</span>
                <span className={section.color}>{parseFloat(section.total).toLocaleString()} {bs.currency}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === 'trial-balance' && tb && (
        <div className="bg-[#1a1a2e] rounded-xl p-6 border border-gray-800">
          <h2 className="text-white font-semibold mb-4">Trial Balance</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400">
                <th className="text-left px-3 py-2">Account</th>
                <th className="text-right px-3 py-2">Debit</th>
                <th className="text-right px-3 py-2">Credit</th>
              </tr>
            </thead>
            <tbody>
              {tb.accounts?.map((a: any) => (
                <tr key={a.account_id} className="border-b border-gray-800/50">
                  <td className="px-3 py-2 text-white">{a.account_code} - {a.account_name}</td>
                  <td className="px-3 py-2 text-right text-gray-300">{a.debit > 0 ? a.debit.toLocaleString() : '—'}</td>
                  <td className="px-3 py-2 text-right text-gray-300">{a.credit > 0 ? a.credit.toLocaleString() : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex justify-between font-bold border-t border-gray-600 pt-3 mt-3">
            <span className="text-white">Total</span>
            <span className={tb.balanced ? 'text-green-400' : 'text-red-400'}>
              Dr {Number(tb.total_debits).toLocaleString()} / Cr {Number(tb.total_credits).toLocaleString()} {tb.balanced ? '✓ Balanced' : '✗ Unbalanced'}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
