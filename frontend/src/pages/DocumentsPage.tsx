import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useCallback } from 'react';
import api, { extractErrorMessage } from '../lib/api';
import UploadZone from '../components/UploadZone';
import FileList from '../components/FileList';
import AnalysisPipeline from '../components/AnalysisPipeline';
import { FileText, BarChart3, Clock, CheckCircle, AlertCircle, X, Eye } from 'lucide-react';
import type { Document, PaginatedResponse, PipelineState } from '../types';

const PIPELINE_STEPS: PipelineState['steps'] = [
  { name: 'ingestion', label: 'Document Ingestion', status: 'pending' as const },
  { name: 'extraction', label: 'Data Extraction', status: 'pending' as const },
  { name: 'normalization', label: 'Normalization', status: 'pending' as const },
  { name: 'validation', label: 'Validation', status: 'pending' as const },
  { name: 'reconciliation', label: 'Reconciliation', status: 'pending' as const },
  { name: 'metrics', label: 'Metrics Calculation', status: 'pending' as const },
];

interface UploadFile {
  id: string;
  name: string;
  type: string;
  size?: number;
  status: 'uploading' | 'processing' | 'completed' | 'error';
  progress?: number;
  error?: string;
}

export default function DocumentsPage() {
  const queryClient = useQueryClient();
  const [uploadFiles, setUploadFiles] = useState<UploadFile[]>([]);
  const [activePipeline, setActivePipeline] = useState<{ docId: string; steps: PipelineState['steps'] } | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [statusFilter, setStatusFilter] = useState('');

  const { data: docs, isLoading } = useQuery<PaginatedResponse<Document>>({
    queryKey: ['documents', statusFilter],
    queryFn: () => api.get('/documents', {
      params: statusFilter ? { status: statusFilter } : {}
    }).then(r => r.data),
  });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return api.post('/documents/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['documents'] }),
    onError: (err) => {
      console.error('Failed to upload document:', extractErrorMessage(err));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/documents/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['documents'] }),
    onError: (err) => {
      console.error('Failed to delete document:', extractErrorMessage(err));
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: async (docId: string) => {
      const steps = PIPELINE_STEPS.map(s => ({ ...s, status: 'pending' as string }));
      setActivePipeline({ docId, steps: steps as PipelineState['steps'] });

      // Simulate pipeline progression
      for (let i = 0; i < steps.length; i++) {
        steps[i].status = 'processing';
        setActivePipeline({ docId, steps: [...steps] as PipelineState['steps'] });
        await new Promise(r => setTimeout(r, 800 + Math.random() * 1200));
        steps[i].status = 'completed';
        setActivePipeline({ docId, steps: [...steps] as PipelineState['steps'] });
      }

      return api.post(`/documents/${docId}/analyze`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setTimeout(() => setActivePipeline(null), 2000);
    },
    onError: () => {
      if (activePipeline) {
        const steps = activePipeline.steps;
        const current = steps.findIndex(s => s.status === 'processing');
        if (current >= 0) {
          steps[current].status = 'error';
          steps[current].message = 'Analysis failed';
          setActivePipeline({ ...activePipeline, steps: [...steps] });
        }
      }
    },
  });

  const handleFilesSelected = useCallback((files: File[]) => {
    const newFiles: UploadFile[] = files.map(f => ({
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      name: f.name,
      type: f.type,
      size: f.size,
      status: 'uploading',
      progress: 0,
    }));
    setUploadFiles(prev => [...newFiles, ...prev]);

    files.forEach((file, i) => {
      const fileId = newFiles[i].id;
      // Simulate upload progress
      let progress = 0;
      const interval = setInterval(() => {
        progress += Math.random() * 30;
        if (progress >= 100) {
          progress = 100;
          clearInterval(interval);
          setUploadFiles(prev => prev.map(f => f.id === fileId ? { ...f, status: 'processing', progress: 100 } : f));
          uploadMutation.mutate(file, {
            onSuccess: () => {
              setUploadFiles(prev => prev.map(f => f.id === fileId ? { ...f, status: 'completed' } : f));
            },
            onError: () => {
              setUploadFiles(prev => prev.map(f => f.id === fileId ? { ...f, status: 'error', error: 'Upload failed' } : f));
            },
          });
        } else {
          setUploadFiles(prev => prev.map(f => f.id === fileId ? { ...f, progress } : f));
        }
      }, 200);
    });
  }, [uploadMutation]);

  const statusCounts = {
    all: docs?.total || 0,
    processing: docs?.items?.filter(d => d.parse_status === 'pending').length || 0,
    completed: docs?.items?.filter(d => d.parse_status === 'parsed').length || 0,
    error: docs?.items?.filter(d => d.parse_status === 'error').length || 0,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Documents</h1>
        <p className="text-gray-400 text-sm mt-1">Upload, process, and analyze financial documents</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { icon: FileText, label: 'Total Documents', value: statusCounts.all, color: 'text-cyan-400' },
          { icon: Clock, label: 'Processing', value: statusCounts.processing, color: 'text-amber-400' },
          { icon: CheckCircle, label: 'Completed', value: statusCounts.completed, color: 'text-green-400' },
          { icon: AlertCircle, label: 'Errors', value: statusCounts.error, color: 'text-red-400' },
        ].map(stat => (
          <div key={stat.label} className="bg-[#1a1a2e] rounded-xl p-4 border border-gray-800">
            <div className="flex items-center gap-2 mb-2">
              <stat.icon size={16} className={stat.color} />
              <span className="text-gray-400 text-xs">{stat.label}</span>
            </div>
            <div className="text-xl font-bold text-white">{stat.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Upload & Pipeline */}
        <div className="lg:col-span-1 space-y-4">
          <UploadZone onFilesSelected={handleFilesSelected} />

          {uploadFiles.length > 0 && (
            <FileList
              files={uploadFiles}
              onDelete={(id) => setUploadFiles(prev => prev.filter(f => f.id !== id))}
            />
          )}

          {activePipeline && (
            <AnalysisPipeline steps={activePipeline.steps} />
          )}
        </div>

        {/* Right: Document List */}
        <div className="lg:col-span-2 space-y-4">
          {/* Status filter tabs */}
          <div className="flex gap-2 flex-wrap">
            {[
              { key: '', label: 'All' },
              { key: 'pending', label: 'Processing' },
              { key: 'parsed', label: 'Completed' },
              { key: 'error', label: 'Errors' },
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

          {/* Document list */}
          <div className="bg-[#1a1a2e] rounded-xl border border-gray-800 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800 text-gray-400">
                    <th className="text-left px-4 py-3 font-medium">File</th>
                    <th className="text-left px-4 py-3 font-medium hidden sm:table-cell">Type</th>
                    <th className="text-left px-4 py-3 font-medium">Status</th>
                    <th className="text-left px-4 py-3 font-medium hidden md:table-cell">Uploaded</th>
                    <th className="text-right px-4 py-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {docs?.items?.map((doc) => (
                    <tr key={doc.id} className="border-b border-gray-800/50 hover:bg-gray-800/20 transition">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="p-2 rounded-lg bg-gray-800/50">
                            <FileText size={16} className="text-gray-400" />
                          </div>
                          <span className="text-white font-medium truncate max-w-[200px]">{doc.original_filename}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-gray-300 hidden sm:table-cell">
                        <span className="bg-gray-800 px-2 py-1 rounded text-xs">{doc.file_type}</span>
                      </td>
                      <td className="px-4 py-3">
                        {doc.parse_status === 'parsed' ? (
                          <span className="inline-flex items-center gap-1.5 text-green-400 text-xs"><CheckCircle size={14} /> Completed</span>
                        ) : doc.parse_status === 'pending' ? (
                          <span className="inline-flex items-center gap-1.5 text-amber-400 text-xs"><Clock size={14} /> Processing</span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 text-red-400 text-xs"><AlertCircle size={14} /> Error</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-xs hidden md:table-cell">
                        {new Date(doc.uploaded_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-1">
                          {doc.parse_status === 'parsed' && (
                            <button
                              onClick={() => analyzeMutation.mutate(doc.id)}
                              className="p-1.5 rounded-lg text-cyan-400 hover:bg-cyan-500/10 transition"
                              title="Analyze"
                            >
                              <BarChart3 size={14} />
                            </button>
                          )}
                          <button
                            onClick={() => setSelectedDoc(doc)}
                            className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-800 transition"
                            title="View details"
                          >
                            <Eye size={14} />
                          </button>
                          <button
                            onClick={() => deleteMutation.mutate(doc.id)}
                            className="p-1.5 rounded-lg text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition"
                            title="Delete"
                          >
                            <X size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {isLoading && (
                    <tr><td colSpan={5} className="px-4 py-12 text-center text-gray-500">Loading...</td></tr>
                  )}
                  {!isLoading && (!docs?.items || docs.items.length === 0) && (
                    <tr><td colSpan={5} className="px-4 py-12 text-center text-gray-500">No documents uploaded yet.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* Document Detail Modal */}
      {selectedDoc && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setSelectedDoc(null)}>
          <div className="bg-[#1a1a2e] rounded-2xl border border-gray-800 w-full max-w-lg p-6 space-y-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <h2 className="text-white text-lg font-semibold">Document Details</h2>
              <button onClick={() => setSelectedDoc(null)} className="text-gray-400 hover:text-white"><X size={20} /></button>
            </div>
            <div className="space-y-3">
              {[
                { label: 'Filename', value: selectedDoc.original_filename },
                { label: 'Type', value: selectedDoc.file_type },
                { label: 'Status', value: selectedDoc.parse_status },
                { label: 'Uploaded', value: new Date(selectedDoc.uploaded_at).toLocaleString() },
              ].map(item => (
                <div key={item.label} className="flex justify-between py-2 border-b border-gray-800/50">
                  <span className="text-gray-400 text-sm">{item.label}</span>
                  <span className="text-white text-sm font-medium">{item.value}</span>
                </div>
              ))}
            </div>

            {/* Pipeline preview */}
            <div>
              <h3 className="text-white text-sm font-medium mb-3">Analysis Pipeline</h3>
              <AnalysisPipeline
                steps={PIPELINE_STEPS.map(s => ({
                  ...s,
                  status: selectedDoc.parse_status === 'parsed' ? 'completed' as const : 'pending' as const,
                }))}
                compact
              />
            </div>

            <button onClick={() => setSelectedDoc(null)}
              className="w-full px-4 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm transition">
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
