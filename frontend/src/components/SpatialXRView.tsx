import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

interface SpatialXRViewProps {
  text: string;
  cells: Array<{ x: number; y: number; w: number; h: number; char: string; confidence: number }>;
  isActive: boolean;
  onExit: () => void;
}

/**
 * SpatialXRView
 *
 * Renders a Three.js WebXR scene with floating 3D text billboards.
 * Works in three modes:
 *   1. Standalone WebXR (Meta Quest Horizon Browser, Vision Pro)
 *   2. Mobile WebXR immersive-ar
 *   3. Desktop 3D simulator (OrbitControls mouse drag fallback)
 */
export function SpatialXRView({ text, cells, isActive, onExit }: SpatialXRViewProps) {
  const mountRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const textMeshRef = useRef<THREE.Mesh | null>(null);
  const animFrameRef = useRef<number>(0);
  const [xrSupported, setXrSupported] = useState<boolean | null>(null);
  const [xrSessionActive, setXrSessionActive] = useState(false);

  // Check WebXR support on mount
  useEffect(() => {
    if (!isActive) return;
    if (navigator.xr) {
      navigator.xr.isSessionSupported('immersive-ar')
        .then(supported => setXrSupported(supported))
        .catch(() => setXrSupported(false));
    } else {
      setXrSupported(false);
    }
  }, [isActive]);

  // Build Three.js scene
  useEffect(() => {
    if (!isActive || !mountRef.current) return;

    const mount = mountRef.current;
    const W = mount.clientWidth || window.innerWidth;
    const H = mount.clientHeight || window.innerHeight;

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(W, H);
    renderer.xr.enabled = true;
    renderer.setClearColor(0x000000, xrSupported ? 0 : 1);
    mount.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Scene
    const scene = new THREE.Scene();
    sceneRef.current = scene;

    // Camera
    const camera = new THREE.PerspectiveCamera(70, W / H, 0.01, 100);
    camera.position.set(0, 1.6, 0); // eye-level height
    cameraRef.current = camera;

    // Ambient + directional lighting
    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const dir = new THREE.DirectionalLight(0xffffff, 0.8);
    dir.position.set(1, 3, 2);
    scene.add(dir);

    // Background star field for desktop simulator
    if (!xrSupported) {
      const starGeo = new THREE.BufferGeometry();
      const starCount = 800;
      const starPositions = new Float32Array(starCount * 3);
      for (let i = 0; i < starCount * 3; i++) {
        starPositions[i] = (Math.random() - 0.5) * 80;
      }
      starGeo.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
      const starMat = new THREE.PointsMaterial({ color: 0x8b8fa8, size: 0.1 });
      scene.add(new THREE.Points(starGeo, starMat));

      // Faint grid floor
      const grid = new THREE.GridHelper(20, 20, 0x1e293b, 0x1e293b);
      grid.position.y = -1.0;
      scene.add(grid);

      // Simple mouse-drag rotation for desktop
      let isDragging = false;
      let prevMouse = { x: 0, y: 0 };
      const euler = new THREE.Euler(0, 0, 0, 'YXZ');

      const onMouseDown = (e: MouseEvent) => { isDragging = true; prevMouse = { x: e.clientX, y: e.clientY }; };
      const onMouseUp = () => { isDragging = false; };
      const onMouseMove = (e: MouseEvent) => {
        if (!isDragging) return;
        const dx = (e.clientX - prevMouse.x) * 0.003;
        const dy = (e.clientY - prevMouse.y) * 0.003;
        euler.y -= dx;
        euler.x = Math.max(-Math.PI / 3, Math.min(Math.PI / 3, euler.x - dy));
        camera.quaternion.setFromEuler(euler);
        prevMouse = { x: e.clientX, y: e.clientY };
      };
      renderer.domElement.addEventListener('mousedown', onMouseDown);
      window.addEventListener('mouseup', onMouseUp);
      window.addEventListener('mousemove', onMouseMove);
    }

    // Animate
    const animate = () => {
      // Billboard: text always faces camera
      if (textMeshRef.current && cameraRef.current) {
        textMeshRef.current.lookAt(cameraRef.current.position);
      }
      renderer.render(scene, camera);
    };

    renderer.setAnimationLoop(animate);

    // Resize handler
    const onResize = () => {
      const nW = mount.clientWidth;
      const nH = mount.clientHeight;
      camera.aspect = nW / nH;
      camera.updateProjectionMatrix();
      renderer.setSize(nW, nH);
    };
    window.addEventListener('resize', onResize);

    return () => {
      renderer.setAnimationLoop(null);
      cancelAnimationFrame(animFrameRef.current);
      window.removeEventListener('resize', onResize);
      renderer.dispose();
      if (mount.contains(renderer.domElement)) {
        mount.removeChild(renderer.domElement);
      }
    };
  }, [isActive, xrSupported]);

  // Update 3D text billboard when text changes
  useEffect(() => {
    if (!sceneRef.current || !isActive) return;

    // Remove old text mesh
    if (textMeshRef.current) {
      sceneRef.current.remove(textMeshRef.current);
      textMeshRef.current = null;
    }

    if (!text) return;

    // Draw text onto a Canvas, then use as Three.js texture
    const canvas = document.createElement('canvas');
    canvas.width = 1024;
    canvas.height = 256;
    const ctx = canvas.getContext('2d')!;

    // Panel background
    ctx.fillStyle = 'rgba(15, 23, 42, 0.9)';
    ctx.beginPath();
    (ctx as any).roundRect(8, 8, 1008, 240, 24);
    ctx.fill();

    // Purple border glow
    ctx.strokeStyle = 'rgba(139, 92, 246, 0.9)';
    ctx.lineWidth = 3;
    ctx.stroke();

    // Main text
    ctx.fillStyle = '#f1f5f9';
    ctx.font = 'bold 52px -apple-system, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const maxChars = 32;
    const displayText = text.length > maxChars ? text.substring(0, maxChars) + '…' : text;
    ctx.fillText(displayText, 512, 110);

    // Subtitle: cell count
    ctx.fillStyle = 'rgba(139, 92, 246, 0.9)';
    ctx.font = '28px -apple-system, sans-serif';
    ctx.fillText(`${cells.length} Braille cells detected`, 512, 185);

    const texture = new THREE.CanvasTexture(canvas);
    const geo = new THREE.PlaneGeometry(2.0, 0.5);
    const mat = new THREE.MeshBasicMaterial({ map: texture, transparent: true, side: THREE.DoubleSide });
    const mesh = new THREE.Mesh(geo, mat);

    // Float the billboard 2m in front of the user, at eye level
    mesh.position.set(0, 1.5, -2.0);
    sceneRef.current.add(mesh);
    textMeshRef.current = mesh;

  }, [text, cells, isActive]);

  const enterXR = async () => {
    const renderer = rendererRef.current;
    if (!renderer || !navigator.xr) return;
    try {
      const session = await navigator.xr.requestSession('immersive-ar', {
        requiredFeatures: ['local-floor'],
        optionalFeatures: ['hand-tracking', 'plane-detection'],
      });
      await renderer.xr.setSession(session);
      setXrSessionActive(true);
      session.addEventListener('end', () => setXrSessionActive(false));
    } catch (err) {
      console.error('Failed to enter XR session:', err);
    }
  };

  if (!isActive) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950 flex flex-col">
      {/* Three.js render target */}
      <div ref={mountRef} className="flex-1 w-full" />

      {/* HUD Controls */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 flex flex-col items-center gap-3">
        {/* XR status badge */}
        <div className="bg-slate-950/85 backdrop-blur-md px-4 py-2 rounded-full border border-purple-500/40 text-xs font-bold text-purple-300">
          {xrSupported === null && '⏳ Checking XR support…'}
          {xrSupported === true && !xrSessionActive && '✅ Immersive-AR available'}
          {xrSupported === true && xrSessionActive && '🥽 XR Session Active'}
          {xrSupported === false && '🖥 Desktop Simulator — Drag to look around'}
        </div>

        {/* Enter XR button */}
        {xrSupported === true && !xrSessionActive && (
          <button
            onClick={enterXR}
            className="px-6 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 text-white text-sm font-bold rounded-xl shadow-lg shadow-purple-700/30 hover:scale-105 transition-all active:scale-95"
          >
            🥽 Enter Immersive AR
          </button>
        )}
      </div>

      {/* Text preview HUD */}
      {text && (
        <div className="absolute bottom-16 left-1/2 -translate-x-1/2 z-50 bg-slate-950/80 border border-purple-500/30 backdrop-blur-md px-6 py-3 rounded-2xl text-center max-w-sm">
          <p className="text-purple-400 text-[10px] font-bold uppercase tracking-wider mb-1">Floating in your headset</p>
          <p className="text-slate-100 font-mono text-base">{text.substring(0, 50)}{text.length > 50 ? '…' : ''}</p>
        </div>
      )}

      {/* Exit */}
      <button
        onClick={onExit}
        className="absolute bottom-4 left-1/2 -translate-x-1/2 z-50 px-6 py-2 bg-slate-900/90 border border-slate-700 text-slate-300 text-xs font-bold rounded-full hover:bg-slate-800 transition-all"
      >
        ✕ Exit XR View
      </button>
    </div>
  );
}
