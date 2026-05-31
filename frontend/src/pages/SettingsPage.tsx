import React from 'react';
import { Volume2, LayoutGrid, Palette, Shield } from 'lucide-react';
import { useSettingsStore } from '../stores/settingsStore';

export function SettingsPage() {
  const {
    ttsEnabled,
    ttsRate,
    ttsPitch,
    showDebugger,
    darkMode,
    setTtsEnabled,
    setTtsRate,
    setTtsPitch,
    setShowDebugger,
    toggleDarkMode,
  } = useSettingsStore();

  return (
    <div className="flex-1 flex flex-col gap-6 p-4 md:p-6 pb-20 md:pb-6 overflow-y-auto bg-slate-950 text-slate-100">
      <div>
        <h2 className="text-xl md:text-2xl font-bold tracking-tight text-slate-100">App Settings</h2>
        <p className="text-xs md:text-sm text-slate-400 mt-0.5">
          Configure reader interface layouts and narration playback behaviors.
        </p>
      </div>

      <div className="space-y-6 max-w-2xl">
        {/* Section 1: TTS Configurations */}
        <section className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-md flex flex-col gap-4">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
            <Volume2 className="text-vision-blue" size={20} />
            <h3 className="font-bold text-slate-200 text-sm">Text-To-Speech (SpeechSynthesis)</h3>
          </div>

          <div className="flex items-center justify-between py-2">
            <div>
              <p className="text-sm font-semibold text-slate-200">Read aloud automatically</p>
              <p className="text-xs text-slate-500">Enable automatic narration of translations</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={ttsEnabled}
                onChange={(e) => setTtsEnabled(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-slate-400 after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-vision-blue peer-checked:after:bg-white" />
            </label>
          </div>

          {ttsEnabled && (
            <div className="space-y-4 pt-2 border-t border-slate-800/40">
              {/* Rate Slider */}
              <div className="flex flex-col gap-1.5">
                <div className="flex justify-between text-xs font-semibold text-slate-400">
                  <span>Speech Rate</span>
                  <span>{ttsRate.toFixed(1)}x</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="2.0"
                  step="0.1"
                  value={ttsRate}
                  onChange={(e) => setTtsRate(parseFloat(e.target.value))}
                  className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-vision-blue"
                />
              </div>

              {/* Pitch Slider */}
              <div className="flex flex-col gap-1.5">
                <div className="flex justify-between text-xs font-semibold text-slate-400">
                  <span>Pitch Tone</span>
                  <span>{ttsPitch.toFixed(1)}</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="1.5"
                  step="0.1"
                  value={ttsPitch}
                  onChange={(e) => setTtsPitch(parseFloat(e.target.value))}
                  className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-vision-blue"
                />
              </div>
            </div>
          )}
        </section>

        {/* Section 2: Reader Overlay settings */}
        <section className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-md flex flex-col gap-4">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
            <LayoutGrid className="text-electric-teal" size={20} />
            <h3 className="font-bold text-slate-200 text-sm">Overlay Settings</h3>
          </div>

          <div className="flex items-center justify-between py-1">
            <div>
              <p className="text-sm font-semibold text-slate-200">Show Cell Debugger</p>
              <p className="text-xs text-slate-500">Overlays bounding boxes and dot values over images</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={showDebugger}
                onChange={(e) => setShowDebugger(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-slate-400 after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-electric-teal peer-checked:after:bg-white" />
            </label>
          </div>
        </section>

        {/* Section 3: System / Appearance */}
        <section className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-md flex flex-col gap-4">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
            <Palette className="text-slate-400" size={20} />
            <h3 className="font-bold text-slate-200 text-sm">Theme Appearance</h3>
          </div>

          <div className="flex items-center justify-between py-1">
            <div>
              <p className="text-sm font-semibold text-slate-200">Dark Mode theme</p>
              <p className="text-xs text-slate-500">Toggle dark/light visual style configurations</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={darkMode}
                onChange={toggleDarkMode}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-slate-400 after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-vision-blue peer-checked:after:bg-white" />
            </label>
          </div>
        </section>
      </div>
    </div>
  );
}
