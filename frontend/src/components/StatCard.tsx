import { LucideIcon } from 'lucide-react';

interface Props {
  icon: LucideIcon;
  label: string;
  value: string;
  color?: string;
}

export default function StatCard({ icon: Icon, label, value, color = 'text-cyan-400' }: Props) {
  return (
    <div className="bg-[#1a1a2e] rounded-xl p-5 border border-gray-800">
      <div className="flex items-center gap-3 mb-3">
        <div className={`p-2 rounded-lg bg-gray-800/50 ${color}`}>
          <Icon size={20} />
        </div>
        <span className="text-gray-400 text-sm">{label}</span>
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
    </div>
  );
}
