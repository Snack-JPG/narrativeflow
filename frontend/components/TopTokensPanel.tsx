'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { marketAPI } from '@/lib/api';

interface Token {
  symbol: string;
  price: number;
  market_cap: number;
  volume_24h: number;
  price_change_24h: number;
  narrative: string;
  undervaluation_score?: number;
}

interface Props {
  narrative: string | null;
}

export default function TopTokensPanel({ narrative }: Props) {
  const [tokens, setTokens] = useState<Token[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTokens();
  }, [narrative]);

  const loadTokens = async () => {
    try {
      const data = await marketAPI.getPrices(undefined, narrative || undefined, 24);

      // Calculate undervaluation scores (simplified)
      const enrichedTokens = data.map((token: any) => ({
        ...token,
        undervaluation_score: calculateUndervaluationScore(token)
      }));

      // Sort by undervaluation score
      enrichedTokens.sort((a: Token, b: Token) =>
        (b.undervaluation_score || 0) - (a.undervaluation_score || 0)
      );

      setTokens(enrichedTokens.slice(0, 10));
      setLoading(false);
    } catch (error) {
      console.error('Failed to load tokens:', error);
      // Use mock data for demo
      setTokens(getMockTokens(narrative));
      setLoading(false);
    }
  };

  const calculateUndervaluationScore = (token: any) => {
    // Simple scoring: low price change + high volume = potentially undervalued
    const priceScore = Math.max(0, 1 - Math.abs(token.price_change_24h || 0));
    const volumeScore = Math.min(1, (token.volume_24h || 0) / 10000000);
    return (priceScore * 0.6 + volumeScore * 0.4) * 100;
  };

  const getMockTokens = (narrative: string | null): Token[] => {
    const baseTokens: Record<string, Token[]> = {
      AI: [
        { symbol: 'TAO', price: 456.78, market_cap: 3200000000, volume_24h: 45000000, price_change_24h: 0.02, narrative: 'AI' },
        { symbol: 'FET', price: 0.67, market_cap: 1800000000, volume_24h: 120000000, price_change_24h: -0.03, narrative: 'AI' },
        { symbol: 'RNDR', price: 7.89, market_cap: 2900000000, volume_24h: 89000000, price_change_24h: 0.05, narrative: 'AI' },
      ],
      RWA: [
        { symbol: 'ONDO', price: 0.89, market_cap: 1200000000, volume_24h: 34000000, price_change_24h: 0.08, narrative: 'RWA' },
        { symbol: 'POLYX', price: 0.34, market_cap: 340000000, volume_24h: 12000000, price_change_24h: -0.02, narrative: 'RWA' },
        { symbol: 'RIO', price: 1.23, market_cap: 450000000, volume_24h: 8000000, price_change_24h: 0.15, narrative: 'RWA' },
      ],
      DePIN: [
        { symbol: 'HNT', price: 5.67, market_cap: 890000000, volume_24h: 23000000, price_change_24h: 0.04, narrative: 'DePIN' },
        { symbol: 'MOBILE', price: 0.002, market_cap: 120000000, volume_24h: 5000000, price_change_24h: 0.12, narrative: 'DePIN' },
        { symbol: 'HONEY', price: 0.045, market_cap: 67000000, volume_24h: 2000000, price_change_24h: -0.05, narrative: 'DePIN' },
      ],
    };

    const defaultTokens = Object.values(baseTokens).flat();
    const selectedTokens = narrative && baseTokens[narrative] ? baseTokens[narrative] : defaultTokens;

    return selectedTokens.map(token => ({
      ...token,
      undervaluation_score: calculateUndervaluationScore(token)
    })).sort((a, b) => (b.undervaluation_score || 0) - (a.undervaluation_score || 0));
  };

  const formatPrice = (price: number) => {
    if (price >= 1000) return `$${(price / 1000).toFixed(1)}k`;
    if (price >= 1) return `$${price.toFixed(2)}`;
    return `$${price.toFixed(4)}`;
  };

  const formatMarketCap = (cap: number) => {
    if (cap >= 1000000000) return `$${(cap / 1000000000).toFixed(1)}B`;
    if (cap >= 1000000) return `$${(cap / 1000000).toFixed(1)}M`;
    return `$${(cap / 1000).toFixed(0)}K`;
  };

  if (loading) {
    return (
      <div className="space-y-2">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-12 bg-dark-300/20 rounded loading-pulse"></div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {tokens.length === 0 ? (
        <div className="text-center py-4 text-gray-500">
          <p>No tokens found</p>
        </div>
      ) : (
        tokens.map((token, index) => (
          <motion.div
            key={token.symbol}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.05 }}
            className="p-3 rounded-lg bg-dark-300/30 border border-dark-400 hover:bg-dark-300/50 transition-colors cursor-pointer"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <span className="font-bold text-sm">{token.symbol}</span>
                <span className="text-xs text-gray-400 px-2 py-0.5 rounded bg-dark-400/50">
                  {token.narrative}
                </span>
              </div>
              <div className="text-right">
                <div className="font-semibold text-sm">{formatPrice(token.price)}</div>
                <div className={`text-xs ${
                  token.price_change_24h > 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  {token.price_change_24h > 0 ? '+' : ''}{(token.price_change_24h * 100).toFixed(1)}%
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between text-xs text-gray-400">
              <div>MCap: {formatMarketCap(token.market_cap)}</div>
              <div>Vol: {formatMarketCap(token.volume_24h)}</div>
              {token.undervaluation_score && (
                <div className="flex items-center space-x-1">
                  <span>Score:</span>
                  <span className={`font-semibold ${
                    token.undervaluation_score > 70 ? 'text-green-400' :
                    token.undervaluation_score > 40 ? 'text-yellow-400' :
                    'text-gray-400'
                  }`}>
                    {token.undervaluation_score.toFixed(0)}
                  </span>
                </div>
              )}
            </div>

            {/* Visual score indicator */}
            {token.undervaluation_score && (
              <div className="mt-2 h-1 bg-dark-500 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-primary-500 to-purple-600"
                  initial={{ width: 0 }}
                  animate={{ width: `${token.undervaluation_score}%` }}
                  transition={{ duration: 0.5, delay: index * 0.05 }}
                />
              </div>
            )}
          </motion.div>
        ))
      )}
    </div>
  );
}