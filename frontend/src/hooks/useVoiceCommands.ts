import { useEffect, useState, useRef } from 'react';

interface VoiceCommandsProps {
  onStart: () => void;
  onPause: () => void;
  onTranslate: (langName: string) => void;
  enabled: boolean;
}

export function useVoiceCommands({ onStart, onPause, onTranslate, enabled }: VoiceCommandsProps) {
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if (!enabled) {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {
          // Ignore state issues on stop
        }
      }
      setIsListening(false);
      return;
    }

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setError("Speech recognition is not supported on this browser.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setIsListening(true);
      setError(null);
    };

    recognition.onend = () => {
      // In continuous mode, sometimes the browser drops connection; restart if still enabled
      if (enabled) {
        try {
          recognition.start();
        } catch (e) {
          // Already running or permission issues
        }
      } else {
        setIsListening(false);
      }
    };

    recognition.onerror = (event: any) => {
      console.error("Speech recognition error:", event.error);
      if (event.error === 'not-allowed') {
        setError("Microphone permission denied.");
      } else if (event.error === 'network') {
        setError("Speech network connection failed.");
      }
    };

    recognition.onresult = (event: any) => {
      const latestResult = event.results[event.results.length - 1];
      if (latestResult.isFinal) {
        const command = latestResult[0].transcript.trim().toLowerCase();
        console.info("Hands-Free Voice Command detected:", command);

        if (
          command.includes("start") || 
          command.includes("read") || 
          command.includes("scan") || 
          command.includes("resume")
        ) {
          onStart();
        } else if (
          command.includes("pause") || 
          command.includes("stop") || 
          command.includes("hold")
        ) {
          onPause();
        } else if (command.includes("translate to")) {
          // Extract target language (e.g., "translate to Hindi", "translate to Spanish")
          const parts = command.split("translate to");
          if (parts.length > 1) {
            const lang = parts[1].trim();
            if (lang) {
              onTranslate(lang);
            }
          }
        }
      }
    };

    recognitionRef.current = recognition;
    
    try {
      recognition.start();
    } catch (e) {
      console.error("Failed to start speech recognition engine:", e);
    }

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {
          // Ignore already stopped errors
        }
      }
    };
  }, [enabled, onStart, onPause, onTranslate]);

  return { isListening, error };
}
