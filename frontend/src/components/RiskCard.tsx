import { motion } from 'framer-motion';
import { AlertTriangle, ShieldAlert, Info } from 'lucide-react';

interface Props {
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  category: string;
  title: string;
  description: string;
  recommendation: string;
  delay?: number;
}

const severityConfig = {
  HIGH: {
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    badge: 'bg-red-500 text-white',
    icon: ShieldAlert,
    iconColor: 'text-red-400',
  },
  MEDIUM: {
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    badge: 'bg-amber-500 text-white',
    icon: AlertTriangle,
    iconColor: 'text-amber-400',
  },
  LOW: {
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    badge: 'bg-blue-500 text-white',
    icon: Info,
    iconColor: 'text-blue-400',
  },
};

export default function RiskCard({ severity, category, title, description, recommendation, delay = 0 }: Props) {
  const config = severityConfig[severity];
  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, delay }}
      className={`${config.bg} border ${config.border} rounded-lg p-4`}
    >
      <div className="flex items-start gap-3">
        <Icon size={18} className={`${config.iconColor} mt-0.5 shrink-0`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className={`${config.badge} text-[10px] font-bold px-2 py-0.5 rounded-full uppercase`}>
              {severity}
            </span>
            <span className="text-gray-500 text-xs">{category}</span>
          </div>
          <h4 className="text-white text-sm font-semibold mb-1">{title}</h4>
          <p className="text-gray-400 text-xs mb-2 leading-relaxed">{description}</p>
          <div className="bg-black/20 rounded px-3 py-2">
            <span className="text-[10px] text-gray-500 uppercase tracking-wider">Recommendation</span>
            <p className="text-gray-300 text-xs mt-0.5">{recommendation}</p>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
