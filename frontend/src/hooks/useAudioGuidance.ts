import { useEffect, useRef } from 'react';

interface AudioGuidanceProps {
  enabled: boolean;
  dotCount: number;
  cellCount: number;
  isInferring: boolean;
}

export function useAudioGuidance({ enabled, dotCount, cellCount, isInferring }: AudioGuidanceProps) {
  const audioCtxRef = useRef<AudioContext | null>(null);

  // Initialize and return the browser AudioContext singleton
  const getAudioContext = (): AudioContext | null => {
    if (!audioCtxRef.current) {
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioContextClass) {
        audioCtxRef.current = new AudioContextClass();
      }
    }
    return audioCtxRef.current;
  };

  // Play a soft synthesizer beep
  const playBeep = (freq: number, duration: number, type: OscillatorType = 'sine') => {
    const ctx = getAudioContext();
    if (!ctx) return;

    // Resume context if suspended by browser security policy
    if (ctx.state === 'suspended') {
      ctx.resume().catch((err) => console.warn("Failed to resume AudioContext:", err));
      return;
    }

    try {
      const osc = ctx.createOscillator();
      const gainNode = ctx.createGain();

      osc.type = type;
      osc.frequency.setValueAtTime(freq, ctx.currentTime);

      // Low volume to prevent headphones discomfort
      gainNode.gain.setValueAtTime(0.05, ctx.currentTime);
      // Smooth decay ramp down to avoid audio pops
      gainNode.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + duration - 0.01);

      osc.connect(gainNode);
      gainNode.connect(ctx.destination);

      osc.start();
      osc.stop(ctx.currentTime + duration);
    } catch (e) {
      console.warn("Audio guidance beep failed:", e);
    }
  };

  // Auto-unlock AudioContext on first user tap/click interaction
  useEffect(() => {
    if (!enabled) return;

    const unlockAudio = () => {
      const ctx = getAudioContext();
      if (ctx && ctx.state === 'suspended') {
        ctx.resume();
      }
    };

    window.addEventListener('click', unlockAudio);
    window.addEventListener('touchstart', unlockAudio);

    return () => {
      window.removeEventListener('click', unlockAudio);
      window.removeEventListener('touchstart', unlockAudio);
    };
  }, [enabled]);

  // Audio Guidance Loop
  useEffect(() => {
    if (!enabled) return;

    const intervalId = setInterval(() => {
      // 1. Loading / Processing state feedback
      if (isInferring) {
        playBeep(600, 0.06, 'triangle'); // high tempo triangle clicks
        return;
      }

      // 2. Alignment state feedback
      if (dotCount > 0) {
        // High pitch = successful grid alignment (more cells parsed = higher pitch)
        const baseFreq = 440; // A4 tone
        const pitchIncrement = 35; 
        const frequency = baseFreq + Math.min(cellCount * pitchIncrement, 360);
        
        playBeep(frequency, 0.15, 'sine');
      } else {
        // Alignment error: double low-frequency beep (warning user to re-align glasses/page)
        playBeep(220, 0.12, 'sine');
        setTimeout(() => {
          if (enabled) {
            playBeep(220, 0.12, 'sine');
          }
        }, 160);
      }
    }, 1800);

    return () => {
      clearInterval(intervalId);
    };
  }, [enabled, dotCount, cellCount, isInferring]);

  return { playBeep };
}
