import { create } from 'zustand';

interface SettingsState {
  ttsEnabled: boolean;
  ttsRate: number;
  ttsPitch: number;
  ttsLanguage: string;
  targetLanguage: string;
  showDebugger: boolean;
  darkMode: boolean;
  setTtsEnabled: (enabled: boolean) => void;
  setTtsRate: (rate: number) => void;
  setTtsPitch: (pitch: number) => void;
  setTtsLanguage: (lang: string) => void;
  setTargetLanguage: (lang: string) => void;
  setShowDebugger: (show: boolean) => void;
  toggleDarkMode: () => void;
}

// Helper to load setting with fallback
const getSetting = <T>(key: string, fallback: T): T => {
  try {
    const raw = localStorage.getItem(key);
    if (raw === null) return fallback;
    if (typeof fallback === 'boolean') return (raw === 'true') as unknown as T;
    if (typeof fallback === 'number') return parseFloat(raw) as unknown as T;
    return raw as unknown as T;
  } catch {
    return fallback;
  }
};

export const useSettingsStore = create<SettingsState>((set) => ({
  ttsEnabled: getSetting('bv_tts_enabled', true),
  ttsRate: getSetting('bv_tts_rate', 1.0),
  ttsPitch: getSetting('bv_tts_pitch', 1.0),
  ttsLanguage: getSetting('bv_tts_language', 'en-US'),
  targetLanguage: getSetting('bv_target_language', 'en'),
  showDebugger: getSetting('bv_show_debugger', true),
  darkMode: getSetting('bv_dark_mode', true),

  setTtsEnabled: (enabled) => set(() => {
    localStorage.setItem('bv_tts_enabled', String(enabled));
    return { ttsEnabled: enabled };
  }),

  setTtsRate: (rate) => set(() => {
    localStorage.setItem('bv_tts_rate', String(rate));
    return { ttsRate: rate };
  }),

  setTtsPitch: (pitch) => set(() => {
    localStorage.setItem('bv_tts_pitch', String(pitch));
    return { ttsPitch: pitch };
  }),

  setTtsLanguage: (lang) => set(() => {
    localStorage.setItem('bv_tts_language', lang);
    return { ttsLanguage: lang };
  }),

  setTargetLanguage: (lang) => set(() => {
    localStorage.setItem('bv_target_language', lang);
    return { targetLanguage: lang };
  }),

  setShowDebugger: (show) => set(() => {
    localStorage.setItem('bv_show_debugger', String(show));
    return { showDebugger: show };
  }),

  toggleDarkMode: () => set((state) => {
    const nextDark = !state.darkMode;
    localStorage.setItem('bv_dark_mode', String(nextDark));
    if (nextDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    return { darkMode: nextDark };
  }),
}));
