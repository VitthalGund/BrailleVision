import React, { useState, useRef, useEffect } from 'react';
import { Send, MessageSquare, HelpCircle, X, Minimize2, Maximize2 } from 'lucide-react';
import { useResultStore } from '../stores/resultStore';
import { api } from '../utils/api';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

const SUGGESTED_PROMPTS = [
  "How does Braille represent numbers?",
  "What does ⠠ (capital indicator) do?",
  "Tips for better camera alignment?",
  "Explain Grade 1 vs Grade 2 Braille.",
];

export function AIAssistant() {
  const { text: currentScanText } = useResultStore();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isMinimized, setIsMinimized] = useState(
    typeof window !== 'undefined' ? window.innerWidth < 768 : false
  );
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll chat history to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isMinimized]);

  // Send message action
  const handleSendMessage = async (msgText: string) => {
    if (!msgText.trim() || isSending) return;

    const userMessage: Message = { role: 'user', content: msgText };
    setMessages((prev) => [...prev, userMessage]);
    setInputMessage('');
    setIsSending(true);

    try {
      // Pass recent messages to maintain conversational state (last 6 turns)
      const chatHistory = messages.map((m) => ({ role: m.role, content: m.content }));
      
      const response = await api.chat(msgText, currentScanText, chatHistory);
      
      const assistantMessage: Message = { role: 'assistant', content: response.reply };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error("Chat error:", err);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: "I'm having trouble connecting right now. Please verify that the API is online." }
      ]);
    } finally {
      setIsSending(false);
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSendMessage(inputMessage);
  };

  const handleClearChat = () => {
    setMessages([]);
  };

  if (isMinimized) {
    return (
      <button
        onClick={() => setIsMinimized(false)}
        className="fixed bottom-20 md:bottom-6 right-4 md:right-6 z-40 bg-electric-teal text-white p-4 rounded-full shadow-2xl flex items-center gap-2 border border-cyan-400/20 active:scale-95 transition-all"
        title="Open AI Assistant"
      >
        <MessageSquare size={20} />
        <span className="font-semibold text-sm pr-1">Ask Assistant</span>
      </button>
    );
  }

  return (
    <div className="w-full md:w-80 bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl flex flex-col h-[400px] md:h-full fixed md:relative bottom-20 md:bottom-auto right-4 md:right-auto left-4 md:left-auto z-40 md:z-auto">
      {/* Chat Title bar */}
      <div className="border-b border-slate-800 p-4 bg-slate-950 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-electric-teal animate-pulse" />
          <h2 className="font-bold text-slate-200 text-sm">AI Dotly Assistant</h2>
        </div>
        <div className="flex items-center gap-1.5">
          {messages.length > 0 && (
            <button
              onClick={handleClearChat}
              className="text-xs text-slate-500 hover:text-slate-300 font-semibold px-2 py-1 rounded hover:bg-slate-900 transition-colors"
            >
              Clear
            </button>
          )}
          <button
            onClick={() => setIsMinimized(true)}
            className="p-1 text-slate-500 hover:text-slate-300 rounded hover:bg-slate-900 transition-colors"
            title="Minimize"
          >
            <Minimize2 size={14} />
          </button>
        </div>
      </div>

      {/* Messages list container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 flex flex-col bg-slate-900/30">
        {messages.length === 0 ? (
          /* Empty Chat Welcome Screen */
          <div className="flex-1 flex flex-col items-center justify-center text-center p-4">
            <HelpCircle className="text-slate-600 mb-2" size={32} />
            <p className="font-bold text-sm text-slate-400">How can I help you?</p>
            <p className="text-xs text-slate-500 mt-1 max-w-xs leading-relaxed">
              Ask about Grade 1 formatting, Braille translation rules, or get scanning tips.
            </p>

            {/* Suggested Prompts Cards */}
            <div className="w-full mt-6 space-y-2">
              {SUGGESTED_PROMPTS.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendMessage(prompt)}
                  className="w-full text-left px-3 py-2 bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-xl text-xs text-slate-300 transition-all active:scale-[0.99] font-medium leading-relaxed block"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Conversation Bubble Feed */
          <>
            {messages.map((msg, idx) => {
              const isUser = msg.role === 'user';
              return (
                <div
                  key={idx}
                  className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-sm leading-relaxed ${
                    isUser
                      ? 'bg-vision-blue text-white align-self-end self-end rounded-tr-none'
                      : 'bg-slate-950 border border-slate-800 text-slate-200 self-start rounded-tl-none border-l-2 border-l-electric-teal'
                  }`}
                >
                  <p className="whitespace-pre-wrap select-text">{msg.content}</p>
                </div>
              );
            })}
            
            {/* Show streaming progress dots if assistant is generating response */}
            {isSending && (
              <div className="bg-slate-950 border border-slate-800 text-slate-200 self-start rounded-2xl rounded-tl-none px-3.5 py-3.5 flex items-center gap-1">
                <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input box Form */}
      <form onSubmit={handleFormSubmit} className="border-t border-slate-800 p-3 bg-slate-950 flex gap-2">
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          placeholder="Ask a question..."
          className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-slate-700 transition-colors"
          disabled={isSending}
        />
        <button
          type="submit"
          disabled={!inputMessage.trim() || isSending}
          className="p-2.5 bg-electric-teal disabled:bg-slate-800 disabled:text-slate-600 text-white rounded-xl transition-all shadow-md active:scale-95 flex items-center justify-center"
        >
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}
