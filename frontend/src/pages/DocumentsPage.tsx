import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import { Upload, FileText, CheckCircle, Clock, AlertCircle } from 'lucide-react';

export default function DocumentsPage() {
  const queryClient = useQueryClient();
  const { data: docs } = useQuery({ queryKey: ['documents'], queryFn: () => api.get('/documents').then(r => r.data) });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return api.post('/documents/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['documents'] }),
  });

  const statusIcon = (status: string) => {
    if (status === 'parsed') return <CheckCircle size={16} className="text-green-400" />;
    if (status === 'pending') return <Clock size={16} className="text-amber-400" />;
    return <AlertCircle size={16} className="text-red-400" />;
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Documents</h1>

      <div className="bg-[#1a1a2e] rounded-xl p-8 border-2 border-dashed border-gray-700 hover:border-cyan-500/50 transition text-center">
        <Upload size={40} className="mx-auto text-gray-500 mb-3" />
        <p className="text-gray-400 mb-3">Drop files here or click to upload</p>
        <p className="text-gray-500 text-xs mb-4">Supports PDF, DOCX, XLSX, CSV, images</p>
        <label className="inline-flex items-center gap-2 bg-cyan-500 hover:bg-cyan-600 text-white px-5 py-2.5 rounded-lg cursor-pointer transition text-sm font-medium">
          <Upload size={16} /> Choose Files
          <input type="file" accept=".pdf,.docx,.xlsx,.csv,.jpg,.png" multiple className="hidden"
            onChange={e => { Array.from(e.target.files || []).forEach(f => uploadMutation.mutate(f)); }} />
        </label>
      </div>

      <div className="bg-[#1a1a2e] rounded-xl border border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-gray-400">
              <th className="text-left px-4 py-3 font-medium">File</th>
              <th className="text-left px-4 py-3 font-medium">Type</th>
              <th className="text-left px-4 py-3 font-medium">Status</th>
              <th className="text-left px-4 py-3 font-medium">Uploaded</th>
            </tr>
          </thead>
          <tbody>
            {docs?.items?.map((doc: any) => (
              <tr key={doc.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                <td className="px-4 py-3 text-white flex items-center gap-2"><FileText size={16} className="text-gray-400" /> {doc.original_filename}</td>
                <td className="px-4 py-3 text-gray-300">{doc.file_type}</td>
                <td className="px-4 py-3 flex items-center gap-1.5">{statusIcon(doc.parse_status)} <span className="text-gray-300">{doc.parse_status}</span></td>
                <td className="px-4 py-3 text-gray-400 text-xs">{new Date(doc.uploaded_at).toLocaleDateString()}</td>
              </tr>
            ))}
            {(!docs?.items || docs.items.length === 0) && (
              <tr><td colSpan={4} className="px-4 py-12 text-center text-gray-500">No documents uploaded yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
