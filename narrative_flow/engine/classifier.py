"""Narrative classification engine for crypto data items."""

import re
import json
from typing import List, Dict, Set, Tuple, Optional
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class NarrativeCategory(Enum):
    """Defined narrative categories."""
    AI = "AI"
    RWA = "RWA"  # Real World Assets
    DEPIN = "DePIN"  # Decentralized Physical Infrastructure
    MEMECOIN = "Memecoin"
    L1_L2 = "L1/L2"  # Layer 1 and Layer 2
    NFT = "NFT"
    DEFI = "DeFi"
    GAMING = "Gaming"
    PRIVACY = "Privacy"
    DERIVATIVES = "Derivatives"
    SOCIAL = "Social"
    INFRASTRUCTURE = "Infrastructure"


class NarrativeClassifier:
    """Fast narrative classification using keyword matching."""

    def __init__(self):
        """Initialize the classifier with keyword mappings."""
        self.keywords = self._init_keywords()
        self.token_mapping = self._init_token_mapping()
        self.pattern_cache = {}
        self._compile_patterns()

    def _init_keywords(self) -> Dict[NarrativeCategory, Set[str]]:
        """Initialize keyword sets for each narrative category."""
        return {
            NarrativeCategory.AI: {
                'ai', 'artificial intelligence', 'machine learning', 'ml', 'neural',
                'agent', 'agents', 'agentic', 'llm', 'gpt', 'claude', 'chatbot',
                'deep learning', 'transformer', 'generative', 'compute', 'gpu',
                'inference', 'training', 'model', 'dataset', 'autonomous',
                'singularitynet', 'fetch.ai', 'ocean protocol', 'cortex'
            },

            NarrativeCategory.RWA: {
                'rwa', 'real world asset', 'tokenized', 'tokenization', 'treasury',
                'bond', 'bonds', 'securities', 'commodities', 'real estate',
                'institutional', 'tradfi', 'blackrock', 'credit', 'debt',
                'mortgage', 'centrifuge', 'maple', 'goldfinch', 'truefi',
                'backed', 'collateralized', 'yield', 'fixed income'
            },

            NarrativeCategory.DEPIN: {
                'depin', 'decentralized infrastructure', 'physical infrastructure',
                'helium', 'render', 'filecoin', 'arweave', 'storj', 'akash',
                'hivemapper', 'dimo', 'wireless', 'network', 'node', 'nodes',
                'hardware', 'device', 'sensor', 'iot', 'mesh', 'bandwidth',
                'storage', 'compute', 'mobile', 'hotspot', 'mining'
            },

            NarrativeCategory.MEMECOIN: {
                'meme', 'memecoin', 'doge', 'shib', 'shiba', 'pepe', 'wojak',
                'floki', 'elon', 'moon', 'rocket', 'inu', 'baby', 'safe',
                'pump', 'based', 'chad', 'virgin', 'bonk', 'wif', 'dogwifhat',
                'community coin', '100x', '1000x', 'gem', 'moonshot', 'degen'
            },

            NarrativeCategory.L1_L2: {
                'layer 1', 'layer 2', 'l1', 'l2', 'rollup', 'sidechain',
                'ethereum', 'bitcoin', 'solana', 'avalanche', 'polygon',
                'arbitrum', 'optimism', 'base', 'zksync', 'starknet',
                'cosmos', 'polkadot', 'near', 'cardano', 'aptos', 'sui',
                'blockchain', 'consensus', 'validator', 'scaling', 'throughput',
                'finality', 'interoperability', 'bridge', 'cross-chain'
            },

            NarrativeCategory.NFT: {
                'nft', 'non-fungible', 'pfp', 'profile picture', 'collectible',
                'art', 'generative art', 'opensea', 'blur', 'magic eden',
                'ordinals', 'inscription', 'bored ape', 'bayc', 'punk',
                'azuki', 'degods', 'pudgy', 'metadata', 'rarity', 'trait',
                'mint', 'minting', 'drop', 'collection', 'floor price'
            },

            NarrativeCategory.DEFI: {
                'defi', 'decentralized finance', 'yield', 'farming', 'lending',
                'borrowing', 'amm', 'automated market maker', 'dex', 'swap',
                'liquidity', 'pool', 'vault', 'protocol', 'aave', 'compound',
                'uniswap', 'curve', 'maker', 'yearn', 'convex', 'balancer',
                'staking', 'governance', 'dao', 'tvl', 'apr', 'apy', 'impermanent'
            },

            NarrativeCategory.GAMING: {
                'gaming', 'gamefi', 'play to earn', 'p2e', 'metaverse', 'virtual',
                'axie', 'sandbox', 'decentraland', 'immutable', 'gala', 'enjin',
                'steam', 'epic', 'unity', 'unreal', 'game', 'player', 'guild',
                'item', 'character', 'quest', 'battle', 'rpg', 'mmorpg', 'fps',
                'esports', 'tournament', 'leaderboard', 'achievement'
            },

            NarrativeCategory.PRIVACY: {
                'privacy', 'private', 'anonymous', 'confidential', 'zero knowledge',
                'zk', 'zkp', 'monero', 'zcash', 'tornado', 'aztec', 'secret',
                'oasis', 'mixer', 'tumbler', 'stealth', 'ring signature',
                'bulletproof', 'mimblewimble', 'encrypted', 'encryption',
                'confidential transaction', 'shielded', 'dark pool'
            },

            NarrativeCategory.DERIVATIVES: {
                'derivatives', 'perpetual', 'perps', 'futures', 'options',
                'leverage', 'margin', 'synthetic', 'synthetix', 'gmx', 'gains',
                'dydx', 'perpetual protocol', 'drift', 'kwenta', 'polynomial',
                'hedge', 'short', 'long', 'funding', 'liquidation', 'delta',
                'gamma', 'volatility', 'strike', 'expiry', 'settlement'
            },

            NarrativeCategory.SOCIAL: {
                'social', 'socialfi', 'lens', 'farcaster', 'friend.tech',
                'mirror', 'paragraph', 'social token', 'creator', 'fan token',
                'community', 'follower', 'engagement', 'content', 'post',
                'share', 'like', 'comment', 'profile', 'feed', 'timeline',
                'decentralized social', 'censorship resistant', 'monetization'
            },

            NarrativeCategory.INFRASTRUCTURE: {
                'infrastructure', 'oracle', 'chainlink', 'graph', 'indexer',
                'api', 'rpc', 'node provider', 'infura', 'alchemy', 'quicknode',
                'subgraph', 'data feed', 'keeper', 'automation', 'middleware',
                'sdk', 'tooling', 'developer', 'framework', 'library', 'protocol',
                'cross-chain', 'interoperability', 'messaging', 'relayer'
            }
        }

    def _init_token_mapping(self) -> Dict[str, List[NarrativeCategory]]:
        """Map specific token symbols/names to narrative categories."""
        return {
            # AI tokens
            'TAO': [NarrativeCategory.AI],
            'FET': [NarrativeCategory.AI],
            'AGIX': [NarrativeCategory.AI],
            'OCEAN': [NarrativeCategory.AI],
            'NMR': [NarrativeCategory.AI],
            'CTXC': [NarrativeCategory.AI],
            'GLM': [NarrativeCategory.AI],
            'RNDR': [NarrativeCategory.AI, NarrativeCategory.DEPIN],

            # RWA tokens
            'ONDO': [NarrativeCategory.RWA],
            'CFG': [NarrativeCategory.RWA],
            'MPL': [NarrativeCategory.RWA],
            'GFI': [NarrativeCategory.RWA],
            'TRU': [NarrativeCategory.RWA],
            'RIO': [NarrativeCategory.RWA],

            # DePIN tokens
            'HNT': [NarrativeCategory.DEPIN],
            'FIL': [NarrativeCategory.DEPIN],
            'AR': [NarrativeCategory.DEPIN],
            'STORJ': [NarrativeCategory.DEPIN],
            'AKT': [NarrativeCategory.DEPIN],
            'MOBILE': [NarrativeCategory.DEPIN],
            'HONEY': [NarrativeCategory.DEPIN],

            # Memecoins
            'DOGE': [NarrativeCategory.MEMECOIN],
            'SHIB': [NarrativeCategory.MEMECOIN],
            'PEPE': [NarrativeCategory.MEMECOIN],
            'FLOKI': [NarrativeCategory.MEMECOIN],
            'BONK': [NarrativeCategory.MEMECOIN],
            'WIF': [NarrativeCategory.MEMECOIN],

            # L1/L2
            'ETH': [NarrativeCategory.L1_L2],
            'BTC': [NarrativeCategory.L1_L2],
            'SOL': [NarrativeCategory.L1_L2],
            'AVAX': [NarrativeCategory.L1_L2],
            'MATIC': [NarrativeCategory.L1_L2],
            'ARB': [NarrativeCategory.L1_L2],
            'OP': [NarrativeCategory.L1_L2],
            'NEAR': [NarrativeCategory.L1_L2],
            'APT': [NarrativeCategory.L1_L2],
            'SUI': [NarrativeCategory.L1_L2],

            # DeFi tokens
            'UNI': [NarrativeCategory.DEFI],
            'AAVE': [NarrativeCategory.DEFI],
            'CRV': [NarrativeCategory.DEFI],
            'MKR': [NarrativeCategory.DEFI],
            'COMP': [NarrativeCategory.DEFI],
            'SNX': [NarrativeCategory.DEFI, NarrativeCategory.DERIVATIVES],
            'YFI': [NarrativeCategory.DEFI],
            'BAL': [NarrativeCategory.DEFI],
            'SUSHI': [NarrativeCategory.DEFI],

            # Gaming tokens
            'AXS': [NarrativeCategory.GAMING],
            'SAND': [NarrativeCategory.GAMING],
            'MANA': [NarrativeCategory.GAMING],
            'GALA': [NarrativeCategory.GAMING],
            'ENJ': [NarrativeCategory.GAMING],
            'IMX': [NarrativeCategory.GAMING],

            # Infrastructure
            'LINK': [NarrativeCategory.INFRASTRUCTURE],
            'GRT': [NarrativeCategory.INFRASTRUCTURE],
            'API3': [NarrativeCategory.INFRASTRUCTURE],
            'BAND': [NarrativeCategory.INFRASTRUCTURE],
        }

    def _compile_patterns(self):
        """Pre-compile regex patterns for better performance."""
        for category, keywords in self.keywords.items():
            # Create pattern with word boundaries for accurate matching
            pattern_str = r'\b(?:' + '|'.join(re.escape(kw) for kw in keywords) + r')\b'
            self.pattern_cache[category] = re.compile(pattern_str, re.IGNORECASE)

    def classify_fast(self, text: str, title: str = "",
                      tokens: List[str] = None) -> Tuple[List[NarrativeCategory], float]:
        """
        Fast classification using keyword matching.
        Returns (categories, confidence) where confidence is 0-1.
        Target: < 1ms per item.
        """
        start_time = datetime.now()
        categories = set()
        match_counts = {}

        # Combine text and title for analysis
        full_text = f"{title} {text}".lower()

        # Check token mappings first (highest confidence)
        if tokens:
            for token in tokens:
                token_upper = token.upper()
                if token_upper in self.token_mapping:
                    for cat in self.token_mapping[token_upper]:
                        categories.add(cat)
                        match_counts[cat] = match_counts.get(cat, 0) + 3  # Higher weight

        # Check keyword patterns
        for category, pattern in self.pattern_cache.items():
            matches = pattern.findall(full_text)
            if matches:
                categories.add(category)
                match_counts[category] = match_counts.get(category, 0) + len(matches)

        # Calculate confidence based on match density
        total_words = len(full_text.split())
        total_matches = sum(match_counts.values())
        confidence = min(1.0, total_matches / max(total_words * 0.05, 1))  # 5% threshold

        # Performance check
        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        if elapsed > 1:
            logger.warning(f"Classification took {elapsed:.2f}ms (target: <1ms)")

        return (list(categories), confidence)

    def extract_tokens(self, text: str) -> List[str]:
        """Extract potential token symbols from text."""
        # Match patterns like $TOKEN, TOKEN/USDT, or standalone uppercase words
        token_pattern = r'\$([A-Z]{2,10})|([A-Z]{2,10})/|(?:^|\s)([A-Z]{2,10})(?:\s|$)'
        matches = re.findall(token_pattern, text.upper())

        tokens = []
        for match in matches:
            # Get the non-empty group
            token = next((m for m in match if m), None)
            if token and len(token) >= 2 and len(token) <= 10:
                tokens.append(token)

        return list(set(tokens))  # Remove duplicates

    def needs_ai_classification(self, categories: List[NarrativeCategory],
                               confidence: float) -> bool:
        """Determine if item needs Claude API classification."""
        # Need AI help if: no categories found, low confidence, or too many categories
        return (
            len(categories) == 0 or
            confidence < 0.3 or
            len(categories) > 3  # Ambiguous if too many matches
        )

    def merge_classifications(self, fast_categories: List[NarrativeCategory],
                            ai_categories: List[str]) -> List[str]:
        """Merge fast and AI classifications."""
        # Convert enum to strings
        result = {cat.value for cat in fast_categories}

        # Add AI classifications if they're valid
        valid_categories = {cat.value for cat in NarrativeCategory}
        for cat in ai_categories:
            if cat in valid_categories:
                result.add(cat)

        return list(result)