import React from 'react';
import type { BrailleCell } from '../utils/api';
import { useSettingsStore } from '../stores/settingsStore';


interface BrailleCellDebuggerProps {
  cells: BrailleCell[];
  viewWidth?: number; // width resolution of inference (e.g. 640)
  viewHeight?: number; // height resolution of inference (e.g. 480)
}

export function BrailleCellDebugger({ cells, viewWidth = 640, viewHeight = 480 }: BrailleCellDebuggerProps) {
  const { showDebugger } = useSettingsStore();

  if (!showDebugger || !cells || cells.length === 0) return null;

  return (
    <svg
      viewBox={`0 0 ${viewWidth} ${viewHeight}`}
      className="absolute inset-0 w-full h-full pointer-events-none z-20 select-none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {cells.map((cell, cellIdx) => {
        const [x, y, w, h] = cell.bbox;
        const confidence = cell.confidence;
        
        // Color code based on character confidence
        // Green: high (> 80%), Orange: medium (> 60%), Red: low (< 60%)
        let strokeColor = '#10B981'; // Success Green
        let bgColor = 'rgba(16, 185, 129, 0.08)';
        if (confidence < 0.60) {
          strokeColor = '#EF4444'; // Error Red
          bgColor = 'rgba(239, 68, 68, 0.08)';
        } else if (confidence < 0.80) {
          strokeColor = '#F59E0B'; // Warning Amber
          bgColor = 'rgba(245, 158, 11, 0.08)';
        }

        return (
          <g key={`cell-${cellIdx}-${cell.char}`}>
            {/* Cell Bounding Box */}
            <rect
              x={x}
              y={y}
              width={w}
              height={h}
              fill={bgColor}
              stroke={strokeColor}
              strokeWidth="2"
              strokeDasharray="2, 2"
              rx="4"
            />

            {/* Bounding Box Info Label */}
            <g transform={`translate(${x}, ${y - 4})`}>
              <rect
                x="0"
                y="-14"
                width={cell.char ? 42 : 36}
                height="16"
                fill={strokeColor}
                rx="3"
              />
              <text
                x="4"
                y="-2"
                fill="#ffffff"
                fontSize="10"
                fontFamily="sans-serif"
                fontWeight="bold"
              >
                {cell.char === ' ' ? 'SPC' : cell.char.toUpperCase()} {Math.round(confidence * 100)}%
              </text>
            </g>

            {/* Render 6 Braille Dot positions inside the cell box */}
            {cell.dots.map((dotPresent, dotIdx) => {
              if (!dotPresent) return null;

              // Grid positioning for 6 dots (2 columns, 3 rows)
              // Column 0 = dots 1, 2, 3 (left). Column 1 = dots 4, 5, 6 (right).
              const col = dotIdx < 3 ? 0 : 1;
              const row = dotIdx % 3;

              // Compute dot center coordinates relative to cell bounding box
              const dotX = x + col * (w / 2) + w / 4;
              const dotY = y + row * (h / 3) + h / 6;

              return (
                <circle
                  key={`dot-${cellIdx}-${dotIdx}`}
                  cx={dotX}
                  cy={dotY}
                  r={Math.max(w * 0.08, 3)}
                  fill={strokeColor}
                  stroke="#ffffff"
                  strokeWidth="0.8"
                />
              );
            })}
          </g>
        );
      })}
    </svg>
  );
}
