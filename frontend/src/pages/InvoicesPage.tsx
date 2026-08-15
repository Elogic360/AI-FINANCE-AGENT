import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import api from '../lib/api';
import { Plus, X, Eye, Send, CheckCircle, AlertCircle, FileText, CreditCard, Trash2 } from 'lucide-react';
import type { Invoice, PaginatedResponse } from '../types';

function formatTZS(amount: number): string {
  return `TZS ${amount.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

const STATUS_CONFIG = {
  draft: { color: 'bg-gray-500/10 text-gray-400', icon: FileText, label: 'Draft' },
  sent: { color: 'bg-blue-500/10 text-blue-400', icon: Send, label: 'Sent' },
  paid: { color: 'bg-green-500/10 text-green-400', icon: CheckCircle, label: 'Paid' },
  overdue: { color: 'bg-red-500/10 text-red-400', icon: AlertCircle, label: 'Overdue' },
  cancelled: { color: 'bg-gray-600/10 text-gray-500', icon: X, label: 'Cancelled' },
};

type StatusFilter = '' | 'draft' | 'sent' | 'paid' | 'overdue';

export default function InvoicesPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [showPaymentForm, setShowPaymentForm] = useState<string | null>(null);
  const [paymentAmount, setPaymentAmount] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [paymentRef, setPaymentRef] = useState('');

  // Create invoice form
  const [newInvoice, setNewInvoice] = useState({
    customer_name: '',
    customer_email: '',
    issue_date: new Date().toISOString().split('T')[0],
    due_date: new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0],
    notes: '',
    items: [{ description: '', quantity: 1, unit_price: '' }],
  });

  const { data: invoices, isLoading } = useQuery<PaginatedResponse<Invoice>>({
    queryKey: ['invoices', statusFilter],
    queryFn: () => api.get('/invoices', { params: statusFilter ? { status: statusFilter } : {} }).then(r => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (inv: typeof newInvoice) => api.post('/invoices', inv),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      setShowCreateForm(false);
      resetForm();
    },
  });

  const paymentMutation = useMutation({
    mutationFn: ({ invoiceId, ...data }: { invoiceId: string; amount: string; method: string; reference: string }) =>
      api.post(`/invoices/${invoiceId}/payments`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      setShowPaymentForm(null);
      setPaymentAmount('');
      setPaymentRef('');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/invoices/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['invoices'] }),
  });

  const resetForm = () => {
    setNewInvoice({
      customer_name: '',
      customer_email: '',
      issue_date: new Date().toISOString().split('T')[0],
      due_date: new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0],
      notes: '',
      items: [{ description: '', quantity: 1, unit_price: '' }],
    });
  };

  const addItem = () => {
    setNewInvoice(prev => ({
      ...prev,
      items: [...prev.items, { description: '', quantity: 1, unit_price: '' }],
    }));
  };

  const removeItem = (index: number) => {
    setNewInvoice(prev => ({
      ...prev,
      items: prev.items.filter((_, i) => i !== index),
    }));
  };

  const updateItem = (index: number, field: string, value: string | number) => {
    setNewInvoice(prev => ({
      ...prev,
      items: prev.items.map((item, i) => i === index ? { ...item, [field]: value } : item),
    }));
  };

  const subtotal = newInvoice.items.reduce((sum, item) => sum + (item.quantity * parseFloat(item.unit_price || '0')), 0);
  const tax = subtotal * 0.18; // 18% VAT
  const total = subtotal + tax;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Invoices</h1>
          <p className="text-gray-400 text-sm mt-1">Manage invoices and track payments</p>
        </div>
        <button
          onClick={() => setShowCreateForm(true)}
          className="flex items-center gap-2 bg-cyan-500 hover:bg-cyan-600 text-white px-4 py-2 rounded-lg transition text-sm font-medium"
        >
          <Plus size={16} /> Create Invoice
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Total Invoices', value: invoices?.total || 0, color: 'text-cyan-400' },
          { label: 'Paid', value: invoices?.items?.filter(i => i.status === 'paid').length || 0, color: 'text-green-400' },
          { label: 'Pending', value: invoices?.items?.filter(i => i.status === 'sent').length || 0, color: 'text-amber-400' },
          { label: 'Overdue', value: invoices?.items?.filter(i => i.status === 'overdue').length || 0, color: 'text-red-400' },
        ].map(stat => (
          <div key={stat.label} className="bg-[#1a1a2e] rounded-xl p-4 border border-gray-800">
            <p className="text-gray-400 text-xs mb-1">{stat.label}</p>
            <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Status Filter */}
      <div className="flex gap-2 flex-wrap">
        {[
          { key: '' as StatusFilter, label: 'All' },
          { key: 'draft' as StatusFilter, label: 'Draft' },
          { key: 'sent' as StatusFilter, label: 'Sent' },
          { key: 'paid' as StatusFilter, label: 'Paid' },
          { key: 'overdue' as StatusFilter, label: 'Overdue' },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setStatusFilter(tab.key)}
            className={`px-3 py-1.5 rounded-lg text-sm transition ${
              statusFilter === tab.key
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                : 'bg-gray-800/50 text-gray-400 border border-gray-700 hover:text-white'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Invoice List */}
      <div className="bg-[#1a1a2e] rounded-xl border border-gray-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400">
                <th className="text-left px-4 py-3 font-medium">Invoice #</th>
                <th className="text-left px-4 py-3 font-medium">Customer</th>
                <th className="text-left px-4 py-3 font-medium hidden sm:table-cell">Issue Date</th>
                <th className="text-left px-4 py-3 font-medium hidden md:table-cell">Due Date</th>
                <th className="text-right px-4 py-3 font-medium">Amount</th>
                <th className="text-left px-4 py-3 font-medium">Status</th>
                <th className="text-right px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {invoices?.items?.map(inv => {
                const cfg = STATUS_CONFIG[inv.status];
                const StatusIcon = cfg.icon;
                return (
                  <tr key={inv.id} className="border-b border-gray-800/50 hover:bg-gray-800/20 transition cursor-pointer" onClick={() => setSelectedInvoice(inv)}>
                    <td className="px-4 py-3 text-white font-medium">{inv.invoice_number}</td>
                    <td className="px-4 py-3 text-gray-300">{inv.customer_name}</td>
                    <td className="px-4 py-3 text-gray-400 hidden sm:table-cell">{inv.issue_date}</td>
                    <td className="px-4 py-3 text-gray-400 hidden md:table-cell">{inv.due_date}</td>
                    <td className="px-4 py-3 text-right text-white font-medium">{formatTZS(parseFloat(inv.total_amount))}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium ${cfg.color}`}>
                        <StatusIcon size={12} /> {cfg.label}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1" onClick={e => e.stopPropagation()}>
                        {(inv.status === 'sent' || inv.status === 'overdue') && (
                          <button onClick={() => { setShowPaymentForm(inv.id); setPaymentAmount(inv.total_amount); }}
                            className="p-1.5 rounded-lg text-green-400 hover:bg-green-500/10 transition" title="Record Payment">
                            <CreditCard size={14} />
                          </button>
                        )}
                        <button onClick={() => setSelectedInvoice(inv)}
                          className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-800 transition" title="View">
                          <Eye size={14} />
                        </button>
                        {inv.status === 'draft' && (
                          <button onClick={() => deleteMutation.mutate(inv.id)}
                            className="p-1.5 rounded-lg text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition" title="Delete">
                            <Trash2 size={14} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {isLoading && (
                <tr><td colSpan={7} className="px-4 py-12 text-center text-gray-500">Loading...</td></tr>
              )}
              {!isLoading && (!invoices?.items || invoices.items.length === 0) && (
                <tr><td colSpan={7} className="px-4 py-12 text-center text-gray-500">No invoices yet. Create your first invoice.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Invoice Modal */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-start justify-center p-4 overflow-y-auto" onClick={() => setShowCreateForm(false)}>
          <div className="bg-[#1a1a2e] rounded-2xl border border-gray-800 w-full max-w-2xl p-6 space-y-4 my-8" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <h2 className="text-white text-lg font-semibold">Create Invoice</h2>
              <button onClick={() => setShowCreateForm(false)} className="text-gray-400 hover:text-white"><X size={20} /></button>
            </div>
            <form onSubmit={e => { e.preventDefault(); createMutation.mutate(newInvoice); }} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-gray-400 text-sm mb-1">Customer Name</label>
                  <input type="text" value={newInvoice.customer_name} onChange={e => setNewInvoice({ ...newInvoice, customer_name: e.target.value })}
                    placeholder="Customer name" className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500" required />
                </div>
                <div>
                  <label className="block text-gray-400 text-sm mb-1">Customer Email</label>
                  <input type="email" value={newInvoice.customer_email} onChange={e => setNewInvoice({ ...newInvoice, customer_email: e.target.value })}
                    placeholder="customer@email.com" className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500" />
                </div>
                <div>
                  <label className="block text-gray-400 text-sm mb-1">Issue Date</label>
                  <input type="date" value={newInvoice.issue_date} onChange={e => setNewInvoice({ ...newInvoice, issue_date: e.target.value })}
                    className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500" required />
                </div>
                <div>
                  <label className="block text-gray-400 text-sm mb-1">Due Date</label>
                  <input type="date" value={newInvoice.due_date} onChange={e => setNewInvoice({ ...newInvoice, due_date: e.target.value })}
                    className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500" required />
                </div>
              </div>

              {/* Line Items */}
              <div>
                <label className="block text-gray-400 text-sm mb-2">Line Items</label>
                <div className="space-y-2">
                  {newInvoice.items.map((item, i) => (
                    <div key={i} className="flex gap-2 items-start">
                      <input type="text" value={item.description} onChange={e => updateItem(i, 'description', e.target.value)}
                        placeholder="Description" className="flex-1 bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-cyan-500" />
                      <input type="number" value={item.quantity} onChange={e => updateItem(i, 'quantity', parseInt(e.target.value) || 1)}
                        placeholder="Qty" min="1" className="w-16 bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-cyan-500" />
                      <input type="number" value={item.unit_price} onChange={e => updateItem(i, 'unit_price', e.target.value)}
                        placeholder="Unit Price (TZS)" className="w-32 bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-cyan-500" />
                      <span className="text-gray-400 text-sm w-24 text-right py-2">
                        {formatTZS(item.quantity * parseFloat(item.unit_price || '0'))}
                      </span>
                      {newInvoice.items.length > 1 && (
                        <button type="button" onClick={() => removeItem(i)} className="p-2 text-gray-500 hover:text-red-400">
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
                <button type="button" onClick={addItem}
                  className="mt-2 text-cyan-400 hover:text-cyan-300 text-sm flex items-center gap-1">
                  <Plus size={14} /> Add Item
                </button>
              </div>

              {/* Totals */}
              <div className="bg-gray-800/30 rounded-lg p-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Subtotal</span>
                  <span className="text-white">{formatTZS(subtotal)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">VAT (18%)</span>
                  <span className="text-white">{formatTZS(tax)}</span>
                </div>
                <div className="flex justify-between text-base font-bold border-t border-gray-700 pt-2">
                  <span className="text-white">Total</span>
                  <span className="text-cyan-400">{formatTZS(total)}</span>
                </div>
              </div>

              <div>
                <label className="block text-gray-400 text-sm mb-1">Notes</label>
                <textarea value={newInvoice.notes} onChange={e => setNewInvoice({ ...newInvoice, notes: e.target.value })}
                  placeholder="Additional notes..." rows={3}
                  className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500 resize-none" />
              </div>

              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowCreateForm(false)}
                  className="flex-1 px-4 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm transition">
                  Cancel
                </button>
                <button type="button" onClick={() => { createMutation.mutate({ ...newInvoice }); }}
                  className="px-4 py-2.5 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-sm transition">
                  Save as Draft
                </button>
                <button type="submit" disabled={createMutation.isPending}
                  className="flex-1 px-4 py-2.5 bg-cyan-500 hover:bg-cyan-600 text-white rounded-lg text-sm font-medium transition disabled:opacity-50">
                  {createMutation.isPending ? 'Creating...' : 'Create & Send'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Invoice Detail Modal */}
      {selectedInvoice && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-start justify-center p-4 overflow-y-auto" onClick={() => setSelectedInvoice(null)}>
          <div className="bg-[#1a1a2e] rounded-2xl border border-gray-800 w-full max-w-lg p-6 space-y-4 my-8" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <h2 className="text-white text-lg font-semibold">Invoice {selectedInvoice.invoice_number}</h2>
              <button onClick={() => setSelectedInvoice(null)} className="text-gray-400 hover:text-white"><X size={20} /></button>
            </div>
            <div className="space-y-3">
              {[
                { label: 'Customer', value: selectedInvoice.customer_name },
                { label: 'Email', value: selectedInvoice.customer_email || '—' },
                { label: 'Issue Date', value: selectedInvoice.issue_date },
                { label: 'Due Date', value: selectedInvoice.due_date },
                { label: 'Status', value: STATUS_CONFIG[selectedInvoice.status].label },
                { label: 'Subtotal', value: formatTZS(parseFloat(selectedInvoice.subtotal)) },
                { label: 'Tax', value: formatTZS(parseFloat(selectedInvoice.tax_amount)) },
                { label: 'Total', value: formatTZS(parseFloat(selectedInvoice.total_amount)), color: 'text-cyan-400' },
              ].map(item => (
                <div key={item.label} className="flex justify-between py-2 border-b border-gray-800/50">
                  <span className="text-gray-400 text-sm">{item.label}</span>
                  <span className={`text-sm font-medium ${item.color || 'text-white'}`}>{item.value}</span>
                </div>
              ))}
            </div>

            {/* Line Items */}
            {selectedInvoice.items && selectedInvoice.items.length > 0 && (
              <div>
                <h3 className="text-white text-sm font-medium mb-2">Line Items</h3>
                <div className="bg-gray-800/30 rounded-lg overflow-hidden">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-gray-700 text-gray-400">
                        <th className="text-left px-3 py-2">Description</th>
                        <th className="text-right px-3 py-2">Qty</th>
                        <th className="text-right px-3 py-2">Price</th>
                        <th className="text-right px-3 py-2">Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedInvoice.items.map(item => (
                        <tr key={item.id} className="border-b border-gray-700/50">
                          <td className="px-3 py-2 text-gray-300">{item.description}</td>
                          <td className="px-3 py-2 text-right text-gray-300">{item.quantity}</td>
                          <td className="px-3 py-2 text-right text-gray-300">{formatTZS(parseFloat(item.unit_price))}</td>
                          <td className="px-3 py-2 text-right text-white">{formatTZS(parseFloat(item.amount))}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Payments */}
            {selectedInvoice.payments && selectedInvoice.payments.length > 0 && (
              <div>
                <h3 className="text-white text-sm font-medium mb-2">Payments</h3>
                <div className="space-y-2">
                  {selectedInvoice.payments.map(p => (
                    <div key={p.id} className="flex justify-between items-center bg-gray-800/30 rounded-lg px-3 py-2">
                      <div>
                        <p className="text-white text-sm">{formatTZS(parseFloat(p.amount))}</p>
                        <p className="text-gray-500 text-xs">{p.method} &middot; {p.payment_date}</p>
                      </div>
                      {p.reference && <span className="text-gray-400 text-xs">{p.reference}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <button onClick={() => setSelectedInvoice(null)}
              className="w-full px-4 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm transition">
              Close
            </button>
          </div>
        </div>
      )}

      {/* Payment Modal */}
      {showPaymentForm && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setShowPaymentForm(null)}>
          <div className="bg-[#1a1a2e] rounded-2xl border border-gray-800 w-full max-w-md p-6 space-y-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <h2 className="text-white text-lg font-semibold">Record Payment</h2>
              <button onClick={() => setShowPaymentForm(null)} className="text-gray-400 hover:text-white"><X size={20} /></button>
            </div>
            <form onSubmit={e => { e.preventDefault(); paymentMutation.mutate({ invoiceId: showPaymentForm, amount: paymentAmount, method: paymentMethod, reference: paymentRef }); }} className="space-y-4">
              <div>
                <label className="block text-gray-400 text-sm mb-1">Amount (TZS)</label>
                <input type="number" step="0.01" value={paymentAmount} onChange={e => setPaymentAmount(e.target.value)}
                  className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500" required />
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-1">Payment Method</label>
                <select value={paymentMethod} onChange={e => setPaymentMethod(e.target.value)}
                  className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500">
                  <option value="cash">Cash</option>
                  <option value="bank_transfer">Bank Transfer</option>
                  <option value="mobile_money">Mobile Money</option>
                  <option value="card">Card</option>
                  <option value="cheque">Cheque</option>
                </select>
              </div>
              <div>
                <label className="block text-gray-400 text-sm mb-1">Reference</label>
                <input type="text" value={paymentRef} onChange={e => setPaymentRef(e.target.value)}
                  placeholder="Transaction reference" className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500" />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowPaymentForm(null)}
                  className="flex-1 px-4 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm transition">
                  Cancel
                </button>
                <button type="submit" disabled={paymentMutation.isPending}
                  className="flex-1 px-4 py-2.5 bg-green-500 hover:bg-green-600 text-white rounded-lg text-sm font-medium transition disabled:opacity-50">
                  {paymentMutation.isPending ? 'Recording...' : 'Record Payment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
