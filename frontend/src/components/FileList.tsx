import { FileText, CheckCircle, AlertCircle, Trash2, Play, Loader2 } from 'lucide-react';

interface FileItem {
  id: string;
  name: string;
  type: string;
  size?: number;
  status: 'uploading' | 'processing' | 'completed' | 'error';
  progress?: number;
  error?: string;
}

interface Props {
  files: FileItem[];
  onDelete?: (id: string) => void;
  onAnalyze?: (id: string) => void;
}

function formatSize(bytes?: number): string {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function StatusBadge({ status }: { status: FileItem['status'] }) {
  const configs = {
    uploading: { icon: Loader2, color: 'text-blue-400 bg-blue-500/10', label: 'Uploading', spin: true },
    processing: { icon: Loader2, color: 'text-amber-400 bg-amber-500/10', label: 'Processing', spin: true },
    completed: { icon: CheckCircle, color: 'text-green-400 bg-green-500/10', label: 'Completed', spin: false },
    error: { icon: AlertCircle, color: 'text-red-400 bg-red-500/10', label: 'Error', spin: false },
  };
  const cfg = configs[status];
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${cfg.color}`}>
      <Icon size={12} className={cfg.spin ? 'animate-spin' : ''} />
      {cfg.label}
    </span>
  );
}

export default function FileList({ files, onDelete, onAnalyze }: Props) {
  if (files.length === 0) {
    return (
      <div className="bg-[#1a1a2e] rounded-xl border border-gray-800 p-8 text-center">
        <FileText size={32} className="mx-auto text-gray-600 mb-2" />
        <p className="text-gray-500 text-sm">No files uploaded yet</p>
      </div>
    );
  }

  return (
    <div className="bg-[#1a1a2e] rounded-xl border border-gray-800 overflow-hidden">
      <div className="divide-y divide-gray-800/50">
        {files.map(file => (
          <div key={file.id} className="flex items-center gap-4 px-4 py-3 hover:bg-gray-800/20 transition">
            <div className="p-2 rounded-lg bg-gray-800/50">
              <FileText size={18} className="text-gray-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white text-sm font-medium truncate">{file.name}</p>
              <p className="text-gray-500 text-xs">{file.type} &middot; {formatSize(file.size)}</p>
              {file.status === 'uploading' && file.progress !== undefined && (
                <div className="mt-1.5 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                  <div className="h-full bg-cyan-500 rounded-full transition-all" style={{ width: `${file.progress}%` }} />
                </div>
              )}
              {file.error && <p className="text-red-400 text-xs mt-1">{file.error}</p>}
            </div>
            <StatusBadge status={file.status} />
            <div className="flex items-center gap-1">
              {file.status === 'completed' && onAnalyze && (
                <button
                  onClick={() => onAnalyze(file.id)}
                  className="p-1.5 rounded-lg text-cyan-400 hover:bg-cyan-500/10 transition"
                  title="Analyze"
                >
                  <Play size={14} />
                </button>
              )}
              {onDelete && (
                <button
                  onClick={() => onDelete(file.id)}
                  className="p-1.5 rounded-lg text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition"
                  title="Delete"
                >
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
