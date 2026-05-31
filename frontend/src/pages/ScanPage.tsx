import React from 'react';
import { CameraView } from '../components/CameraView';
import { ResultPanel } from '../components/ResultPanel';
import { AIAssistant } from '../components/AIAssistant';
import { BrailleCellDebugger } from '../components/BrailleCellDebugger';
import { useResultStore } from '../stores/resultStore';
import { api } from '../utils/api';

export function ScanPage() {
  const { isInferring, cells, setInferring, setResult, setError } = useResultStore();

  const handleFrameCapture = async (imageBlob: Blob) => {
    setInferring(true);
    try {
      const response = await api.infer(imageBlob);
      setResult(response);
    } catch (err: any) {
      console.error("Frame capture inference failed:", err);
      setError("Inference failed. Verify the server connection.");
    }
  };

  // Bounding box overlay for the camera feed
  const debuggerOverlay = cells.length > 0 ? (
    <BrailleCellDebugger cells={cells} viewWidth={640} viewHeight={480} />
  ) : undefined;

  return (
    <div className="flex-1 flex flex-col md:flex-row gap-6 p-4 md:p-6 pb-20 md:pb-6 overflow-hidden min-h-0 bg-slate-950 text-slate-100">
      {/* Scanning and Output Area */}
      <div className="flex-1 flex flex-col gap-6 overflow-y-auto pr-0 md:pr-2 min-h-0">
        <div className="flex flex-col gap-2">
          <h2 className="text-xl md:text-2xl font-bold tracking-tight text-slate-100">Dotly Scan Reader</h2>
          <p className="text-xs md:text-sm text-slate-400">
            Align camera feed parallel to the page. Enable raking light to resolve embossed dots.
          </p>
        </div>

        {/* Live Camera Scanner Box */}
        <CameraView
          onFrame={handleFrameCapture}
          isInferring={isInferring}
          debuggerOverlay={debuggerOverlay}
        />

        {/* Translation and Text Output Display */}
        <ResultPanel />
      </div>

      {/* AI Assistant Sidebar (Desktop) or Floating Chat bubble (Mobile) */}
      <div className="w-full md:w-auto flex flex-col flex-shrink-0">
        <AIAssistant />
      </div>
    </div>
  );
}
