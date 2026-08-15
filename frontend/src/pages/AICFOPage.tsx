import { useState, useRef, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  Bot,
  Send,
  Sparkles,
  RotateCcw,
  Globe,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import ChatMessage from '../components/ChatMessage';
import {
  fetchSuggestedQuestions,
  sendChatMessage,
  streamChatMessage,
} from '../lib/api';
import type { ChatMessageData, SuggestedQuestion } from '../types';

const DEFAULT_SUGGESTED: SuggestedQuestion[] = [
  { id: '1', text: 'Why is my profit falling this quarter?', text_sw: 'Kwa nini faida yangu inashuka robo hii?', category: 'analysis' },
  { id: '2', text: 'Can I afford to hire another employee?', text_sw: 'Je, ninaweza kumudu kuajiri mfanyakazi mwingine?', category: 'planning' },
  { id: '3', text: 'What are my biggest expenses?', text_sw: 'Gharama zangu kubwa ni zipi?', category: 'analysis' },
  { id: '4', text: 'How can I improve cash flow?', text_sw: 'Ninawezaje kuboresha mtiririko wa pesa?', category: 'advice' },
  { id: '5', text: 'Am I at risk of running out of cash?', text_sw: 'Je, niko hatarini kukosa pesa?', category: 'risk' },
  { id: '6', text: 'Summarize my financial health', text_sw: 'Fupisha hali yangu ya kifedha', category: 'summary' },
];

export default function AICFOPage() {
  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [useSwahili, setUseSwahili] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<(() => void) | null>(null);

  const { data: suggested } = useQuery<SuggestedQuestion[]>({
    queryKey: ['suggested-questions'],
    queryFn: fetchSuggestedQuestions,
    staleTime: 300_000,
  });

  const questions = (suggested && suggested.length > 0) ? suggested : DEFAULT_SUGGESTED;

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  // Auto-resize textarea
  useEffect(() => {
    const el = inputRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
    }
  }, [input]);

  const handleSend = useCallback(async (text?: string) => {
    const msg = (text ?? input).trim();
    if (!msg || isStreaming) return;

    const userMsg: ChatMessageData = {
      id: crypto.randomUUID(),
      role: 'user',
      content: msg,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsStreaming(true);
    setStreamingContent('');

    const streamingMsgId = crypto.randomUUID();

    abortRef.current = streamChatMessage(
      msg,
      // onChunk
      (chunk) => {
        setStreamingContent((prev) => prev + chunk);
      },
      // onComplete
      (response) => {
        const aiMsg: ChatMessageData = {
          ...response,
          id: streamingMsgId,
          role: 'assistant',
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, aiMsg]);
        setStreamingContent('');
        setIsStreaming(false);
        abortRef.current = null;
      },
      // onError
      (err) => {
        // Fallback to non-streaming API
        sendChatMessage(msg)
          .then((res) => {
            setMessages((prev) => [
              ...prev,
              { ...res, id: streamingMsgId, role: 'assistant', timestamp: new Date().toISOString() },
            ]);
          })
          .catch(() => {
            setMessages((prev) => [
              ...prev,
              {
                id: streamingMsgId,
                role: 'assistant',
                content: `Sorry, I encountered an error: ${err.message}. Please try again.`,
                timestamp: new Date().toISOString(),
              },
            ]);
          })
          .finally(() => {
            setStreamingContent('');
            setIsStreaming(false);
            abortRef.current = null;
          });
      },
    );
  }, [input, isStreaming]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClear = () => {
    if (abortRef.current) {
      abortRef.current();
      abortRef.current = null;
    }
    setMessages([]);
    setStreamingContent('');
    setIsStreaming(false);
  };

  const suggestedText = (q: SuggestedQuestion) =>
    useSwahili && q.text_sw ? q.text_sw : q.text;

  return (
    <div className="flex flex-col h-[calc(100vh-7rem)] max-h-[calc(100vh-7rem)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <Bot size={22} className="text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">AI CFO</h1>
            <p className="text-gray-500 text-xs">Ask anything about your finances</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setUseSwahili(!useSwahili)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              useSwahili
                ? 'bg-green-500/10 text-green-400 border border-green-500/30'
                : 'bg-gray-800 text-gray-400 border border-gray-700 hover:text-white'
            }`}
            title="Toggle Swahili / English"
          >
            <Globe size={14} />
            {useSwahili ? 'Kiswahili' : 'English'}
          </button>
          {messages.length > 0 && (
            <button
              onClick={handleClear}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-800 text-gray-400 border border-gray-700 hover:text-white transition-colors"
            >
              <RotateCcw size={14} />
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto rounded-xl bg-[#0d0d14] border border-gray-800 p-4 space-y-4 min-h-0">
        {messages.length === 0 && !isStreaming ? (
          /* Welcome / Suggested Questions */
          <div className="flex flex-col items-center justify-center h-full">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4 }}
              className="text-center mb-8"
            >
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-cyan-500/20">
                <Sparkles size={30} className="text-white" />
              </div>
              <h2 className="text-white text-lg font-semibold mb-2">
                {useSwahili ? 'Habari! Mimi ni AI CFO wako' : "Hi! I'm your AI CFO"}
              </h2>
              <p className="text-gray-500 text-sm max-w-md">
                {useSwahili
                  ? 'Niulize chochote kuhusu fedha zako. Niko hapa kukusaidia.'
                  : 'Ask me anything about your finances. I analyze your data to give actionable insights.'}
              </p>
            </motion.div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-2xl">
              {questions.slice(0, 6).map((q, i) => (
                <motion.button
                  key={q.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: 0.1 + i * 0.05 }}
                  onClick={() => handleSend(suggestedText(q))}
                  className="text-left p-3 rounded-lg bg-[#1a1a2e] border border-gray-800 hover:border-cyan-500/30 hover:bg-[#1a2a3e] transition-all group"
                >
                  <span className="text-gray-300 text-sm group-hover:text-white transition-colors">
                    {suggestedText(q)}
                  </span>
                  <span className="block text-[10px] text-gray-600 mt-1 capitalize">{q.category}</span>
                </motion.button>
              ))}
            </div>
          </div>
        ) : (
          /* Chat messages */
          <>
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}

            {/* Streaming indicator */}
            {isStreaming && (
              <ChatMessage
                message={{
                  id: 'streaming',
                  role: 'assistant',
                  content: streamingContent || 'Thinking...',
                  timestamp: new Date().toISOString(),
                  is_streaming: true,
                }}
              />
            )}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input area */}
      <div className="mt-4">
        <div className="flex items-end gap-3 bg-[#1a1a2e] border border-gray-800 rounded-xl p-3 focus-within:border-cyan-500/50 transition-colors">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              useSwahili
                ? 'Andika swali lako la fedha hapa...'
                : 'Ask a financial question...'
            }
            rows={1}
            className="flex-1 bg-transparent text-white text-sm placeholder-gray-600 resize-none outline-none min-h-[24px] max-h-[120px]"
            disabled={isStreaming}
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || isStreaming}
            className={`p-2.5 rounded-lg transition-all ${
              input.trim() && !isStreaming
                ? 'bg-cyan-500 text-white hover:bg-cyan-400 shadow-lg shadow-cyan-500/20'
                : 'bg-gray-800 text-gray-600 cursor-not-allowed'
            }`}
          >
            {isStreaming ? (
              <div className="w-5 h-5 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
            ) : (
              <Send size={18} />
            )}
          </button>
        </div>
        <p className="text-center text-gray-600 text-[10px] mt-2">
          {useSwahili
            ? 'AI CFO inaweza kufanya makosa. Thibitisha taarifa muhimu na mhasibu wako.'
            : 'AI CFO can make mistakes. Verify important data with your accountant.'}
        </p>
      </div>
    </div>
  );
}
