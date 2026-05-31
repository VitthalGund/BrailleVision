import React, { useState, useEffect } from 'react';
import { Volume2, VolumeX, Copy, Check, RefreshCw, Globe, ChevronDown } from 'lucide-react';
import { useResultStore } from '../stores/resultStore';
import { useSettingsStore } from '../stores/settingsStore';
import { useTTS } from '../hooks/useTTS';
import { api } from '../utils/api';

const SUPPORTED_LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'hi', name: 'Hindi (हिन्दी)' },
  { code: 'ar', name: 'Arabic (العربية)' },
  { code: 'es', name: 'Spanish (Español)' },
  { code: 'fr', name: 'French (Français)' },
  { code: 'de', name: 'German (Deutsch)' },
  { code: 'zh', name: 'Chinese (中文)' },
];

export function ResultPanel() {
  const { text, confidence, processingTimeMs, resetResult } = useResultStore();
  const { ttsEnabled, targetLanguage, setTargetLanguage } = useSettingsStore();
  const { speak, stop } = useTTS();

  const [copied, setCopied] = useState(false);
  const [translatedText, setTranslatedText] = useState('');
  const [isTranslating, setIsTranslating] = useState(false);
  const [translationError, setTranslationError] = useState<string | null>(null);
  const [isPlayingTts, setIsPlayingTts] = useState(false);

  // Reset translation when source text changes
  useEffect(() => {
    setTranslatedText('');
    setTranslationError(null);
    stop();
    setIsPlayingTts(false);
  }, [text, stop]);

  // Handle Translate Trigger
  const handleTranslate = async (langCode: string) => {
    setTargetLanguage(langCode);
    if (langCode === 'en' || !text.trim()) {
      setTranslatedText('');
      return;
    }

    setIsTranslating(true);
    setTranslationError(null);
    try {
      const res = await api.translate(text, langCode);
      setTranslatedText(res.translated);
      if (res.warning) {
        console.warn("Translation warning:", res.warning);
      }
    } catch (err: any) {
      console.error("Translation error:", err);
      setTranslationError("Failed to connect to translation server.");
    } finally {
      setIsTranslating(false);
    }
  };

  // Copy to clipboard action
  const handleCopy = () => {
    const textToCopy = translatedText || text;
    if (!textToCopy) return;

    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // TTS playback handler
  const handleToggleTts = () => {
    if (isPlayingTts) {
      stop();
      setIsPlayingTts(false);
    } else {
      const textToSpeak = translatedText || text;
      // Map ISO language code to SpeechSynthesis locale code
      const localeMap: Record<string, string> = {
        en: 'en-US', hi: 'hi-IN', ar: 'ar-SA', es: 'es-ES', fr: 'fr-FR', de: 'de-DE', zh: 'zh-CN'
      };
      const locale = localeMap[translatedText ? targetLanguage : 'en'] || 'en-US';
      
      speak(textToSpeak, locale);
      setIsPlayingTts(true);
      
      // Auto-reset speaking state after average length
      const wordsCount = textToSpeak.split(' ').length;
      const durationEstimate = (wordsCount / 150) * 60 * 1000 + 1000; // ~150 WPM
      setTimeout(() => {
        setIsPlayingTts(false);
      }, durationEstimate);
    }
  };

  if (!text) {
    return (
      <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-8 flex flex-col items-center justify-center text-center text-slate-500 shadow-xl">
        <Globe size={40} className="text-slate-600 mb-3" />
        <p className="font-semibold">No active translation</p>
        <p className="text-xs text-slate-600 mt-1 max-w-xs">
          Point the camera at embossed Braille or upload an image file to begin translation.
        </p>
      </div>
    );
  }

  // Get confidence color state
  let confidenceColor = 'text-green-400 bg-green-950/30 border-green-900/30';
  if (confidence < 0.6) {
    confidenceColor = 'text-red-400 bg-red-950/30 border-red-900/30';
  } else if (confidence < 0.8) {
    confidenceColor = 'text-amber-400 bg-amber-950/30 border-amber-900/30';
  }

  return (
    <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl flex flex-col flex-shrink-0">
      {/* Panel Header */}
      <div className="border-b border-slate-800 p-4 bg-slate-950 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h2 className="font-bold text-slate-200">Decoded Text</h2>
          <span className={`text-xs px-2.5 py-1 rounded-full font-bold border ${confidenceColor}`}>
            {Math.round(confidence * 100)}% Match
          </span>
          <span className="text-xs text-slate-500 font-medium">
            {processingTimeMs}ms
          </span>
        </div>

        {/* Toolbar Controls */}
        <div className="flex items-center gap-2">
          {/* Language Selector Dropdown */}
          <div className="relative flex items-center bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-300 font-semibold cursor-pointer">
            <Globe size={14} className="mr-1.5 text-slate-400" />
            <select
              value={targetLanguage}
              onChange={(e) => handleTranslate(e.target.value)}
              className="bg-transparent border-none outline-none pr-4 cursor-pointer text-slate-200"
            >
              {SUPPORTED_LANGUAGES.map((lang) => (
                <option key={lang.code} value={lang.code} className="bg-slate-900 text-slate-200">
                  {lang.name}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleCopy}
            className="p-2 bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-100 rounded-xl border border-slate-800 transition-colors"
            title="Copy to clipboard"
          >
            {copied ? <Check size={16} className="text-green-400" /> : <Copy size={16} />}
          </button>

          <button
            onClick={resetResult}
            className="p-2 bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-100 rounded-xl border border-slate-800 transition-colors"
            title="Reset scanner"
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {/* Output Content Area */}
      <div className="p-5 flex flex-col md:flex-row gap-4 divide-y md:divide-y-0 md:divide-x divide-slate-800 min-h-[140px]">
        {/* Source English Text */}
        <div className="flex-1 pb-4 md:pb-0 md:pr-4 flex flex-col justify-between">
          <div>
            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Original English (Grade 1)</span>
            <p className="mt-2 text-slate-100 font-mono text-lg leading-relaxed whitespace-pre-wrap select-text">
              {text}
            </p>
          </div>
        </div>

        {/* Translation Output */}
        {targetLanguage !== 'en' && (
          <div className="flex-1 pt-4 md:pt-0 md:pl-4 flex flex-col justify-between">
            <div>
              <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">
                {SUPPORTED_LANGUAGES.find(l => l.code === targetLanguage)?.name} Translation
              </span>
              
              {isTranslating ? (
                <div className="mt-4 flex items-center gap-2 text-sm text-slate-500">
                  <RefreshCw size={16} className="animate-spin text-blue-500" />
                  Translating...
                </div>
              ) : translationError ? (
                <p className="mt-2 text-sm text-red-400">{translationError}</p>
              ) : (
                <p className="mt-2 text-slate-100 font-sans text-lg leading-relaxed whitespace-pre-wrap select-text">
                  {translatedText || 'Select a language to translate...'}
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* TTS Footer Banner */}
      <div className="bg-slate-950/50 border-t border-slate-800 px-5 py-3.5 flex items-center justify-between">
        <span className="text-xs text-slate-400 font-medium">
          {isPlayingTts ? 'Narration playing...' : 'Narration ready.'}
        </span>
        <button
          onClick={handleToggleTts}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold shadow-md transition-all active:scale-95 ${
            isPlayingTts
              ? 'bg-red-600 hover:bg-red-700 text-white'
              : 'bg-vision-blue hover:bg-blue-700 text-white shadow-blue-500/10'
          }`}
        >
          {isPlayingTts ? <VolumeX size={14} /> : <Volume2 size={14} />}
          {isPlayingTts ? 'Stop Speaking' : 'Read Aloud'}
        </button>
      </div>
    </div>
  );
}
