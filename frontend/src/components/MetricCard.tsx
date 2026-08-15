import { LucideIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { motion } from 'framer-motion';

interface Props {
  icon: LucideIcon;
  label: string;
  value: string;
  change?: string;
  trend?: 'up' | 'down' | 'flat';
  color?: string;
  delay?: number;
}

function formatTZS(amount: string | number): string {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  if (isNaN(num)) return 'TZS 0';
  return `TZS ${num.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

export { formatTZS };

export default function MetricCard({ icon: Icon, label, value, change, trend, color = 'text-cyan-400', delay = 0 }: Props) {
  const trendColor =
    trend === 'up' ? 'text-green-400' : trend === 'down' ? 'text-red-400' : 'text-gray-400';
  const TrendIcon =
    trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className="bg-[#1a1a2e] rounded-xl p-5 border border-gray-800 hover:border-gray-700 transition-colors"
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg bg-gray-800/50 ${color}`}>
            <Icon size={20} />
          </div>
          <span className="text-gray-400 text-sm">{label}</span>
        </div>
        {trend && (
          <div className={`flex items-center gap-1 ${trendColor}`}>
            <TrendIcon size={14} />
            {change && <span className="text-xs font-medium">{change}</span>}
          </div>
        )}
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
    </motion.div>
  );
}
