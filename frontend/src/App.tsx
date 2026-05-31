import React, { useState, useEffect } from 'react';
import { NavBar } from './components/NavBar';
import type { ActiveTab } from './components/NavBar';

import { ScanPage } from './pages/ScanPage';
import { HistoryPage } from './pages/HistoryPage';
import { SettingsPage } from './pages/SettingsPage';
import { useSettingsStore } from './stores/settingsStore';

function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('scan');
  const { darkMode } = useSettingsStore();

  // Apply dark mode styling class on mount/toggle
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  const renderActivePage = () => {
    switch (activeTab) {
      case 'scan':
        return <ScanPage />;
      case 'history':
        return <HistoryPage />;
      case 'settings':
        return <SettingsPage />;
      default:
        return <ScanPage />;
    }
  };

  return (
    <div className="flex flex-col md:flex-row w-screen h-screen bg-slate-950 text-slate-100 font-sans overflow-hidden">
      {/* Sidebar (Desktop) or Bottom Tab navigation (Mobile) */}
      <NavBar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Page Display Frame */}
      <main className="flex-1 flex flex-col min-h-0 overflow-hidden relative">
        {renderActivePage()}
      </main>
    </div>
  );
}

export default App;
