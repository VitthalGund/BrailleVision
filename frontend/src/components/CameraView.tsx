import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Camera, Image, RefreshCw, Upload, Play, Pause, AlertTriangle } from 'lucide-react';
import { useCamera } from '../hooks/useCamera';

interface CameraViewProps {
  onFrame: (blob: Blob) => void;
  isInferring: boolean;
  debuggerOverlay?: React.ReactNode;
}

export function CameraView({ onFrame, isInferring, debuggerOverlay }: CameraViewProps) {
  const { stream, isLive, error: cameraError, startCamera, stopCamera } = useCamera();
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  const [isLiveScan, setIsLiveScan] = useState(false);
  const [activeMode, setActiveMode] = useState<'camera' | 'upload'>('camera');
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);
  const [uploadedBlob, setUploadedBlob] = useState<Blob | null>(null);

  // Sync camera stream with HTML5 video element
  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream]);

  // Handle auto-capture loops in Live Scan mode
  useEffect(() => {
    if (!isLive || !isLiveScan || activeMode !== 'camera') return;

    let timeoutId: any;

    
    const captureLoop = () => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (video && canvas && isLiveScan && !isInferring) {
        const ctx = canvas.getContext('2d');
        if (ctx) {
          // Adjust canvas dimensions to match current video aspect ratio
          canvas.width = video.videoWidth || 640;
          canvas.height = video.videoHeight || 480;
          
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
          canvas.toBlob((blob) => {
            if (blob) {
              onFrame(blob);
            }
          }, 'image/jpeg', 0.85);
        }
      }
      
      // Throttle captures to every 1.5 seconds to avoid over-stacking requests
      timeoutId = setTimeout(captureLoop, 1500);
    };

    captureLoop();

    return () => {
      clearTimeout(timeoutId);
    };
  }, [isLive, isLiveScan, isInferring, activeMode, onFrame]);

  // Capture a single frame manually (Manual Snapshot)
  const handleSingleCapture = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (video && canvas) {
      const ctx = canvas.getContext('2d');
      if (ctx) {
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        canvas.toBlob((blob) => {
          if (blob) {
            onFrame(blob);
          }
        }, 'image/jpeg', 0.85);
      }
    }
  }, [onFrame]);

  // Handle Drag & Drop / File Select Upload
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = () => {
        setUploadedImage(reader.result as string);
        setUploadedBlob(file);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleRunUploadInference = () => {
    if (uploadedBlob) {
      onFrame(uploadedBlob);
    }
  };

  // Toggle active mode (camera vs upload fallback)
  const toggleMode = (mode: 'camera' | 'upload') => {
    setActiveMode(mode);
    if (mode === 'upload') {
      stopCamera();
      setIsLiveScan(false);
    } else {
      startCamera();
    }
  };

  return (
    <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl flex flex-col">
      {/* Mode Selector Tabs */}
      <div className="flex border-b border-slate-800 p-2 gap-2 bg-slate-950">
        <button
          onClick={() => toggleMode('camera')}
          className={`flex-1 py-2 rounded-xl flex items-center justify-center gap-2 text-sm font-semibold transition-all ${
            activeMode === 'camera'
              ? 'bg-vision-blue text-white shadow-md'
              : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900'
          }`}
        >
          <Camera size={18} />
          Camera Feed
        </button>
        <button
          onClick={() => toggleMode('upload')}
          className={`flex-1 py-2 rounded-xl flex items-center justify-center gap-2 text-sm font-semibold transition-all ${
            activeMode === 'upload'
              ? 'bg-vision-blue text-white shadow-md'
              : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900'
          }`}
        >
          <Image size={18} />
          File Upload Fallback
        </button>
      </div>

      {/* Main Display Frame */}
      <div className="relative aspect-video bg-black flex items-center justify-center overflow-hidden">
        {activeMode === 'camera' ? (
          <>
            {isLive ? (
              <div className="relative w-full h-full">
                <video
                  ref={videoRef}
                  className="w-full h-full object-cover"
                  autoPlay
                  playsInline
                  muted
                  aria-label="Live camera feed for Braille recognition"
                />
                
                {/* Canvas used internally for capturing blob data */}
                <canvas ref={canvasRef} className="hidden" />

                {/* Bounding box / Debugger SVG/Canvas Overlay */}
                {debuggerOverlay}

                {/* Pulse Border Indicator when scanning live */}
                {isLiveScan && (
                  <div className="absolute inset-0 border-4 border-green-500 rounded-none pointer-events-none animate-pulse z-10" />
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center gap-4 text-center px-6">
                <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center text-slate-400">
                  <Camera size={32} />
                </div>
                <div>
                  <h3 className="font-bold text-slate-200">Camera offline</h3>
                  <p className="text-sm text-slate-500 mt-1 max-w-sm">
                    {cameraError || 'Activate the live video scanning mode to read physical Braille.'}
                  </p>
                </div>
                <button
                  onClick={startCamera}
                  className="px-6 py-2.5 bg-vision-blue hover:bg-blue-700 text-white rounded-xl font-semibold text-sm transition-all active:scale-95 shadow-lg"
                >
                  Start Camera
                </button>
              </div>
            )}
          </>
        ) : (
          /* File Upload Display */
          <div className="w-full h-full p-6 flex flex-col items-center justify-center">
            {uploadedImage ? (
              <div className="relative max-h-full max-w-full">
                <img
                  src={uploadedImage}
                  alt="Uploaded Braille source"
                  className="max-h-[300px] object-contain rounded-lg shadow-lg"
                />
                {debuggerOverlay}
              </div>
            ) : (
              <label className="border-2 border-dashed border-slate-700 hover:border-slate-500 rounded-xl cursor-pointer w-full h-full max-h-[260px] flex flex-col items-center justify-center gap-3 text-slate-400 hover:text-slate-200 transition-all p-6">
                <Upload size={36} />
                <div className="text-center">
                  <p className="font-semibold text-sm">Upload Braille photograph</p>
                  <p className="text-xs text-slate-500 mt-1">Supports PNG, JPG, or JPEG</p>
                </div>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleFileChange}
                  className="hidden"
                />
              </label>
            )}
          </div>
        )}
      </div>

      {/* Control Actions Bar */}
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
              Scanning live
            </span>
          ) : (
            <span className="text-slate-400">Ready</span>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex gap-2">
          {activeMode === 'camera' && isLive && (
            <>
              <button
                onClick={() => setIsLiveScan(!isLiveScan)}
                className={`px-4 py-2 rounded-xl flex items-center gap-2 text-sm font-semibold transition-all ${
                  isLiveScan
                    ? 'bg-green-600 hover:bg-green-700 text-white shadow-lg shadow-green-600/10'
                    : 'bg-slate-800 hover:bg-slate-700 text-slate-200'
                }`}
              >
                {isLiveScan ? <Pause size={16} /> : <Play size={16} />}
                {isLiveScan ? 'Pause Auto-Scan' : 'Live Scan'}
              </button>

              <button
                onClick={handleSingleCapture}
                disabled={isInferring}
                className="px-5 py-2 bg-vision-blue hover:bg-blue-700 disabled:bg-slate-800 disabled:text-slate-600 text-white rounded-xl font-semibold text-sm transition-all shadow-lg active:scale-95"
              >
                Snapshot
              </button>
            </>
          )}

          {activeMode === 'upload' && (
            <>
              {uploadedImage && (
                <button
                  onClick={() => {
                    setUploadedImage(null);
                    setUploadedBlob(null);
                  }}
                  className="px-4 py-2 border border-slate-700 hover:bg-slate-800 text-slate-300 rounded-xl text-sm font-semibold"
                >
                  Clear File
                </button>
              )}
              <button
                onClick={handleRunUploadInference}
                disabled={!uploadedBlob || isInferring}
                className="px-5 py-2 bg-vision-blue hover:bg-blue-700 disabled:bg-slate-800 disabled:text-slate-600 text-white rounded-xl font-semibold text-sm transition-all shadow-lg shadow-blue-500/10"
              >
                Analyze File
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
