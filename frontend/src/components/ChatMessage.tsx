import { motion } from 'framer-motion';
import { Bot, User, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';
import type { ChatMessageData, ResponseMetric, ResponseRecommendation, ResponseRisk } from '../types';

interface Props {
  message: ChatMessageData;
}

function MetricCard({ metric }: { metric: ResponseMetric }) {
  return (
    <div className="bg-gray-800/50 rounded-lg p-3">
      <span className="text-gray-400 text-xs">{metric.label}</span>
      <div className="flex items-center gap-2 mt-1">
        <span className="text-white text-lg font-bold">{metric.value}</span>
        {metric.change && (
          <span className={`text-xs font-medium ${metric.trend === 'up' ? 'text-green-400' : metric.trend === 'down' ? 'text-red-400' : 'text-gray-400'}`}>
            {metric.change}
          </span>
        )}
      </div>
    </div>
  );
}

function RecommendationCard({ rec }: { rec: ResponseRecommendation }) {
  const priorityColor = rec.priority === 'HIGH' ? 'text-red-400 bg-red-500/10' : rec.priority === 'MEDIUM' ? 'text-amber-400 bg-amber-500/10' : 'text-blue-400 bg-blue-500/10';
  return (
    <div className="bg-gray-800/30 border border-gray-700/50 rounded-lg p-3">
      <div className="flex items-center gap-2 mb-1">
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${priorityColor}`}>
          {rec.priority}
        </span>
        <span className="text-white text-sm font-medium">{rec.title}</span>
      </div>
      <p className="text-gray-400 text-xs leading-relaxed">{rec.description}</p>
    </div>
  );
}

function RiskBadge({ risk }: { risk: ResponseRisk }) {
  const color = risk.severity === 'HIGH' ? 'border-red-500/30 bg-red-500/5' : risk.severity === 'MEDIUM' ? 'border-amber-500/30 bg-amber-500/5' : 'border-blue-500/30 bg-blue-500/5';
  const badgeColor = risk.severity === 'HIGH' ? 'bg-red-500 text-white' : risk.severity === 'MEDIUM' ? 'bg-amber-500 text-white' : 'bg-blue-500 text-white';
  return (
    <div className={`border rounded-lg p-3 ${color}`}>
      <div className="flex items-center gap-2 mb-1">
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${badgeColor}`}>
          {risk.severity}
        </span>
        <span className="text-gray-400 text-xs">{risk.category}</span>
      </div>
      <p className="text-white text-sm font-medium">{risk.title}</p>
      <p className="text-gray-400 text-xs mt-1">{risk.description}</p>
      {risk.recommendation && (
        <p className="text-cyan-400 text-xs mt-2">💡 {risk.recommendation}</p>
      )}
    </div>
  );
}

export default function ChatMessage({ message }: Props) {
  const [showEvidence, setShowEvidence] = useState(false);
  const isUser = message.role === 'user';
  const structured = message.structured;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}
    >
      {/* Avatar */}
      <div className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${isUser ? 'bg-cyan-500' : 'bg-gray-700'}`}>
        {isUser ? <User size={16} className="text-white" /> : <Bot size={16} className="text-cyan-400" />}
      </div>

      {/* Bubble */}
      <div className={`max-w-[80%] ${isUser ? 'text-right' : ''}`}>
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? 'bg-cyan-500 text-white rounded-br-md'
              : 'bg-[#1a1a2e] border border-gray-800 text-gray-200 rounded-bl-md'
          }`}
        >
          {message.is_streaming ? (
            <span className="inline-flex items-center gap-1">
              {message.content}
              <span className="animate-pulse text-cyan-400">▊</span>
            </span>
          ) : (
            <div className="whitespace-pre-wrap">{message.content}</div>
          )}
        </div>

        {/* Structured sections (AI only) */}
        {!isUser && structured && !message.is_streaming && (
          <div className="mt-3 space-y-3">
            {/* Metrics */}
            {structured.metrics && structured.metrics.length > 0 && (
              <div className="grid grid-cols-2 gap-2">
                {structured.metrics.map((m, i) => (
                  <MetricCard key={i} metric={m} />
                ))}
              </div>
            )}

            {/* Recommendations */}
            {structured.recommendations && structured.recommendations.length > 0 && (
              <div className="space-y-2">
                <span className="text-gray-500 text-xs font-medium uppercase tracking-wider">Recommendations</span>
                {structured.recommendations.map((rec, i) => (
                  <RecommendationCard key={i} rec={rec} />
                ))}
              </div>
            )}

            {/* Risks */}
            {structured.risks && structured.risks.length > 0 && (
              <div className="space-y-2">
                <span className="text-gray-500 text-xs font-medium uppercase tracking-wider">Risk Assessment</span>
                {structured.risks.map((risk, i) => (
                  <RiskBadge key={i} risk={risk} />
                ))}
              </div>
            )}

            {/* Evidence toggle */}
            {structured.evidence && structured.evidence.length > 0 && (
              <div>
                <button
                  onClick={() => setShowEvidence(!showEvidence)}
                  className="flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
                >
                  {showEvidence ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  {showEvidence ? 'Hide' : 'Show'} Evidence ({structured.evidence.length})
                </button>
                {showEvidence && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    className="mt-2 space-y-2"
                  >
                    {structured.evidence.map((ev) => (
                      <div key={ev.id} className="bg-gray-900/50 border border-gray-800 rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-gray-500 text-xs">Source: {ev.source}</span>
                        </div>
                        <pre className="text-xs text-gray-400 overflow-x-auto">
                          {JSON.stringify(ev.data, null, 2)}
                        </pre>
                        <p className="text-cyan-400 text-xs mt-1">{ev.relevance}</p>
                      </div>
                    ))}
                  </motion.div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Timestamp */}
        <div className={`text-[10px] text-gray-600 mt-1 ${isUser ? 'text-right' : ''}`}>
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </motion.div>
  );
}
