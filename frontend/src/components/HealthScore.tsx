interface Props {
  score: number;
}

export default function HealthScore({ score }: Props) {
  const color = score >= 70 ? '#22c55e' : score >= 40 ? '#f59e0b' : '#ef4444';
  const circumference = 2 * Math.PI * 45;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="bg-[#1a1a2e] rounded-xl p-6 border border-gray-800 flex flex-col items-center">
      <h3 className="text-gray-400 text-sm mb-4">Financial Health</h3>
      <svg width="120" height="120" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="45" fill="none" stroke="#2a2a3e" strokeWidth="8" />
        <circle cx="50" cy="50" r="45" fill="none" stroke={color} strokeWidth="8"
          strokeDasharray={circumference} strokeDashoffset={offset}
          strokeLinecap="round" transform="rotate(-90 50 50)" />
        <text x="50" y="50" textAnchor="middle" dy="0.35em" className="text-2xl font-bold fill-white">
          {score}
        </text>
        <text x="50" y="65" textAnchor="middle" className="text-xs fill-gray-400">/ 100</text>
      </svg>
    </div>
  );
}
