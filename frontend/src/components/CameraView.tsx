import React, { useRef, useEffect, useState, useCallback } from 'react';
import {
  Camera, Image, Upload, Play, Pause, AlertTriangle,
  Glasses, Smartphone, Copy, Check
} from 'lucide-react';
import { useCamera } from '../hooks/useCamera';
import { useResultStore } from '../stores/resultStore';
import { useSettingsStore } from '../stores/settingsStore';
import { useVoiceCommands } from '../hooks/useVoiceCommands';
import { useAudioGuidance } from '../hooks/useAudioGuidance';
import { useGyroscope } from '../hooks/useGyroscope';
import { useVerbalGuidance } from '../hooks/useVerbalGuidance';
import { useTTS } from '../hooks/useTTS';
import { useCompanionStore } from '../stores/companionStore';
import { StereoCardboardView } from './StereoCardboardView';
import { SpatialXRView } from './SpatialXRView';

interface CameraViewProps {
  onFrame: (blob: Blob) => void;
  isInferring: boolean;
  debuggerOverlay?: React.ReactNode;
}

type TabMode = 'camera' | 'upload' | 'cardboard' | 'headset';

export function CameraView({ onFrame, isInferring, debuggerOverlay }: CameraViewProps) {
  const { stream, isLive, error: cameraError, startCamera, stopCamera } = useCamera();
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const [activeTab, setActiveTab] = useState<TabMode>('camera');
  const [isLiveScan, setIsLiveScan] = useState(false);
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);
  const [uploadedBlob, setUploadedBlob] = useState<Blob | null>(null);

  // VR / XR overlays
  const [showCardboard, setShowCardboard] = useState(false);
  const [showSpatialXR, setShowSpatialXR] = useState(false);
  const [pairCodeCopied, setPairCodeCopied] = useState(false);

  // Stores
  const { cells, dots, text } = useResultStore();
  const { targetLanguage, setTargetLanguage } = useSettingsStore();
  const { pairingCode } = useCompanionStore();

  // Map BrailleCell (bbox: number[]) → flat shape for VR components
  const mappedCells = cells.map(c => ({
    x: c.bbox[0] ?? 0,
    y: c.bbox[1] ?? 0,
    w: c.bbox[2] ?? 0,
    h: c.bbox[3] ?? 0,
    char: c.char,
    confidence: c.confidence,
  }));
  const { speak, stop: stopTTS } = useTTS();

  // Gyroscope for Cardboard head-tracking
  const { angles: gyroAngles, permissionGranted, requestPermission } = useGyroscope({
    enabled: activeTab === 'cardboard',
  });

  // Sync camera stream to video element
  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream]);

  // Auto-capture loop
  useEffect(() => {
    if (!isLive || !isLiveScan || activeTab !== 'camera') return;
    let timeoutId: any;
    const captureLoop = () => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (video && canvas && isLiveScan && !isInferring) {
        const ctx = canvas.getContext('2d');
        if (ctx) {
          canvas.width = video.videoWidth || 640;
          canvas.height = video.videoHeight || 480;
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
          canvas.toBlob((blob) => { if (blob) onFrame(blob); }, 'image/jpeg', 0.85);
        }
      }
      timeoutId = setTimeout(captureLoop, 1500);
    };
    captureLoop();
    return () => clearTimeout(timeoutId);
  }, [isLive, isLiveScan, isInferring, activeTab, onFrame]);

  // Cardboard mode: also auto-capture for YOLO processing
  useEffect(() => {
    if (!isLive || !showCardboard || isInferring) return;
    let timeoutId: any;
    const cardboardCaptureLoop = () => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (video && canvas && !isInferring) {
        const ctx = canvas.getContext('2d');
        if (ctx) {
          canvas.width = video.videoWidth || 640;
          canvas.height = video.videoHeight || 480;
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
          canvas.toBlob((blob) => { if (blob) onFrame(blob); }, 'image/jpeg', 0.85);
        }
      }
      timeoutId = setTimeout(cardboardCaptureLoop, 2000);
    };
    cardboardCaptureLoop();
    return () => clearTimeout(timeoutId);
  }, [isLive, showCardboard, isInferring, onFrame]);

  // Manual snapshot
  const handleSingleCapture = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (video && canvas) {
      const ctx = canvas.getContext('2d');
      if (ctx) {
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        canvas.toBlob((blob) => { if (blob) onFrame(blob); }, 'image/jpeg', 0.85);
      }
    }
  }, [onFrame]);

  // Voice command callbacks
  const handleVoiceStart = useCallback(() => {
    setIsLiveScan(true);
    if (!isLive) startCamera();
    speak('Scanning resumed.');
  }, [isLive, startCamera, speak]);

  const handleVoicePause = useCallback(() => {
    setIsLiveScan(false);
    speak('Scanning paused.');
  }, [speak]);

  const handleVoiceTranslate = useCallback((langName: string) => {
    const map: Record<string, string> = {
      english: 'en', hindi: 'hi', arabic: 'ar',
      spanish: 'es', french: 'fr', german: 'de', chinese: 'zh',
    };
    const code = map[langName.toLowerCase()];
    if (code) { setTargetLanguage(code); speak(`Translating to ${langName}.`); }
  }, [setTargetLanguage, speak]);

  const { error: voiceError } = useVoiceCommands({
    onStart: handleVoiceStart,
    onPause: handleVoicePause,
    onTranslate: handleVoiceTranslate,
    enabled: showCardboard || showSpatialXR,
  });

  // Audio alignment beeps (Cardboard / XR modes)
  useAudioGuidance({
    enabled: (showCardboard || showSpatialXR) && isLiveScan,
    dotCount: dots.length,
    cellCount: cells.length,
    isInferring,
  });

  // Verbal alignment guidance
  useVerbalGuidance({
    enabled: showCardboard || showSpatialXR,
    dots: dots.map(d => ({ x: d.x, y: d.y })),
    frameWidth: videoRef.current?.videoWidth || 640,
    frameHeight: videoRef.current?.videoHeight || 480,
    cellCount: cells.length,
    isInferring,
  });

  // Auto-TTS in immersive modes
  useEffect(() => {
    if ((showCardboard || showSpatialXR) && text) {
      const localeMap: Record<string, string> = {
        en: 'en-US', hi: 'hi-IN', ar: 'ar-SA', es: 'es-ES',
        fr: 'fr-FR', de: 'de-DE', zh: 'zh-CN',
      };
      speak(text, localeMap[targetLanguage] || 'en-US');
    }
  }, [text, showCardboard, showSpatialXR, targetLanguage, speak]);

  // Tab switching
  const switchTab = (tab: TabMode) => {
    setActiveTab(tab);
    setShowCardboard(false);
    setShowSpatialXR(false);
    setIsLiveScan(false);
    stopTTS();

    if (tab === 'camera') {
      startCamera();
    } else if (tab === 'cardboard') {
      startCamera();
    } else if (tab === 'headset') {
      stopCamera();
    } else if (tab === 'upload') {
      stopCamera();
    }
  };

  const enterCardboardVR = async () => {
    if (!permissionGranted) await requestPermission();
    setShowCardboard(true);
    speak('Cardboard VR mode active. Hold phone inside your headset. Processing will continue automatically.');
  };

  const enterSpatialXR = () => {
    setShowSpatialXR(true);
  };

  const copyPairingCode = () => {
    navigator.clipboard.writeText(pairingCode);
    setPairCodeCopied(true);
    setTimeout(() => setPairCodeCopied(false), 2000);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = () => { setUploadedImage(reader.result as string); setUploadedBlob(file); };
      reader.readAsDataURL(file);
    }
  };

  // ─── Render ──────────────────────────────────────────────────────────────────

  return (
    <>
      {/* ── Cardboard VR Overlay ── */}
      <StereoCardboardView
        videoRef={videoRef}
        text={text}
        cells={mappedCells}
        gyro={gyroAngles}
        isActive={showCardboard}
        onExit={() => { setShowCardboard(false); setIsLiveScan(false); speak('Cardboard VR exited.'); }}
      />

      {/* ── Spatial XR Overlay ── */}
      <SpatialXRView
        text={text}
        cells={mappedCells}
        isActive={showSpatialXR}
        onExit={() => { setShowSpatialXR(false); speak('Spatial XR exited.'); }}
      />

      <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl flex flex-col flex-shrink-0">

        {/* ── Mode Tabs ── */}
        <div className="grid grid-cols-2 sm:grid-cols-4 border-b border-slate-800 p-2 gap-2 bg-slate-950">
          <button
            onClick={() => switchTab('camera')}
            className={`py-2 rounded-xl flex items-center justify-center gap-2 text-sm font-semibold transition-all ${
              activeTab === 'camera' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900'
            }`}
          >
            <Camera size={16} /> Camera
          </button>

          <button
            onClick={() => switchTab('cardboard')}
            className={`py-2 rounded-xl flex items-center justify-center gap-2 text-sm font-semibold transition-all ${
              activeTab === 'cardboard'
                ? 'bg-gradient-to-r from-violet-600 to-purple-600 text-white shadow-lg shadow-purple-700/20'
                : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900'
            }`}
          >
            <Smartphone size={16} /> Cardboard VR
          </button>

          <button
            onClick={() => switchTab('headset')}
            className={`py-2 rounded-xl flex items-center justify-center gap-2 text-sm font-semibold transition-all ${
              activeTab === 'headset'
                ? 'bg-gradient-to-r from-indigo-600 to-cyan-600 text-white shadow-lg shadow-indigo-700/20'
                : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900'
            }`}
          >
            <Glasses size={16} /> Smart Glasses
          </button>

          <button
            onClick={() => switchTab('upload')}
            className={`py-2 rounded-xl flex items-center justify-center gap-2 text-sm font-semibold transition-all ${
              activeTab === 'upload' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900'
            }`}
          >
            <Image size={16} /> Upload
          </button>
        </div>

        {/* ── Main Display ── */}
        <div className="relative aspect-video min-h-[360px] md:min-h-[480px] w-full bg-black flex items-center justify-center overflow-hidden">

          {/* Standard camera feed (hidden but always mounted when camera tab or cardboard) */}
          {(activeTab === 'camera' || activeTab === 'cardboard') && (
            <div className={`relative w-full h-full ${activeTab === 'cardboard' ? 'hidden' : ''}`}>
              {isLive ? (
                <div className="relative w-full h-full">
                  <video ref={videoRef} className="w-full h-full object-cover" autoPlay playsInline muted />
                  <canvas ref={canvasRef} className="hidden" />
                  {debuggerOverlay}
                  {isLiveScan && (
                    <div className="absolute inset-0 border-4 border-green-500 pointer-events-none animate-pulse z-10" />
                  )}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center gap-4 text-center px-6 w-full h-full">
                  <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center text-slate-400">
                    <Camera size={32} />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-200">Camera offline</h3>
                    <p className="text-sm text-slate-500 mt-1 max-w-sm">
                      {cameraError || 'Start the camera to begin scanning.'}
                    </p>
                  </div>
                  <button onClick={startCamera} className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-semibold text-sm transition-all">
                    Start Camera
                  </button>
                </div>
              )}
            </div>
          )}

          {/* ── Cardboard VR Setup Panel ── */}
          {activeTab === 'cardboard' && (
            <div className="w-full h-full flex flex-col items-center justify-center gap-6 p-6 bg-gradient-to-b from-slate-950 to-slate-900">
              {/* Hidden video for capture */}
              <video ref={videoRef} className="hidden" autoPlay playsInline muted />
              <canvas ref={canvasRef} className="hidden" />

              <div className="text-center max-w-sm">
                <div className="w-20 h-20 rounded-full bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-purple-700/30">
                  <Smartphone size={40} className="text-white" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">Google Cardboard VR Mode</h3>
                <p className="text-sm text-slate-400 leading-relaxed">
                  Place your phone in a Cardboard or VR Box headset. The screen splits into two eyes with
                  the rear camera as real-world passthrough. Translated Braille text floats in 3D in front of you.
                </p>
              </div>

              <div className="flex flex-col gap-3 w-full max-w-xs">
                <button
                  onClick={enterCardboardVR}
                  disabled={!isLive}
                  className="w-full py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-bold rounded-xl shadow-lg shadow-purple-700/30 hover:scale-105 transition-all active:scale-95 disabled:opacity-50 disabled:scale-100 flex items-center justify-center gap-2"
                >
                  <Smartphone size={18} />
                  {isLive ? 'Enter Cardboard VR' : 'Start Camera First'}
                </button>

                {!isLive && (
                  <button onClick={startCamera} className="w-full py-2.5 border border-slate-700 text-slate-300 hover:bg-slate-800 font-semibold rounded-xl text-sm transition-all">
                    Start Camera
                  </button>
                )}

                <p className="text-center text-[11px] text-slate-500">
                  Voice commands work inside VR: "Read", "Stop", "Translate to Hindi"
                </p>
              </div>
            </div>
          )}

          {/* ── Smart Glasses / Standalone Headset Panel ── */}
          {activeTab === 'headset' && (
            <div className="w-full h-full flex flex-col items-center justify-center gap-6 p-6 bg-gradient-to-b from-slate-950 to-slate-900">
              <div className="text-center max-w-sm">
                <div className="w-20 h-20 rounded-full bg-gradient-to-br from-indigo-600 to-cyan-600 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-indigo-700/30">
                  <Glasses size={40} className="text-white" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">Smart Glasses / Headset Mode</h3>
                <p className="text-sm text-slate-400 leading-relaxed">
                  For Meta Quest, Apple Vision Pro, or any WebXR-capable headset.
                  Keep your phone scanning, and open the 3D Spatial View on your headset browser.
                  Text floats as spatial 3D billboards in your field of view.
                </p>
              </div>

              {/* Pairing code */}
              <div className="bg-slate-900 border border-indigo-500/30 rounded-2xl p-4 w-full max-w-xs text-center">
                <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-2">Session Code</p>
                <div className="flex items-center justify-center gap-3">
                  <span className="text-4xl font-black text-indigo-400 tracking-[0.25em]">{pairingCode}</span>
                  <button onClick={copyPairingCode} className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-100 transition-colors">
                    {pairCodeCopied ? <Check size={16} className="text-green-400" /> : <Copy size={16} />}
                  </button>
                </div>
                <p className="text-[11px] text-slate-600 mt-2">Enter this on your headset browser to sync</p>
              </div>

              <div className="flex flex-col gap-3 w-full max-w-xs">
                <button
                  onClick={enterSpatialXR}
                  className="w-full py-3 bg-gradient-to-r from-indigo-600 to-cyan-600 text-white font-bold rounded-xl shadow-lg shadow-indigo-700/30 hover:scale-105 transition-all active:scale-95 flex items-center justify-center gap-2"
                >
                  <Glasses size={18} />
                  Open 3D Spatial View
                </button>
                <p className="text-center text-[11px] text-slate-500">
                  Use this button on your Quest/Vision Pro browser to open the floating text scene
                </p>
              </div>
            </div>
          )}

          {/* ── Upload Panel ── */}
          {activeTab === 'upload' && (
            <div className="w-full h-full p-6 flex flex-col items-center justify-center">
              {uploadedImage ? (
                <div className="relative max-h-full max-w-full">
                  <img src={uploadedImage} alt="Uploaded Braille" className="max-h-[340px] md:max-h-[440px] object-contain rounded-lg shadow-lg" />
                  {debuggerOverlay}
                </div>
              ) : (
                <label className="border-2 border-dashed border-slate-700 hover:border-slate-500 rounded-xl cursor-pointer w-full h-full max-h-[340px] md:max-h-[440px] flex flex-col items-center justify-center gap-3 text-slate-400 hover:text-slate-200 transition-all p-6">
                  <Upload size={36} />
                  <div className="text-center">
                    <p className="font-semibold text-sm">Upload Braille photograph</p>
                    <p className="text-xs text-slate-500 mt-1">PNG, JPG, or JPEG</p>
                  </div>
                  <input type="file" accept="image/*" onChange={handleFileChange} className="hidden" />
                </label>
              )}
            </div>
          )}
        </div>

        {/* ── Control Bar ── */}
        <div className="border-t border-slate-800 p-4 flex flex-wrap items-center justify-between gap-3 bg-slate-950">
          <div className="text-xs text-slate-500 font-semibold flex items-center gap-1.5">
            {isInferring ? (
              <span className="flex items-center gap-1.5 text-blue-400">
                <span className="w-2 h-2 rounded-full bg-blue-500 animate-ping" />
                Processing frame...
              </span>
            ) : isLiveScan ? (
              <span className="flex items-center gap-1.5 text-green-400">
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                Live scanning
              </span>
            ) : (
              <span className="text-slate-400">Ready</span>
            )}
          </div>

          <div className="flex gap-2">
            {activeTab === 'camera' && isLive && (
              <>
                <button
                  onClick={() => setIsLiveScan(!isLiveScan)}
                  className={`px-4 py-2 rounded-xl flex items-center gap-2 text-sm font-semibold transition-all ${
                    isLiveScan
                      ? 'bg-green-600 hover:bg-green-700 text-white shadow-lg'
                      : 'bg-slate-800 hover:bg-slate-700 text-slate-200'
                  }`}
                >
                  {isLiveScan ? <Pause size={16} /> : <Play size={16} />}
                  {isLiveScan ? 'Pause' : 'Live Scan'}
                </button>
                <button
                  onClick={handleSingleCapture}
                  disabled={isInferring}
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-800 disabled:text-slate-600 text-white rounded-xl font-semibold text-sm transition-all"
                >
                  Snapshot
                </button>
              </>
            )}

            {activeTab === 'upload' && (
              <>
                {uploadedImage && (
                  <button
                    onClick={() => { setUploadedImage(null); setUploadedBlob(null); }}
                    className="px-4 py-2 border border-slate-700 hover:bg-slate-800 text-slate-300 rounded-xl text-sm font-semibold"
                  >
                    Clear
                  </button>
                )}
                <button
                  onClick={() => uploadedBlob && onFrame(uploadedBlob)}
                  disabled={!uploadedBlob || isInferring}
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-800 disabled:text-slate-600 text-white rounded-xl font-semibold text-sm transition-all"
                >
                  Analyze File
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
