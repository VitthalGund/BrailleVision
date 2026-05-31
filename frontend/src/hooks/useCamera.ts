import { useState, useEffect, useCallback, useRef } from 'react';

export function useCamera() {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [isLive, setIsLive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const activeStreamRef = useRef<MediaStream | null>(null);

  const stopCamera = useCallback(() => {
    if (activeStreamRef.current) {
      activeStreamRef.current.getTracks().forEach((track) => track.stop());
      activeStreamRef.current = null;
    }
    setStream(null);
    setIsLive(false);
  }, []);

  const startCamera = useCallback(async () => {
    // Clear any active camera stream first
    stopCamera();
    setError(null);

    const constraints: MediaStreamConstraints = {
      video: {
        facingMode: { ideal: 'environment' }, // Rear camera
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false, // Don't request mic
    };

    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      activeStreamRef.current = mediaStream;
      setStream(mediaStream);
      setIsLive(true);
      return mediaStream;
    } catch (err: any) {
      console.error('Camera access error:', err);
      let errMsg = 'Could not access the camera. ';
      if (err.name === 'NotAllowedError') {
        errMsg += 'Camera permissions were denied.';
      } else if (err.name === 'NotFoundError') {
        errMsg += 'No camera device found on this machine.';
      } else {
        errMsg += err.message || '';
      }
      setError(errMsg);
      setIsLive(false);
      return null;
    }
  }, [stopCamera]);

  // Clean up media tracks on component unmount
  useEffect(() => {
    return () => {
      if (activeStreamRef.current) {
        activeStreamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  return {
    stream,
    isLive,
    error,
    startCamera,
    stopCamera,
  };
}
