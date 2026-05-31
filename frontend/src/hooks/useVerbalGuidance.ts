import { useEffect, useRef } from 'react';

interface VerbalGuidanceOptions {
  enabled: boolean;
  dots: Array<{ x: number; y: number }>;
  frameWidth: number;
  frameHeight: number;
  cellCount: number;
  isInferring: boolean;
}

/**
 * useVerbalGuidance
 *
 * Analyses detected dot positions and speaks alignment instructions
 * to guide a blind user in centering the Braille page under the camera.
 *
 * Instructions spoken (via Web Speech TTS):
 *   - "Move phone left / right" — horizontal offset
 *   - "Tilt page up / down"    — vertical offset
 *   - "Move closer / further"  — based on dot spread (scale)
 *   - "Hold steady, scanning"  — when perfectly aligned
 *   - "Point camera at Braille"— when no dots found
 */
export function useVerbalGuidance({
  enabled,
  dots,
  frameWidth,
  frameHeight,
  cellCount,
  isInferring,
}: VerbalGuidanceOptions) {
  const lastSpokenRef = useRef<string>('');
  const cooldownRef = useRef<boolean>(false);

  const speak = (msg: string) => {
    if (!window.speechSynthesis || cooldownRef.current) return;
    if (lastSpokenRef.current === msg) return; // avoid repeating identical message

    window.speechSynthesis.cancel();
    const utt = new SpeechSynthesisUtterance(msg);
    utt.rate = 1.1;
    utt.pitch = 1.0;
    utt.volume = 1.0;
    window.speechSynthesis.speak(utt);
    lastSpokenRef.current = msg;

    // 3s cooldown between guidance prompts to avoid overlapping speech
    cooldownRef.current = true;
    setTimeout(() => { cooldownRef.current = false; }, 3000);
  };

  useEffect(() => {
    if (!enabled) return;

    const intervalId = setInterval(() => {
      if (isInferring) return; // don't interrupt during active inference

      if (dots.length === 0) {
        speak("Point the camera at Braille. No dots detected.");
        return;
      }

      const centerX = frameWidth / 2;
      const centerY = frameHeight / 2;

      // Compute centroid of all detected dots
      const avgX = dots.reduce((sum, d) => sum + d.x, 0) / dots.length;
      const avgY = dots.reduce((sum, d) => sum + d.y, 0) / dots.length;

      const offsetX = avgX - centerX; // positive = dots are right of center
      const offsetY = avgY - centerY; // positive = dots are below center

      // Compute spread to estimate distance
      const xs = dots.map(d => d.x);
      const ys = dots.map(d => d.y);
      const spreadX = Math.max(...xs) - Math.min(...xs);
      const spreadY = Math.max(...ys) - Math.min(...ys);

      const HORIZ_THRESH = frameWidth * 0.15;   // 15% of frame width
      const VERT_THRESH  = frameHeight * 0.15;  // 15% of frame height

      // Horizontal guidance
      if (Math.abs(offsetX) > HORIZ_THRESH) {
        if (offsetX > 0) {
          speak("Move phone slightly to the right.");
        } else {
          speak("Move phone slightly to the left.");
        }
        return;
      }

      // Vertical guidance
      if (Math.abs(offsetY) > VERT_THRESH) {
        if (offsetY > 0) {
          speak("Tilt the page upward.");
        } else {
          speak("Tilt the page downward.");
        }
        return;
      }

      // Distance / scale guidance (spread too small = too far, too large = too close)
      if (spreadX < frameWidth * 0.1 && dots.length > 3) {
        speak("Move the page closer to the camera.");
        return;
      }
      if (spreadX > frameWidth * 0.9) {
        speak("Move the page further away from the camera.");
        return;
      }

      // All good
      if (cellCount > 0) {
        speak("Hold steady. Scanning.");
      } else {
        speak("Aligned. Processing dots.");
      }

    }, 4000); // Check every 4 seconds

    return () => clearInterval(intervalId);
  }, [enabled, dots, frameWidth, frameHeight, cellCount, isInferring]);
}
