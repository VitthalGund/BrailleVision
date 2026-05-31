import { useEffect, useState, useRef } from 'react';

export interface GyroscopeAngles {
  alpha: number; // Yaw   — rotation around Z axis (0–360)
  beta: number;  // Pitch — rotation around X axis (-180–180), tilt forward/back
  gamma: number; // Roll  — rotation around Y axis (-90–90), tilt left/right
}

interface UseGyroscopeOptions {
  enabled: boolean;
  smoothingFactor?: number; // 0 = no smoothing, 1 = never updates. Default 0.15
}

/**
 * useGyroscope — reads device orientation for head-tracking in Cardboard VR.
 * On iOS 13+, requestPermission() must be triggered by a user gesture.
 */
export function useGyroscope({ enabled, smoothingFactor = 0.15 }: UseGyroscopeOptions) {
  const [angles, setAngles] = useState<GyroscopeAngles>({ alpha: 0, beta: 0, gamma: 0 });
  const [supported, setSupported] = useState(true);
  const [permissionGranted, setPermissionGranted] = useState(false);
  const smoothed = useRef<GyroscopeAngles>({ alpha: 0, beta: 0, gamma: 0 });

  const requestPermission = async () => {
    const DeviceOrientationEventAny = DeviceOrientationEvent as any;
    if (typeof DeviceOrientationEventAny.requestPermission === 'function') {
      try {
        const result = await DeviceOrientationEventAny.requestPermission();
        if (result === 'granted') {
          setPermissionGranted(true);
        }
      } catch (e) {
        console.error('Gyroscope permission denied:', e);
        setSupported(false);
      }
    } else {
      // Non-iOS: no permission required
      setPermissionGranted(true);
    }
  };

  useEffect(() => {
    if (!enabled) return;
    if (!window.DeviceOrientationEvent) {
      setSupported(false);
      return;
    }

    const handleOrientation = (e: DeviceOrientationEvent) => {
      const raw = {
        alpha: e.alpha ?? 0,
        beta: e.beta ?? 0,
        gamma: e.gamma ?? 0,
      };

      // Exponential low-pass filter to smooth jitter
      smoothed.current = {
        alpha: smoothed.current.alpha + smoothingFactor * (raw.alpha - smoothed.current.alpha),
        beta: smoothed.current.beta + smoothingFactor * (raw.beta - smoothed.current.beta),
        gamma: smoothed.current.gamma + smoothingFactor * (raw.gamma - smoothed.current.gamma),
      };

      setAngles({ ...smoothed.current });
    };

    window.addEventListener('deviceorientation', handleOrientation, true);
    return () => window.removeEventListener('deviceorientation', handleOrientation, true);
  }, [enabled, smoothingFactor]);

  return { angles, supported, permissionGranted, requestPermission };
}
