import React from 'react';
import { Camera, History, Settings, Moon, Sun } from 'lucide-react';
import { useSettingsStore } from '../stores/settingsStore';

export type ActiveTab = 'scan' | 'history' | 'settings';

interface NavBarProps {
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
}

export function NavBar({ activeTab, setActiveTab }: NavBarProps) {
  const { darkMode, toggleDarkMode } = useSettingsStore();

  const navItems = [
    { id: 'scan' as ActiveTab, label: 'Scan', icon: Camera },
    { id: 'history' as ActiveTab, label: 'History', icon: History },
    { id: 'settings' as ActiveTab, label: 'Settings', icon: Settings },
  ];

  return (
    <>
      {/* Desktop Sidebar (visible on md screens and up) */}
      <aside className="hidden md:flex flex-col w-64 bg-slate-900 border-r border-slate-800 text-slate-100 min-h-screen p-4 flex-shrink-0">
        <div className="flex items-center gap-3 px-2 py-4 mb-8">
          <div className="w-10 h-10 rounded-lg bg-vision-blue flex items-center justify-center font-bold text-xl text-white shadow-lg shadow-blue-500/20">
            BV
          </div>
          <div>
            <h1 className="font-bold text-lg leading-none">BrailleVision</h1>
            <span className="text-xs text-slate-400">Accessibility Reader</span>
          </div>
        </div>

        <nav className="flex-1 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-vision-blue text-white shadow-md shadow-blue-600/10'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100'
                }`}
              >
                <Icon size={20} className={isActive ? 'text-white' : 'text-slate-400'} />
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="border-t border-slate-800 pt-4 mt-auto">
          <button
            onClick={toggleDarkMode}
            className="w-full flex items-center justify-between px-4 py-3 text-slate-400 hover:text-slate-100 rounded-lg hover:bg-slate-800 text-sm font-medium transition-all"
          >
            <span className="flex items-center gap-3">
              {darkMode ? <Sun size={20} /> : <Moon size={20} />}
              {darkMode ? 'Light Mode' : 'Dark Mode'}
            </span>
          </button>
        </div>
      </aside>

      {/* Mobile Header / Bottom Tabs (visible on mobile < md) */}
      <div className="md:hidden flex flex-col w-full flex-shrink-0">
        <header className="flex items-center justify-between px-4 py-3 bg-slate-900 border-b border-slate-800 text-slate-100">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-vision-blue flex items-center justify-center font-bold text-white">
              BV
            </div>
            <h1 className="font-bold text-md">BrailleVision</h1>
          </div>
          <button
            onClick={toggleDarkMode}
            className="p-2 text-slate-400 hover:text-slate-100 transition-colors"
            aria-label="Toggle theme"
          >
            {darkMode ? <Sun size={20} /> : <Moon size={20} />}
          </button>
        </header>

        {/* Bottom Tab Bar */}
        <nav className="fixed bottom-0 left-0 right-0 z-50 bg-slate-900 border-t border-slate-800 flex justify-around py-1 shadow-lg shadow-black/40">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex flex-col items-center gap-1 py-1 px-4 text-xs font-medium transition-all ${
                  isActive ? 'text-vision-blue font-bold scale-105' : 'text-slate-400'
                }`}
              >
                <Icon size={20} className={isActive ? 'text-vision-blue' : 'text-slate-400'} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </>
  );
}
