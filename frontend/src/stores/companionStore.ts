import { create } from 'zustand';

export type DeviceRole = 'phone' | 'headset' | 'standalone';
export type VRMode = 'cardboard' | 'webxr' | null;

interface CompanionState {
  // Pairing
  pairingCode: string;
  deviceRole: DeviceRole;
  isHeadsetConnected: boolean;
  activeMode: VRMode;

  // Live spatial data streamed from phone to headset
  spatialText: string;
  spatialCells: Array<{ x: number; y: number; w: number; h: number; char: string; confidence: number }>;
  dotCount: number;
  frameWidth: number;
  frameHeight: number;

  // Actions
  setPairingCode: (code: string) => void;
  setDeviceRole: (role: DeviceRole) => void;
  setHeadsetConnected: (connected: boolean) => void;
  setActiveMode: (mode: VRMode) => void;
  updateSpatialData: (data: {
    text: string;
    cells: CompanionState['spatialCells'];
    dotCount: number;
    frameWidth: number;
    frameHeight: number;
  }) => void;
  reset: () => void;
}

const generateCode = () =>
  Math.floor(1000 + Math.random() * 9000).toString();

export const useCompanionStore = create<CompanionState>((set) => ({
  pairingCode: generateCode(),
  deviceRole: 'standalone',
  isHeadsetConnected: false,
  activeMode: null,
  spatialText: '',
  spatialCells: [],
  dotCount: 0,
  frameWidth: 640,
  frameHeight: 480,

  setPairingCode: (code) => set({ pairingCode: code }),
  setDeviceRole: (role) => set({ deviceRole: role }),
  setHeadsetConnected: (connected) => set({ isHeadsetConnected: connected }),
  setActiveMode: (mode) => set({ activeMode: mode }),
  updateSpatialData: (data) =>
    set({
      spatialText: data.text,
      spatialCells: data.cells,
      dotCount: data.dotCount,
      frameWidth: data.frameWidth,
      frameHeight: data.frameHeight,
    }),
  reset: () =>
    set({
      pairingCode: generateCode(),
      isHeadsetConnected: false,
      activeMode: null,
      spatialText: '',
      spatialCells: [],
      dotCount: 0,
    }),
}));
