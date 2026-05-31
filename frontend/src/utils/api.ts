export interface BrailleCell {
  dots: boolean[];
  char: string;
  bbox: number[]; // [x, y, w, h]
  confidence: number;
}

export interface BrailleDot {
  x: number;
  y: number;
  confidence: number;
}

export interface InferenceResponse {
  text: string;
  confidence: number;
  cells: BrailleCell[];
  dots: BrailleDot[];
  processing_time_ms: number;
  error?: string;
}

export interface TranslateResponse {
  translated: string;
  source_lang: string;
  warning?: string;
}

export interface ChatResponse {
  reply: string;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = {
  /**
   * Send an image file to the backend for Braille dot detection and decoding.
   */
  async infer(imageBlob: Blob): Promise<InferenceResponse> {
    const formData = new FormData();
    formData.append('file', imageBlob, 'capture.jpg');

    const response = await fetch(`${API_BASE_URL}/api/infer`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Inference API error: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Translate recognized text to target language.
   */
  async translate(text: string, targetLang: string): Promise<TranslateResponse> {
    const response = await fetch(`${API_BASE_URL}/api/translate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text, target_lang: targetLang }),
    });

    if (!response.ok) {
      throw new Error(`Translation API error: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Chat with the BrailleVision assistant.
   */
  async chat(message: string, context: string = '', history: { role: string; content: string }[] = []): Promise<ChatResponse> {
    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message, context, history }),
    });

    if (!response.ok) {
      throw new Error(`Chat API error: ${response.statusText}`);
    }

    return response.json();
  },
};
