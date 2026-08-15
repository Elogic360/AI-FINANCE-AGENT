import { motion } from 'framer-motion';
import { ArrowUpRight, ArrowDownLeft } from 'lucide-react';
import type { Transaction } from '../types';

interface Props {
  transactions: Transaction[];
  limit?: number;
}

function formatTZS(amount: string): string {
  const num = parseFloat(amount);
  if (isNaN(num)) return 'TZS 0';
  return `TZS ${num.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

export default function TransactionList({ transactions, limit = 8 }: Props) {
  const items = transactions.slice(0, limit);

  if (items.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 text-sm">
        No recent transactions
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {items.map((txn, i) => {
        const amount = parseFloat(txn.amount);
        const isIncome = amount > 0;

        return (
          <motion.div
            key={txn.id}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, delay: i * 0.04 }}
            className="flex items-center gap-3 py-3 px-2 rounded-lg hover:bg-gray-800/30 transition-colors"
          >
            <div className={`p-2 rounded-lg ${isIncome ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
              {isIncome ? (
                <ArrowDownLeft size={16} className="text-green-400" />
              ) : (
                <ArrowUpRight size={16} className="text-red-400" />
              )}
            </div>

            <div className="flex-1 min-w-0">
              <p className="text-white text-sm font-medium truncate">
                {txn.description || txn.counterparty || 'Transaction'}
              </p>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-gray-500 text-xs">{formatDate(txn.txn_date)}</span>
                {txn.ai_category && (
                  <span className="text-xs px-1.5 py-0.5 rounded bg-gray-800 text-gray-400">
                    {txn.ai_category}
                  </span>
                )}
              </div>
            </div>

            <span className={`text-sm font-semibold whitespace-nowrap ${isIncome ? 'text-green-400' : 'text-red-400'}`}>
              {isIncome ? '+' : ''}{formatTZS(txn.amount)}
            </span>
          </motion.div>
        );
      })}
    </div>
  );
}
