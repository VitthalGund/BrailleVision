import { useCallback, useRef } from 'react';
import { useSettingsStore } from '../stores/settingsStore';

export function useTTS() {
  const { ttsEnabled, ttsLanguage, ttsRate, ttsPitch } = useSettingsStore();
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  const speak = useCallback((text: string, lang?: string) => {
    if (!ttsEnabled || !window.speechSynthesis || !text.trim()) return;

    try {
      // Cancel active speech playback
      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang || ttsLanguage;
      utterance.rate = ttsRate;
      utterance.pitch = ttsPitch;

      // Handle speech end or errors cleanly
      utterance.onend = () => {
        utteranceRef.current = null;
      };
      utterance.onerror = (e) => {
        console.error("SpeechSynthesis error:", e);
        utteranceRef.current = null;
      };

      utteranceRef.current = utterance;
      window.speechSynthesis.speak(utterance);
    } catch (err) {
      console.warn("TTS speak failed:", err);
    }
  }, [ttsEnabled, ttsLanguage, ttsRate, ttsPitch]);

  const stop = useCallback(() => {
    try {
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    } catch (err) {
      console.warn("TTS cancel failed:", err);
    }
    utteranceRef.current = null;
  }, []);

  return { speak, stop };
}
