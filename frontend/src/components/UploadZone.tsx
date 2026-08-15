import { useCallback, useState, useRef } from 'react';
import { Upload, FileUp, AlertCircle } from 'lucide-react';

interface Props {
  onFilesSelected: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
  maxSizeMB?: number;
  disabled?: boolean;
}

const ALLOWED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'text/csv',
  'image/png',
  'image/jpeg',
];

const ALLOWED_EXTENSIONS = '.pdf,.docx,.xlsx,.csv,.png,.jpg,.jpeg';

export default function UploadZone({ onFilesSelected, accept = ALLOWED_EXTENSIONS, multiple = true, maxSizeMB = 25, disabled = false }: Props) {
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateFiles = useCallback((files: File[]): File[] => {
    setError(null);
    const valid: File[] = [];
    const maxSize = maxSizeMB * 1024 * 1024;

    for (const file of files) {
      if (file.size > maxSize) {
        setError(`${file.name} exceeds ${maxSizeMB}MB limit`);
        continue;
      }
      if (ALLOWED_TYPES.length > 0 && !ALLOWED_TYPES.includes(file.type) && !file.name.match(/\.(pdf|docx|xlsx|csv|png|jpe?g)$/i)) {
        setError(`${file.name} is not a supported file type`);
        continue;
      }
      valid.push(file);
    }
    return valid;
  }, [maxSizeMB]);

  const handleFiles = useCallback((files: FileList | File[]) => {
    const arr = Array.from(files);
    const valid = validateFiles(arr);
    if (valid.length > 0) onFilesSelected(valid);
  }, [validateFiles, onFilesSelected]);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
    else if (e.type === 'dragleave') setDragActive(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (!disabled && e.dataTransfer.files?.length) handleFiles(e.dataTransfer.files);
  }, [disabled, handleFiles]);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (!disabled && e.target.files?.length) handleFiles(e.target.files);
    e.target.value = '';
  }, [disabled, handleFiles]);

  return (
    <div className="space-y-2">
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => !disabled && inputRef.current?.click()}
        className={`relative rounded-xl border-2 border-dashed p-8 text-center cursor-pointer transition-all ${
          disabled
            ? 'border-gray-700 bg-gray-800/30 opacity-50 cursor-not-allowed'
            : dragActive
            ? 'border-cyan-400 bg-cyan-500/10'
            : 'border-gray-700 bg-[#1a1a2e] hover:border-cyan-500/50 hover:bg-[#1a1a2e]/80'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={handleChange}
          className="hidden"
          disabled={disabled}
        />
        <div className="flex flex-col items-center gap-3">
          {dragActive ? (
            <FileUp size={40} className="text-cyan-400" />
          ) : (
            <Upload size={40} className="text-gray-500" />
          )}
          <div>
            <p className="text-gray-300 font-medium">
              {dragActive ? 'Drop files here' : 'Drag & drop files here'}
            </p>
            <p className="text-gray-500 text-sm mt-1">or click to browse</p>
          </div>
          <p className="text-gray-600 text-xs">
            PDF, DOCX, XLSX, CSV, PNG, JPG &middot; Max {maxSizeMB}MB per file
          </p>
        </div>
      </div>
      {error && (
        <div className="flex items-center gap-2 text-red-400 text-sm">
          <AlertCircle size={14} />
          {error}
        </div>
      )}
    </div>
  );
}
