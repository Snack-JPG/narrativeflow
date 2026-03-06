'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { briefingAPI, Briefing } from '@/lib/api';
import { format } from 'date-fns';

export default function AIBriefingPanel() {
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    loadLatestBriefing();
  }, []);

  const loadLatestBriefing = async () => {
    try {
      const data = await briefingAPI.getLatest();
      setBriefing(data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load briefing:', error);
      // Use mock data for demo
      setBriefing(getMockBriefing());
      setLoading(false);
    }
  };

  const generateNewBriefing = async () => {
    setGenerating(true);
    try {
      const data = await briefingAPI.generate(24, true);
      setBriefing(data);
    } catch (error) {
      console.error('Failed to generate briefing:', error);
      // Use mock data for demo
      setBriefing(getMockBriefing());
    }
    setGenerating(false);
  };

  const getMockBriefing = (): Briefing => ({
    timestamp: new Date().toISOString(),
    executive_summary: "AI narrative shows strongest momentum with TAO leading. Smart money accumulating RWA tokens while prices remain flat. DePIN seeing increased developer activity.",
    emerging_narratives: [
      { name: 'AI Agents', signal: 'early_entry', confidence: 0.85 },
      { name: 'Bitcoin L2s', signal: 'whisper', confidence: 0.72 }
    ],
    overheated_narratives: [
      { name: 'Memecoins', signal: 'peak', confidence: 0.91 }
    ],
    key_catalysts: [
      { event: 'Coinbase launches AI agent wallets', narrative: 'AI', impact: 'high' },
      { event: 'BlackRock expands RWA program', narrative: 'RWA', impact: 'medium' }
    ],
    divergences: [],
    market_regime: { overall: 'accumulation', confidence: 'high' },
    recommendations: [
      { action: 'accumulate', narrative: 'AI', tokens: ['TAO', 'FET'], reason: 'Strong fundamentals, price lagging' },
      { action: 'watch', narrative: 'RWA', tokens: ['ONDO'], reason: 'Whale accumulation detected' },
      { action: 'reduce', narrative: 'Memecoin', tokens: [], reason: 'Overheated, rotation likely' }
    ],
    markdown_output: '',
    json_output: {}
  });

  if (loading) {
    return (
      <div className="space-y-3">
        <div className="h-20 bg-dark-300/20 rounded loading-pulse"></div>
        <div className="h-32 bg-dark-300/20 rounded loading-pulse"></div>
      </div>
    );
  }

  if (!briefing) {
    return (
      <div className="text-center py-4">
        <p className="text-gray-500 mb-4">No briefing available</p>
        <button
          onClick={generateNewBriefing}
          disabled={generating}
          className="px-4 py-2 bg-primary-600 hover:bg-primary-700 rounded-lg text-sm font-medium transition-colors"
        >
          {generating ? 'Generating...' : 'Generate Briefing'}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="text-xs text-gray-400">
          {format(new Date(briefing.timestamp), 'MMM dd, HH:mm')}
        </div>
        <button
          onClick={generateNewBriefing}
          disabled={generating}
          className="px-3 py-1 bg-dark-400 hover:bg-dark-500 rounded text-xs transition-colors"
        >
          {generating ? '...' : 'Refresh'}
        </button>
      </div>

      {/* Executive Summary */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-3 rounded-lg bg-gradient-to-br from-primary-600/20 to-purple-600/20 border border-primary-500/30"
      >
        <h4 className="text-xs font-semibold text-primary-400 mb-2">Executive Summary</h4>
        <p className="text-sm text-gray-200 leading-relaxed">
          {briefing.executive_summary}
        </p>
      </motion.div>

      {/* Key Insights */}
      <div className="space-y-3">
        {/* Emerging Narratives */}
        {briefing.emerging_narratives.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-400 mb-2">🚀 Emerging</h4>
            <div className="space-y-1">
              {briefing.emerging_narratives.map((narrative: any, i: number) => (
                <div key={i} className="flex items-center justify-between p-2 rounded bg-green-500/10 border border-green-500/30">
                  <span className="text-sm">{narrative.name}</span>
                  <span className="text-xs text-green-400">
                    {(narrative.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Overheated Narratives */}
        {briefing.overheated_narratives.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-400 mb-2">🔥 Overheated</h4>
            <div className="space-y-1">
              {briefing.overheated_narratives.map((narrative: any, i: number) => (
                <div key={i} className="flex items-center justify-between p-2 rounded bg-red-500/10 border border-red-500/30">
                  <span className="text-sm">{narrative.name}</span>
                  <span className="text-xs text-red-400">
                    {(narrative.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recommendations */}
        {briefing.recommendations.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-400 mb-2">📊 Recommendations</h4>
            <div className="space-y-2">
              {briefing.recommendations.slice(0, expanded ? undefined : 2).map((rec: any, i: number) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.1 }}
                  className="p-2 rounded bg-dark-300/50 border border-dark-400"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                      rec.action === 'accumulate' ? 'bg-green-600' :
                      rec.action === 'watch' ? 'bg-yellow-600' :
                      'bg-red-600'
                    }`}>
                      {rec.action.toUpperCase()}
                    </span>
                    <span className="text-xs text-gray-400">{rec.narrative}</span>
                  </div>
                  {rec.tokens && rec.tokens.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-1">
                      {rec.tokens.map((token: string) => (
                        <span key={token} className="text-xs px-1.5 py-0.5 bg-dark-500 rounded">
                          {token}
                        </span>
                      ))}
                    </div>
                  )}
                  <p className="text-xs text-gray-400">{rec.reason}</p>
                </motion.div>
              ))}
            </div>

            {briefing.recommendations.length > 2 && (
              <button
                onClick={() => setExpanded(!expanded)}
                className="text-xs text-primary-400 hover:text-primary-300 mt-2"
              >
                {expanded ? 'Show less' : `Show ${briefing.recommendations.length - 2} more`}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Market Regime */}
      <div className="p-2 rounded bg-dark-300/30 border border-dark-400">
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-400">Market Regime</span>
          <div className="flex items-center space-x-2">
            <span className="text-sm font-semibold capitalize">
              {briefing.market_regime.overall}
            </span>
            <span className="text-xs text-gray-500">
              ({briefing.market_regime.confidence})
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}