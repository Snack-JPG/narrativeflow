'use client';

import { useState, useEffect } from 'react';
import NarrativeHeatmap from '@/components/NarrativeHeatmap';
import DivergenceAlerts from '@/components/DivergenceAlerts';
import LifecycleTracker from '@/components/LifecycleTracker';
import TopTokensPanel from '@/components/TopTokensPanel';
import AIBriefingPanel from '@/components/AIBriefingPanel';
import RotationChart from '@/components/RotationChart';
import wsClient from '@/lib/websocket';

export default function Dashboard() {
  const [connected, setConnected] = useState(false);
  const [selectedNarrative, setSelectedNarrative] = useState<string | null>(null);

  useEffect(() => {
    // Connect to WebSocket
    wsClient.connect();

    // Listen for connection status
    const cleanupConnected = wsClient.on('connected', setConnected);

    // Subscribe to alerts
    wsClient.subscribe({
      signal_types: ['early_entry', 'accumulation'],
      min_confidence: 0.7,
      message_types: ['divergence_alert', 'lifecycle_change', 'whale_move', 'catalyst_event']
    });

    // Cleanup
    return () => {
      cleanupConnected();
      wsClient.disconnect();
    };
  }, []);

  return (
    <div className="min-h-screen bg-dark-100 text-gray-100">
      {/* Header */}
      <header className="glass border-b border-dark-300/50 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <h1 className="text-2xl font-bold bg-gradient-to-r from-primary-500 to-purple-600 bg-clip-text text-transparent">
                NarrativeFlow
              </h1>
              <span className="text-sm text-gray-400">
                Crypto Narrative Rotation Tracker
              </span>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
                <span className="text-sm text-gray-400">
                  {connected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-12 gap-6">
          {/* Left Column - Heatmap & Lifecycle */}
          <div className="col-span-8 space-y-6">
            {/* Narrative Heatmap */}
            <div className="glass rounded-xl p-6">
              <h2 className="text-xl font-semibold mb-4">Narrative Momentum Heatmap</h2>
              <NarrativeHeatmap onNarrativeSelect={setSelectedNarrative} />
            </div>

            {/* Lifecycle Tracker */}
            <div className="glass rounded-xl p-6">
              <h2 className="text-xl font-semibold mb-4">Narrative Lifecycle Tracker</h2>
              <LifecycleTracker selectedNarrative={selectedNarrative} />
            </div>

            {/* Historical Rotation Chart */}
            <div className="glass rounded-xl p-6">
              <h2 className="text-xl font-semibold mb-4">Historical Capital Rotation</h2>
              <RotationChart />
            </div>
          </div>

          {/* Right Column - Alerts & Info */}
          <div className="col-span-4 space-y-6">
            {/* Divergence Alerts */}
            <div className="glass rounded-xl p-6 max-h-[400px] overflow-y-auto">
              <h2 className="text-xl font-semibold mb-4">Real-Time Alerts</h2>
              <DivergenceAlerts />
            </div>

            {/* Top Tokens */}
            <div className="glass rounded-xl p-6">
              <h2 className="text-xl font-semibold mb-4">Top Undervalued Tokens</h2>
              <TopTokensPanel narrative={selectedNarrative} />
            </div>

            {/* AI Briefing */}
            <div className="glass rounded-xl p-6">
              <h2 className="text-xl font-semibold mb-4">Daily AI Briefing</h2>
              <AIBriefingPanel />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
