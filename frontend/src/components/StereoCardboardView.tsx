import React, { useEffect, useRef, useState, useCallback } from 'react';
import type { GyroscopeAngles } from '../hooks/useGyroscope';

interface StereoCardboardViewProps {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  text: string;
  cells: Array<{ x: number; y: number; w: number; h: number; char: string; confidence: number }>;
  gyro: GyroscopeAngles;
  isActive: boolean;
  onExit: () => void;
}

// Depth parallax offset in pixels (half IPD simulation)
const PARALLAX_DEPTH = 8;

/**
 * StereoCardboardView
 *
 * Renders a full-screen Side-by-Side stereoscopic view for Google Cardboard / VR Box.
 * - Left half  = left eye (video passthrough + text shifted left by PARALLAX_DEPTH)
 * - Right half = right eye (video passthrough + text shifted right by PARALLAX_DEPTH)
 * - Gyroscope rotates the text overlay to simulate head tracking
 */
export function StereoCardboardView({ videoRef, text, cells, gyro, isActive, onExit }: StereoCardboardViewProps) {
  const leftCanvasRef = useRef<HTMLCanvasElement>(null);
  const rightCanvasRef = useRef<HTMLCanvasElement>(null);
  const animFrameRef = useRef<number>(0);

  const drawEye = useCallback(
    (ctx: CanvasRenderingContext2D, video: HTMLVideoElement, side: 'left' | 'right', w: number, h: number) => {
      // 1. Draw camera passthrough
      ctx.drawImage(video, 0, 0, w, h);

      // 2. Lens vignette overlay (darkened circular edges — Cardboard feel)
      const gradient = ctx.createRadialGradient(w / 2, h / 2, h * 0.3, w / 2, h / 2, h * 0.75);
      gradient.addColorStop(0, 'rgba(0,0,0,0)');
      gradient.addColorStop(1, 'rgba(0,0,0,0.75)');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, w, h);

      if (!text) return;

      // 3. Gyro-based offset so text "tracks" with head tilt
      const gyroShiftX = (gyro.gamma / 45) * 30; // max ±30px for ±45° roll
      const gyroShiftY = (gyro.beta / 45) * 20;   // max ±20px for ±45° pitch

      // 4. Parallax offset for depth perception
      const parallaxX = side === 'left' ? -PARALLAX_DEPTH : PARALLAX_DEPTH;

      // 5. Draw floating text panel
      const panelW = Math.min(w * 0.85, 480);
      const panelH = 90;
      const panelX = (w - panelW) / 2 + gyroShiftX + parallaxX;
      const panelY = h * 0.68 + gyroShiftY;

      // Glassmorphism panel background
      ctx.save();
      ctx.globalAlpha = 0.82;
      ctx.fillStyle = '#0f172a';
      ctx.beginPath();
      ctx.roundRect(panelX, panelY, panelW, panelH, 16);
      ctx.fill();

      // Panel border glow
      ctx.strokeStyle = 'rgba(139, 92, 246, 0.7)'; // purple
      ctx.lineWidth = 1.5;
      ctx.stroke();
      ctx.globalAlpha = 1.0;
      ctx.restore();

      // Text rendering
      ctx.save();
      ctx.font = 'bold 20px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
      ctx.fillStyle = '#f1f5f9';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';

      // Wrap long text
      const maxChars = 38;
      const displayText = text.length > maxChars ? text.substring(0, maxChars) + '…' : text;
      ctx.fillText(displayText, panelX + panelW / 2, panelY + panelH * 0.4);

      // Confidence dots for detected cells
      const dotSpacing = Math.min(panelW / (cells.length + 1), 20);
      cells.slice(0, 20).forEach((cell, i) => {
        const dotX = panelX + dotSpacing * (i + 1);
        const dotY = panelY + panelH * 0.78;
        const confidence = cell.confidence;
        ctx.beginPath();
        ctx.arc(dotX, dotY, 4, 0, Math.PI * 2);
        ctx.fillStyle = confidence > 0.8 ? '#4ade80' : confidence > 0.5 ? '#fbbf24' : '#f87171';
        ctx.fill();
      });
      ctx.restore();

      // 6. HUD corner indicators
      ctx.save();
      ctx.font = '10px monospace';
      ctx.fillStyle = 'rgba(139, 92, 246, 0.8)';
      ctx.fillText(`${side.toUpperCase()} EYE | γ${gyro.gamma.toFixed(0)}° β${gyro.beta.toFixed(0)}°`, 10, 18);
      ctx.restore();
    },
    [text, cells, gyro]
  );

  useEffect(() => {
    if (!isActive) {
      cancelAnimationFrame(animFrameRef.current);
      return;
    }

    const render = () => {
      const video = videoRef.current;
      const leftCtx = leftCanvasRef.current?.getContext('2d');
      const rightCtx = rightCanvasRef.current?.getContext('2d');

      if (video && leftCtx && rightCtx && video.readyState >= 2) {
        const w = leftCanvasRef.current!.width;
        const h = leftCanvasRef.current!.height;
        drawEye(leftCtx, video, 'left', w, h);
        drawEye(rightCtx, video, 'right', w, h);
      }

      animFrameRef.current = requestAnimationFrame(render);
    };

    animFrameRef.current = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animFrameRef.current);
  }, [isActive, drawEye, videoRef]);

  // Keep canvas size matching half the viewport
  const [eyeSize, setEyeSize] = useState({ w: 640, h: 480 });
  useEffect(() => {
    const update = () => {
      setEyeSize({ w: Math.floor(window.innerWidth / 2), h: window.innerHeight });
    };
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);

  if (!isActive) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex bg-black"
      style={{ touchAction: 'none', userSelect: 'none' }}
    >
      {/* LEFT EYE */}
      <div className="relative flex-1 overflow-hidden border-r border-purple-900/50">
        <canvas
          ref={leftCanvasRef}
          width={eyeSize.w}
          height={eyeSize.h}
          className="w-full h-full"
        />
        {/* Center cross-hair for lens alignment */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-4 h-px bg-purple-500/40" />
          <div className="absolute w-px h-4 bg-purple-500/40" />
        </div>
      </div>

      {/* RIGHT EYE */}
      <div className="relative flex-1 overflow-hidden">
        <canvas
          ref={rightCanvasRef}
          width={eyeSize.w}
          height={eyeSize.h}
          className="w-full h-full"
        />
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-4 h-px bg-purple-500/40" />
          <div className="absolute w-px h-4 bg-purple-500/40" />
        </div>
      </div>

      {/* EXIT — tap with two fingers or hold to exit */}
      <button
        onClick={onExit}
        className="absolute top-4 left-1/2 -translate-x-1/2 z-50 px-5 py-2 bg-slate-950/80 border border-purple-500/40 text-purple-300 text-xs font-bold rounded-full backdrop-blur-md"
      >
        ✕ Exit VR
      </button>
    </div>
  );
}
