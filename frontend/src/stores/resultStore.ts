import { create } from 'zustand';
import type { InferenceResponse, BrailleCell, BrailleDot } from '../utils/api';


export interface ScanItem {
  id: string;
  timestamp: number;
  text: string;
  confidence: number;
}

interface ResultState {
  text: string;
  confidence: number;
  cells: BrailleCell[];
  dots: BrailleDot[];
  processingTimeMs: number;
  isInferring: boolean;
  error: string | null;
  history: ScanItem[];
  setResult: (result: InferenceResponse) => void;
  setInferring: (isInferring: boolean) => void;
  setError: (error: string | null) => void;
  resetResult: () => void;
  addToHistory: (text: string, confidence: number) => void;
  clearHistory: () => void;
}

// Load scan history from localStorage if available
const loadHistory = (): ScanItem[] => {
  try {
    const raw = localStorage.getItem('bv_scan_history');
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
};

export const useResultStore = create<ResultState>((set) => ({
  text: '',
  confidence: 0,
  cells: [],
  dots: [],
  processingTimeMs: 0,
  isInferring: false,
  error: null,
  history: loadHistory(),

  setResult: (result) => set((state) => {
    if (result.text && result.text.trim()) {
      state.addToHistory(result.text, result.confidence);
    }
    return {
      text: result.text,
      confidence: result.confidence,
      cells: result.cells,
      dots: result.dots,
      processingTimeMs: result.processing_time_ms,
      error: result.error || null,
      isInferring: false,
    };
  }),

  setInferring: (isInferring) => set({ isInferring }),
  
  setError: (error) => set({ error, isInferring: false }),

  resetResult: () => set({
    text: '',
    confidence: 0,
    cells: [],
    dots: [],
    processingTimeMs: 0,
    error: null,
  }),

  addToHistory: (text, confidence) => set((state) => {
    const newItem: ScanItem = {
      id: Math.random().toString(36).substring(2, 9),
      timestamp: Date.now(),
      text,
      confidence,
    };
    const updatedHistory = [newItem, ...state.history].slice(0, 20); // Keep last 20
    localStorage.setItem('bv_scan_history', JSON.stringify(updatedHistory));
    return { history: updatedHistory };
  }),

  clearHistory: () => set(() => {
    localStorage.removeItem('bv_scan_history');
    return { history: [] };
  }),
}));
