"""Configuration settings for NarrativeFlow."""

from typing import List, Dict
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""

    # API Settings
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./narrative_flow/data/narrative_flow.db",
        description="Database connection URL"
    )

    # Data Collection Intervals (in seconds)
    cryptopanic_interval: int = Field(default=300, description="CryptoPanic polling interval (5 min)")
    reddit_interval: int = Field(default=600, description="Reddit polling interval (10 min)")
    rss_interval: int = Field(default=900, description="RSS polling interval (15 min)")
    defi_llama_interval: int = Field(default=1800, description="DeFiLlama polling interval (30 min)")
    coingecko_interval: int = Field(default=600, description="CoinGecko polling interval (10 min)")
    binance_interval: int = Field(default=60, description="Binance polling interval (1 min)")

    # API Keys (optional for some services)
    cryptopanic_api_key: str = Field(default="", description="CryptoPanic API key (optional for free tier)")
    reddit_client_id: str = Field(default="", description="Reddit client ID")
    reddit_client_secret: str = Field(default="", description="Reddit client secret")
    reddit_user_agent: str = Field(default="NarrativeFlow/1.0", description="Reddit user agent")
    coingecko_api_key: str = Field(default="", description="CoinGecko API key (optional)")

    # Reddit Configuration
    reddit_subreddits: List[str] = Field(
        default=["cryptocurrency", "solana", "defi", "altcoin", "ethtrader"],
        description="Subreddits to monitor"
    )
    reddit_post_limit: int = Field(default=50, description="Number of posts to fetch per subreddit")

    # RSS Feeds
    rss_feeds: Dict[str, str] = Field(
        default={
            "TheBlock": "https://www.theblock.co/rss.xml",
            "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "Decrypt": "https://decrypt.co/feed"
        },
        description="RSS feeds to monitor"
    )

    # Narrative Taxonomy
    narrative_categories: List[str] = Field(
        default=[
            "AI", "RWA", "DePIN", "Memecoin", "L1/L2",
            "NFT", "DeFi", "Gaming", "Privacy",
            "Derivatives", "Social", "Infrastructure"
        ],
        description="Narrative categories for classification"
    )

    # Binance Configuration
    binance_top_symbols: int = Field(default=50, description="Number of top symbols to track")

    # CoinGecko Categories (mapped to our narratives)
    coingecko_category_mapping: Dict[str, str] = Field(
        default={
            "artificial-intelligence": "AI",
            "real-world-assets": "RWA",
            "depin": "DePIN",
            "meme-token": "Memecoin",
            "layer-1": "L1/L2",
            "layer-2": "L1/L2",
            "non-fungible-tokens-nft": "NFT",
            "decentralized-finance-defi": "DeFi",
            "gaming": "Gaming",
            "privacy-coins": "Privacy",
            "derivatives": "Derivatives",
            "social": "Social",
            "infrastructure": "Infrastructure"
        },
        description="Mapping from CoinGecko categories to our narratives"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()