import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import { CheckCircle, Clock } from 'lucide-react';
import type { JournalEntry } from '../types';

export default function JournalPage() {
  const queryClient = useQueryClient();
  const { data: entries } = useQuery<JournalEntry[]>({ queryKey: ['journal'], queryFn: () => api.get('/journal-entries').then(r => r.data) });

  const approveMutation = useMutation({
    mutationFn: (id: string) => api.post(`/journal-entries/${id}/approve`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['journal'] }),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Journal Entries</h1>

      <div className="bg-[#1a1a2e] rounded-xl border border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-gray-400">
              <th className="text-left px-4 py-3 font-medium">Date</th>
              <th className="text-left px-4 py-3 font-medium">Memo</th>
              <th className="text-left px-4 py-3 font-medium">Created By</th>
              <th className="text-left px-4 py-3 font-medium">Status</th>
              <th className="text-right px-4 py-3 font-medium">Action</th>
            </tr>
          </thead>
          <tbody>
            {entries?.map((entry: any) => (
              <tr key={entry.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                <td className="px-4 py-3 text-gray-300">{entry.entry_date}</td>
                <td className="px-4 py-3 text-white">{entry.memo || '—'}</td>
                <td className="px-4 py-3 text-gray-300">{entry.created_by}</td>
                <td className="px-4 py-3">
                  {entry.is_draft ? (
                    <span className="flex items-center gap-1 text-amber-400 text-xs"><Clock size={14} /> Draft</span>
                  ) : (
                    <span className="flex items-center gap-1 text-green-400 text-xs"><CheckCircle size={14} /> Posted</span>
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  {entry.is_draft && (
                    <button onClick={() => approveMutation.mutate(entry.id)}
                      className="text-cyan-400 hover:text-cyan-300 text-xs font-medium">
                      Approve
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {(!entries || entries.length === 0) && (
              <tr><td colSpan={5} className="px-4 py-12 text-center text-gray-500">No journal entries yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
