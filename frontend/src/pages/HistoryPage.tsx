import React from 'react';
import { Trash2, Copy, Volume2, Calendar } from 'lucide-react';
import { useResultStore } from '../stores/resultStore';

import { useTTS } from '../hooks/useTTS';

export function HistoryPage() {
  const { history, clearHistory } = useResultStore();
  const { speak } = useTTS();

  const handleCopyText = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const formatRelativeTime = (timestamp: number) => {
    const diff = Date.now() - timestamp;
    const mins = Math.floor(diff / 60000);
    const hours = Math.floor(mins / 60);
    
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return new Date(timestamp).toLocaleDateString();
  };

  return (
    <div className="flex-1 flex flex-col gap-6 p-4 md:p-6 pb-20 md:pb-6 overflow-y-auto min-h-0 bg-slate-950 text-slate-100">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl md:text-2xl font-bold tracking-tight text-slate-100">Scan Logs History</h2>
          <p className="text-xs md:text-sm text-slate-400 mt-0.5">
            View last 20 translations cached locally in the browser.
          </p>
        </div>
        {history.length > 0 && (
          <button
            onClick={clearHistory}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold bg-red-950 hover:bg-red-900 border border-red-800 text-red-200 rounded-xl transition-all"
          >
            <Trash2 size={14} />
            Clear Log
          </button>
        )}
      </div>

      {history.length === 0 ? (
        <div className="flex-1 border border-dashed border-slate-800 rounded-2xl flex flex-col items-center justify-center text-center p-8 text-slate-500">
          <Calendar size={40} className="text-slate-700 mb-2" />
          <p className="font-semibold text-sm">No history items yet</p>
          <p className="text-xs text-slate-600 mt-1 max-w-xs leading-relaxed">
            Successful scan interpretations will automatically populate in this log history.
          </p>
        </div>
      ) : (
        <div className="space-y-4 max-w-3xl">
          {history.map((item) => (
            <div
              key={item.id}
              className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col gap-3 shadow-md hover:border-slate-700 transition-all"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500 font-semibold">
                  {formatRelativeTime(item.timestamp)}
                </span>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                  item.confidence > 0.8
                    ? 'bg-green-950/20 text-green-400 border-green-900/30'
                    : 'bg-amber-950/20 text-amber-400 border-amber-900/30'
                }`}>
                  {Math.round(item.confidence * 100)}% Match
                </span>
              </div>
              
              <p className="text-slate-100 font-mono text-md break-words select-text">
                {item.text}
              </p>

              <div className="flex gap-2 justify-end pt-1 border-t border-slate-800/50 mt-1">
                <button
                  onClick={() => handleCopyText(item.text)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-950 hover:bg-slate-800 text-slate-400 hover:text-slate-100 border border-slate-800 text-xs font-semibold rounded-lg transition-colors"
                >
                  <Copy size={12} />
                  Copy
                </button>
                <button
                  onClick={() => speak(item.text, 'en-US')}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-vision-blue hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-md transition-colors"
                >
                  <Volume2 size={12} />
                  Speak
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
