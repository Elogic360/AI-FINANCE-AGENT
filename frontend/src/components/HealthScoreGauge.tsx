import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { HealthScoreBreakdown } from '../types';

interface Props {
  score: number;
  breakdown?: HealthScoreBreakdown[];
  trend?: 'improving' | 'stable' | 'declining';
  previousScore?: number;
}

function getScoreColor(score: number): string {
  if (score >= 80) return '#22c55e';
  if (score >= 60) return '#f59e0b';
  return '#ef4444';
}

function getScoreLabel(score: number): string {
  if (score >= 80) return 'Excellent';
  if (score >= 60) return 'Fair';
  return 'Needs Attention';
}

export default function HealthScoreGauge({ score, breakdown, trend, previousScore }: Props) {
  const [showBreakdown, setShowBreakdown] = useState(false);
  const color = getScoreColor(score);
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (score / 100) * circumference;
  const diff = previousScore != null ? score - previousScore : null;

  return (
    <div className="bg-[#1a1a2e] rounded-xl p-6 border border-gray-800 flex flex-col items-center relative">
      <h3 className="text-gray-400 text-sm font-medium mb-4">Financial Health Score</h3>

      <div
        className="cursor-pointer"
        onClick={() => breakdown && setShowBreakdown((v) => !v)}
        role={breakdown ? 'button' : undefined}
        tabIndex={breakdown ? 0 : undefined}
        title={breakdown ? 'Click to see breakdown' : undefined}
      >
        <svg width="150" height="150" viewBox="0 0 120 120">
          <circle cx="60" cy="60" r="54" fill="none" stroke="#2a2a3e" strokeWidth="10" />
          <motion.circle
            cx="60"
            cy="60"
            r="54"
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1.2, ease: 'easeOut' }}
            strokeLinecap="round"
            transform="rotate(-90 60 60)"
          />
          <text x="60" y="55" textAnchor="middle" className="text-3xl font-bold" fill="white">
            {score}
          </text>
          <text x="60" y="72" textAnchor="middle" className="text-xs" fill="#8888a0">
            / 100
          </text>
        </svg>
      </div>

      <div className="mt-2 flex items-center gap-2">
        <span
          className="text-sm font-semibold"
          style={{ color }}
        >
          {getScoreLabel(score)}
        </span>
        {diff != null && diff !== 0 && (
          <span className={`text-xs font-medium ${diff > 0 ? 'text-green-400' : 'text-red-400'}`}>
            {diff > 0 ? '↑' : '↓'} {Math.abs(diff)} from last period
          </span>
        )}
        {trend && (
          <span className={`text-xs px-2 py-0.5 rounded-full ${
            trend === 'improving'
              ? 'bg-green-500/10 text-green-400'
              : trend === 'declining'
                ? 'bg-red-500/10 text-red-400'
                : 'bg-gray-500/10 text-gray-400'
          }`}>
            {trend === 'improving' ? '↗ Improving' : trend === 'declining' ? '↘ Declining' : '→ Stable'}
          </span>
        )}
      </div>

      <AnimatePresence>
        {showBreakdown && breakdown && breakdown.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="w-full mt-4 overflow-hidden"
          >
            <div className="space-y-2 pt-3 border-t border-gray-800">
              {breakdown.map((item) => (
                <div key={item.category} className="flex items-center gap-3">
                  <div className="flex-1">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-gray-400">{item.category}</span>
                      <span className="text-white font-medium">{item.score}/{item.max_score}</span>
                    </div>
                    <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                      <motion.div
                        className="h-full rounded-full"
                        style={{
                          backgroundColor:
                            item.score / item.max_score >= 0.7
                              ? '#22c55e'
                              : item.score / item.max_score >= 0.4
                                ? '#f59e0b'
                                : '#ef4444',
                        }}
                        initial={{ width: 0 }}
                        animate={{ width: `${(item.score / item.max_score) * 100}%` }}
                        transition={{ duration: 0.6 }}
                      />
                    </div>
                    {item.detail && (
                      <p className="text-[10px] text-gray-500 mt-0.5">{item.detail}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
