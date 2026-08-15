import { Download, Printer } from 'lucide-react';

interface ReportSection {
  title: string;
  type: 'text' | 'table' | 'summary';
  content?: string;
  headers?: string[];
  rows?: (string | number)[][];
  summaryItems?: { label: string; value: string; color?: string }[];
}

interface Props {
  title: string;
  subtitle?: string;
  currency?: string;
  sections: ReportSection[];
  onExport?: () => void;
}

export default function ReportViewer({ title, subtitle, sections, onExport }: Props) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-xl font-bold text-white">{title}</h2>
          {subtitle && <p className="text-gray-400 text-sm mt-1">{subtitle}</p>}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => window.print()}
            className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm transition"
          >
            <Printer size={14} /> Print
          </button>
          {onExport && (
            <button
              onClick={onExport}
              className="flex items-center gap-2 px-3 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded-lg text-sm transition"
            >
              <Download size={14} /> Export
            </button>
          )}
        </div>
      </div>

      {/* Sections */}
      {sections.map((section, i) => (
        <div key={i} className="bg-[#1a1a2e] rounded-xl border border-gray-800 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-800">
            <h3 className="text-white font-semibold">{section.title}</h3>
          </div>
          <div className="p-6">
            {section.type === 'text' && section.content && (
              <p className="text-gray-300 text-sm leading-relaxed">{section.content}</p>
            )}

            {section.type === 'summary' && section.summaryItems && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {section.summaryItems.map((item, j) => (
                  <div key={j} className="bg-gray-800/30 rounded-lg p-4">
                    <p className="text-gray-400 text-xs uppercase tracking-wider mb-1">{item.label}</p>
                    <p className={`text-lg font-bold ${item.color || 'text-white'}`}>{item.value}</p>
                  </div>
                ))}
              </div>
            )}

            {section.type === 'table' && section.headers && section.rows && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-800">
                      {section.headers.map((h, j) => (
                        <th key={j} className={`px-4 py-2.5 font-medium text-gray-400 ${j === section.headers!.length - 1 ? 'text-right' : 'text-left'}`}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {section.rows.map((row, j) => (
                      <tr key={j} className="border-b border-gray-800/50 hover:bg-gray-800/20">
                        {row.map((cell, k) => (
                          <td key={k} className={`px-4 py-2.5 ${k === row.length - 1 ? 'text-right font-medium text-white' : 'text-gray-300'}`}>
                            {typeof cell === 'number' ? cell.toLocaleString() : cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                    {section.rows.length === 0 && (
                      <tr>
                        <td colSpan={section.headers.length} className="px-4 py-8 text-center text-gray-500">
                          No data available
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
