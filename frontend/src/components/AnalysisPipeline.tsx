import { CheckCircle, Loader2, AlertCircle, Circle } from 'lucide-react';
import type { PipelineStep } from '../types';

interface Step {
  name: PipelineStep;
  label: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  message?: string;
}

interface Props {
  steps: Step[];
  compact?: boolean;
}

const stepIcons: Record<PipelineStep, string> = {
  ingestion: '📥',
  extraction: '🔍',
  normalization: '⚙️',
  validation: '✅',
  reconciliation: '🔄',
  metrics: '📊',
};

function StepIcon({ status }: { status: Step['status'] }) {
  switch (status) {
    case 'completed':
      return <CheckCircle size={20} className="text-green-400" />;
    case 'processing':
      return <Loader2 size={20} className="text-cyan-400 animate-spin" />;
    case 'error':
      return <AlertCircle size={20} className="text-red-400" />;
    default:
      return <Circle size={20} className="text-gray-600" />;
  }
}

export default function AnalysisPipeline({ steps, compact = false }: Props) {
  const currentIndex = steps.findIndex(s => s.status === 'processing');

  if (compact) {
    return (
      <div className="flex items-center gap-1">
        {steps.map((step, i) => (
          <div key={step.name} className="flex items-center">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium border-2 transition ${
                step.status === 'completed'
                  ? 'bg-green-500/20 border-green-500 text-green-400'
                  : step.status === 'processing'
                  ? 'bg-cyan-500/20 border-cyan-500 text-cyan-400 animate-pulse'
                  : step.status === 'error'
                  ? 'bg-red-500/20 border-red-500 text-red-400'
                  : 'bg-gray-800 border-gray-700 text-gray-500'
              }`}
              title={step.label}
            >
              {step.status === 'completed' ? '✓' : step.status === 'error' ? '!' : i + 1}
            </div>
            {i < steps.length - 1 && (
              <div className={`w-6 h-0.5 ${step.status === 'completed' ? 'bg-green-500' : 'bg-gray-700'}`} />
            )}
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="bg-[#1a1a2e] rounded-xl border border-gray-800 p-6">
      <h3 className="text-white font-semibold mb-6">Analysis Pipeline</h3>
      <div className="space-y-1">
        {steps.map((step, i) => (
          <div key={step.name}>
            <div className={`flex items-center gap-4 p-3 rounded-lg transition ${
              step.status === 'processing' ? 'bg-cyan-500/5 border border-cyan-500/20' : ''
            }`}>
              <StepIcon status={step.status} />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm">{stepIcons[step.name]}</span>
                  <span className={`font-medium text-sm ${
                    step.status === 'completed' ? 'text-green-400' :
                    step.status === 'processing' ? 'text-cyan-400' :
                    step.status === 'error' ? 'text-red-400' : 'text-gray-500'
                  }`}>
                    {step.label}
                  </span>
                </div>
                {step.message && (
                  <p className={`text-xs mt-1 ${step.status === 'error' ? 'text-red-400/70' : 'text-gray-500'}`}>
                    {step.message}
                  </p>
                )}
              </div>
              {step.status === 'processing' && (
                <span className="text-xs text-cyan-400 animate-pulse">Processing...</span>
              )}
            </div>
            {i < steps.length - 1 && (
              <div className="flex justify-start pl-9 py-1">
                <div className={`w-0.5 h-4 ${
                  step.status === 'completed' ? 'bg-green-500/50' : 'bg-gray-700'
                }`} />
              </div>
            )}
          </div>
        ))}
      </div>
      {currentIndex >= 0 && (
        <div className="mt-4 pt-4 border-t border-gray-800">
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <span>Step {currentIndex + 1} of {steps.length}</span>
            <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-cyan-500 rounded-full transition-all duration-500"
                style={{ width: `${((currentIndex) / steps.length) * 100}%` }}
              />
            </div>
            <span className="text-cyan-400">{Math.round(((currentIndex) / steps.length) * 100)}%</span>
          </div>
        </div>
      )}
    </div>
  );
}
